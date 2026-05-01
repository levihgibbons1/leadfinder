from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from leadfinder.config import Settings
from leadfinder.models import LeadRecord, WebsiteAnalysis


class LeadAIEnricher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def enrich(self, lead: LeadRecord, analysis: WebsiteAnalysis) -> tuple[list[str], list[str]]:
        base_signals = self._build_base_signals(lead, analysis)
        base_openers = self._build_openers(lead, base_signals)

        if not self.settings.openai_api_key:
            return base_signals, base_openers

        try:
            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.responses.create(
                model=self.settings.openai_model,
                instructions=(
                    "You are enriching local business sales leads for a website and branding redesign agency. "
                    "Return JSON only with two keys: key_signals and personalized_openers. "
                    "key_signals must be 3 to 5 concise, evidence-based bullets. "
                    "personalized_openers must be exactly 3 short outreach openers tailored to the lead."
                ),
                input=json.dumps(
                    {
                        "business_name": lead.business_name,
                        "category": lead.category,
                        "city": lead.city,
                        "state": lead.state,
                        "location": lead.location,
                        "phone": lead.phone,
                        "website": lead.website,
                        "rating": lead.rating,
                        "reviews": lead.reviews,
                        "website_analysis": {
                            "signals": analysis.signals,
                            "summary": analysis.summary,
                            "page_title": analysis.page_title,
                            "metrics": analysis.metrics,
                        },
                        "fallback_signals": base_signals,
                    }
                ),
                text={"format": {"type": "json_object"}},
            )
            parsed = json.loads(response.output_text)
        except Exception:  # noqa: BLE001
            return base_signals, base_openers

        key_signals = self._clean_string_list(parsed.get("key_signals"), limit=5) or base_signals
        openers = self._clean_string_list(parsed.get("personalized_openers"), limit=3) or base_openers
        return key_signals, openers

    @staticmethod
    def _clean_string_list(value: Any, limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned[:limit]

    def _build_base_signals(self, lead: LeadRecord, analysis: WebsiteAnalysis) -> list[str]:
        signals = list(analysis.signals)

        if lead.reviews is not None and lead.reviews <= 15:
            signals.append(f"Only {lead.reviews} Google reviews visible, so credibility still has room to grow online.")
        elif lead.reviews is not None and lead.reviews <= 40:
            signals.append(f"Review volume is still modest at {lead.reviews}, which leaves room for stronger trust signals on-site.")

        if lead.rating is not None and lead.rating >= 4.7:
            signals.append(f"Strong {lead.rating:.1f}-star rating suggests the reputation is better than the likely website presentation.")

        if not lead.website:
            signals.append("No website is linked in the listing, which makes the digital refresh angle especially direct.")

        if not signals:
            signals.append("Local-service positioning is present, but the brand likely needs a more modern visual front door.")

        unique: list[str] = []
        for signal in signals:
            if signal not in unique:
                unique.append(signal)
        return unique[:5]

    def _build_openers(self, lead: LeadRecord, signals: list[str]) -> list[str]:
        town = f"{lead.city}, {lead.state}"
        first_signal = signals[0].rstrip(".")
        second_signal = signals[1].rstrip(".") if len(signals) > 1 else "the brand could feel more current online"

        openers = [
            (
                f"I was looking at {lead.business_name} in {town} and noticed {first_signal.lower()}. "
                f"We redesign websites and branding for family-owned trades businesses without making them feel corporate."
            ),
            (
                f"{lead.business_name} already has a real local footprint in {town}, but {second_signal.lower()}. "
                "That is usually where a cleaner site and stronger visuals start converting more estimate requests."
            ),
        ]

        if any("family-owned" in signal.lower() for signal in signals):
            openers.append(
                f"The family-owned angle at {lead.business_name} stands out. We’d keep that trust factor intact while making the site look far more current."
            )
        else:
            openers.append(
                f"If you ever want a quick teardown, I can show how {lead.business_name} could look more modern and premium while still feeling local to {town}."
            )

        return openers[:3]
