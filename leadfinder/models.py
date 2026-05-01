from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from leadfinder.utils import build_dedupe_key


@dataclass(slots=True)
class SearchInput:
    category: str
    city: str
    state: str
    limit: int = 30


@dataclass(slots=True)
class WebsiteAnalysis:
    final_url: str = ""
    page_title: str = ""
    reachable: bool = False
    signals: list[str] = field(default_factory=list)
    summary: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LeadRecord:
    business_name: str
    category: str
    city: str
    state: str
    location: str = ""
    phone: str = ""
    website: str = ""
    rating: float | None = None
    reviews: int | None = None
    key_signals: list[str] = field(default_factory=list)
    personalized_openers: list[str] = field(default_factory=list)
    website_summary: str = ""
    status: str = "New"
    notes: str = ""
    source: str = "RapidAPI"
    source_id: str = ""
    dedupe_key: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    last_seen_at: str = ""

    def prepare(self) -> "LeadRecord":
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if not self.created_at:
            self.created_at = timestamp
        self.updated_at = timestamp
        self.last_seen_at = timestamp
        if not self.dedupe_key:
            self.dedupe_key = build_dedupe_key(
                self.business_name,
                self.phone,
                self.website,
                self.location or f"{self.city}, {self.state}",
            )
        return self

    def to_storage_tuple(self) -> tuple[Any, ...]:
        self.prepare()
        return (
            self.dedupe_key,
            self.source_id,
            self.business_name,
            self.category,
            self.city,
            self.state,
            self.location,
            self.phone,
            self.website,
            self.rating,
            self.reviews,
            json.dumps(self.key_signals),
            json.dumps(self.personalized_openers),
            self.website_summary,
            self.status,
            self.notes,
            self.source,
            json.dumps(self.raw_payload),
            self.created_at,
            self.updated_at,
            self.last_seen_at,
        )

    def to_excel_row(self) -> dict[str, Any]:
        self.prepare()
        return {
            "dedupe_key": self.dedupe_key,
            "Business Name": self.business_name,
            "Category": self.category,
            "City": self.city,
            "State": self.state,
            "Location": self.location,
            "Phone": self.phone,
            "Website": self.website,
            "Rating": self.rating,
            "Reviews": self.reviews,
            "Key Signals": " | ".join(self.key_signals),
            "Personalized Openers": " | ".join(self.personalized_openers),
            "Status": self.status,
            "Notes": self.notes,
            "Source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
