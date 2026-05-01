from __future__ import annotations

from typing import Callable

import pandas as pd

from leadfinder.config import Settings
from leadfinder.database import LeadDatabase
from leadfinder.excel import ExcelExporter
from leadfinder.models import LeadRecord, SearchInput
from leadfinder.services.ai_enrichment import LeadAIEnricher
from leadfinder.services.business_search import RapidAPIBusinessSearch
from leadfinder.services.website_analyzer import WebsiteAnalyzer


ProgressCallback = Callable[[float, str], None]


class LeadPipeline:
    def __init__(
        self,
        settings: Settings,
        database: LeadDatabase,
        search_service: RapidAPIBusinessSearch,
        website_analyzer: WebsiteAnalyzer,
        ai_enricher: LeadAIEnricher,
    ) -> None:
        self.settings = settings
        self.database = database
        self.search_service = search_service
        self.website_analyzer = website_analyzer
        self.ai_enricher = ai_enricher
        self.excel_exporter = ExcelExporter(settings.excel_path)

    def run_search(
        self,
        search_input: SearchInput,
        progress_callback: ProgressCallback | None = None,
    ) -> list[LeadRecord]:
        self._progress(progress_callback, 0.05, "Searching local business listings...")
        records = self.search_service.search(search_input)
        if not records:
            return []

        processed: list[LeadRecord] = []
        total = len(records)
        for index, lead in enumerate(records, start=1):
            self._progress(progress_callback, 0.15 + (0.75 * ((index - 1) / total)), f"Analyzing {lead.business_name}...")
            analysis = self.website_analyzer.analyze(lead.website)
            lead.website = analysis.final_url or lead.website
            lead.website_summary = analysis.summary
            lead.key_signals, lead.personalized_openers = self.ai_enricher.enrich(lead, analysis)
            processed.append(lead.prepare())

        self._progress(progress_callback, 0.92, "Saving leads to SQLite and Excel...")
        self.database.upsert_leads(processed)
        self.excel_exporter.upsert_leads(processed)
        self._progress(progress_callback, 1.0, "Lead search complete.")
        return processed

    @staticmethod
    def records_to_dataframe(records: list[LeadRecord]) -> pd.DataFrame:
        if not records:
            return pd.DataFrame()

        return pd.DataFrame(
            [
                {
                    "Business Name": lead.business_name,
                    "Location": lead.location or f"{lead.city}, {lead.state}",
                    "Phone": lead.phone,
                    "Website": lead.website,
                    "Rating": lead.rating,
                    "Reviews": lead.reviews,
                    "Key Signals": "\n".join(lead.key_signals),
                    "Personalized Openers": "\n\n".join(lead.personalized_openers),
                }
                for lead in records
            ]
        ).sort_values(by=["Reviews", "Business Name"], ascending=[True, True], na_position="last")

    @staticmethod
    def _progress(callback: ProgressCallback | None, progress: float, message: str) -> None:
        if callback:
            callback(progress, message)
