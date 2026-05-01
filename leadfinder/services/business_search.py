from __future__ import annotations

from typing import Any

import requests

from leadfinder.config import Settings
from leadfinder.models import LeadRecord, SearchInput
from leadfinder.utils import ensure_url, parse_float, parse_int


class RapidAPIBusinessSearch:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent})

    def search(self, search_input: SearchInput) -> list[LeadRecord]:
        if not self.settings.rapidapi_key:
            raise RuntimeError("RAPIDAPI_KEY is required to run business searches.")

        response = self.session.get(
            f"{self.settings.rapidapi_base_url.rstrip('/')}/search",
            headers={
                "x-rapidapi-key": self.settings.rapidapi_key,
                "x-rapidapi-host": self.settings.rapidapi_host,
            },
            params={
                "query": f"{search_input.category} in {search_input.city}, {search_input.state}",
                "limit": search_input.limit,
                "region": "us",
                "language": "en",
            },
            timeout=self.settings.rapidapi_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        items = self._extract_items(payload)

        leads: list[LeadRecord] = []
        for item in items[: search_input.limit]:
            lead = LeadRecord(
                business_name=self._pick(item, "name", "title", "business_name") or "Unknown business",
                category=search_input.category,
                city=search_input.city,
                state=search_input.state,
                location=self._pick(
                    item,
                    "full_address",
                    "address",
                    "street_address",
                    "formatted_address",
                )
                or f"{search_input.city}, {search_input.state}",
                phone=self._pick(
                    item,
                    "phone_number",
                    "phone",
                    "international_phone_number",
                    "formatted_phone_number",
                )
                or "",
                website=ensure_url(
                    self._pick(item, "website", "site", "domain", "website_url", "url") or ""
                ),
                rating=parse_float(self._pick(item, "rating", "review_rating", "stars")),
                reviews=parse_int(self._pick(item, "review_count", "reviews", "reviews_count")),
                source="RapidAPI",
                source_id=str(self._pick(item, "place_id", "google_id", "business_id", "cid", "id") or ""),
                raw_payload=item,
            )
            leads.append(lead)

        return leads

    @staticmethod
    def _extract_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []

        direct = payload.get("data") or payload.get("results") or payload.get("items")
        if isinstance(direct, list):
            return [item for item in direct if isinstance(item, dict)]
        if isinstance(direct, dict):
            nested = direct.get("items") or direct.get("results")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return []

    @staticmethod
    def _pick(item: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return None
