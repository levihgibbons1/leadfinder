from __future__ import annotations

from pathlib import Path

import pandas as pd

from leadfinder.models import LeadRecord


class ExcelExporter:
    def __init__(self, workbook_path: Path) -> None:
        self.workbook_path = workbook_path
        self.workbook_path.parent.mkdir(parents=True, exist_ok=True)

    def upsert_leads(self, leads: list[LeadRecord]) -> None:
        if not leads:
            return

        incoming_df = pd.DataFrame([lead.to_excel_row() for lead in leads])
        if self.workbook_path.exists():
            existing_df = pd.read_excel(self.workbook_path)
            merged_df = pd.concat([existing_df, incoming_df], ignore_index=True)
        else:
            merged_df = incoming_df

        merged_df = merged_df.drop_duplicates(subset=["dedupe_key"], keep="last")
        merged_df = merged_df.sort_values(by=["created_at", "Business Name"], ascending=[False, True])
        merged_df.to_excel(self.workbook_path, index=False, engine="openpyxl")
