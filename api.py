"""FastAPI server exposing the LeadFinder pipeline for the Next.js CPM app."""
from __future__ import annotations

import asyncio
import json
import dataclasses
import os
from queue import Queue
from threading import Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from leadfinder.config import get_settings
from leadfinder.database import LeadDatabase
from leadfinder.models import SearchInput
from leadfinder.pipeline import LeadPipeline
from leadfinder.services.ai_enrichment import LeadAIEnricher
from leadfinder.services.business_search import RapidAPIBusinessSearch
from leadfinder.services.website_analyzer import WebsiteAnalyzer

app = FastAPI(title="LeadFinder API")

_CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


def _build_pipeline() -> LeadPipeline:
    settings = get_settings()
    db = LeadDatabase(settings)
    return LeadPipeline(
        settings=settings,
        database=db,
        search_service=RapidAPIBusinessSearch(settings),
        website_analyzer=WebsiteAnalyzer(settings),
        ai_enricher=LeadAIEnricher(settings),
    )


class SearchRequest(BaseModel):
    category: str
    city: str
    state: str
    limit: int = 10


def _lead_to_dict(record) -> dict:
    d = dataclasses.asdict(record)
    d["key_signals"] = record.key_signals if isinstance(record.key_signals, list) else json.loads(record.key_signals or "[]")
    d["personalized_openers"] = record.personalized_openers if isinstance(record.personalized_openers, list) else json.loads(record.personalized_openers or "[]")
    d.pop("raw_payload", None)
    return d


@app.post("/api/search")
async def search(request: SearchRequest):
    queue: Queue = Queue()

    def run():
        try:
            pipeline = _build_pipeline()
            search_input = SearchInput(
                category=request.category,
                city=request.city,
                state=request.state,
                limit=request.limit,
            )

            def progress(pct: float, msg: str) -> None:
                queue.put({"type": "progress", "pct": round(pct, 2), "msg": msg})

            records = pipeline.run_search(search_input, progress)
            queue.put({"type": "done", "results": [_lead_to_dict(r) for r in records]})
        except Exception as exc:  # noqa: BLE001
            queue.put({"type": "error", "msg": str(exc)})

    Thread(target=run, daemon=True).start()

    async def stream():
        while True:
            if not queue.empty():
                item = queue.get()
                yield f"data: {json.dumps(item)}\n\n"
                if item["type"] in ("done", "error"):
                    break
            await asyncio.sleep(0.15)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/health")
async def health():
    return {"ok": True}
