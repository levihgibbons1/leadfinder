from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from leadfinder.models import LeadRecord


STORAGE_FIELDS = [
    "dedupe_key",
    "source_id",
    "business_name",
    "category",
    "city",
    "state",
    "location",
    "phone",
    "website",
    "rating",
    "reviews",
    "key_signals",
    "personalized_openers",
    "website_summary",
    "status",
    "notes",
    "source",
    "raw_payload",
    "created_at",
    "updated_at",
    "last_seen_at",
]


class LeadDatabase:
    def __init__(self, sqlite_path: Path, database_url: str = "") -> None:
        self.sqlite_path = sqlite_path
        self.database_url = self._normalize_database_url(database_url)
        self.engine = self._create_engine()
        self._initialize()

    def _create_engine(self) -> Engine:
        if self.database_url:
            return create_engine(self.database_url, pool_pre_ping=True)

        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite:///{self.sqlite_path}", future=True)

    def _initialize(self) -> None:
        ddl = self._postgres_ddl() if self.engine.dialect.name == "postgresql" else self._sqlite_ddl()
        with self.engine.begin() as connection:
            connection.execute(text(ddl))

    def upsert_leads(self, leads: list[LeadRecord]) -> None:
        if not leads:
            return

        payload = [self._lead_to_dict(lead) for lead in leads]
        with self.engine.begin() as connection:
            connection.execute(text(self._upsert_sql()), payload)

    def fetch_all_leads(self) -> pd.DataFrame:
        with self.engine.connect() as connection:
            df = pd.read_sql_query(
                text(
                    """
                    SELECT
                        id,
                        dedupe_key,
                        source_id,
                        business_name,
                        category,
                        city,
                        state,
                        location,
                        phone,
                        website,
                        rating,
                        reviews,
                        key_signals,
                        personalized_openers,
                        website_summary,
                        status,
                        notes,
                        source,
                        created_at,
                        updated_at,
                        last_seen_at
                    FROM leads
                    ORDER BY created_at DESC, business_name ASC
                    """
                ),
                connection,
            )

        if df.empty:
            return df

        for column in ["key_signals", "personalized_openers"]:
            df[column] = df[column].apply(self._parse_json_list)

        return df

    def update_status_notes(self, updates: pd.DataFrame) -> None:
        if updates.empty:
            return

        payload = [
            {
                "id": int(row["id"]),
                "status": ("" if pd.isna(row["status"]) else str(row["status"]).strip()) or "New",
                "notes": "" if pd.isna(row["notes"]) else str(row["notes"]).strip(),
            }
            for _, row in updates.iterrows()
        ]

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE leads
                    SET status = :status, notes = :notes, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                payload,
            )

    @staticmethod
    def _normalize_database_url(database_url: str) -> str:
        clean_url = database_url.strip()
        if clean_url.startswith("postgres://"):
            return clean_url.replace("postgres://", "postgresql+psycopg2://", 1)
        if clean_url.startswith("postgresql://"):
            return clean_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return clean_url

    @staticmethod
    def _lead_to_dict(lead: LeadRecord) -> dict[str, Any]:
        return dict(zip(STORAGE_FIELDS, lead.to_storage_tuple(), strict=True))

    @staticmethod
    def _parse_json_list(value: str) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
        return []

    @staticmethod
    def _sqlite_ddl() -> str:
        return """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dedupe_key TEXT NOT NULL UNIQUE,
                source_id TEXT,
                business_name TEXT NOT NULL,
                category TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                website TEXT NOT NULL DEFAULT '',
                rating REAL,
                reviews INTEGER,
                key_signals TEXT NOT NULL DEFAULT '[]',
                personalized_openers TEXT NOT NULL DEFAULT '[]',
                website_summary TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'New',
                notes TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'RapidAPI',
                raw_payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
        """

    @staticmethod
    def _postgres_ddl() -> str:
        return """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                dedupe_key TEXT NOT NULL UNIQUE,
                source_id TEXT,
                business_name TEXT NOT NULL,
                category TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                website TEXT NOT NULL DEFAULT '',
                rating DOUBLE PRECISION,
                reviews INTEGER,
                key_signals TEXT NOT NULL DEFAULT '[]',
                personalized_openers TEXT NOT NULL DEFAULT '[]',
                website_summary TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'New',
                notes TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'RapidAPI',
                raw_payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
        """

    @staticmethod
    def _upsert_sql() -> str:
        return """
            INSERT INTO leads (
                dedupe_key,
                source_id,
                business_name,
                category,
                city,
                state,
                location,
                phone,
                website,
                rating,
                reviews,
                key_signals,
                personalized_openers,
                website_summary,
                status,
                notes,
                source,
                raw_payload,
                created_at,
                updated_at,
                last_seen_at
            ) VALUES (
                :dedupe_key,
                :source_id,
                :business_name,
                :category,
                :city,
                :state,
                :location,
                :phone,
                :website,
                :rating,
                :reviews,
                :key_signals,
                :personalized_openers,
                :website_summary,
                :status,
                :notes,
                :source,
                :raw_payload,
                :created_at,
                :updated_at,
                :last_seen_at
            )
            ON CONFLICT(dedupe_key) DO UPDATE SET
                source_id = COALESCE(NULLIF(excluded.source_id, ''), leads.source_id),
                business_name = excluded.business_name,
                category = excluded.category,
                city = excluded.city,
                state = excluded.state,
                location = COALESCE(NULLIF(excluded.location, ''), leads.location),
                phone = COALESCE(NULLIF(excluded.phone, ''), leads.phone),
                website = COALESCE(NULLIF(excluded.website, ''), leads.website),
                rating = COALESCE(excluded.rating, leads.rating),
                reviews = COALESCE(excluded.reviews, leads.reviews),
                key_signals = CASE
                    WHEN excluded.key_signals != '[]' THEN excluded.key_signals
                    ELSE leads.key_signals
                END,
                personalized_openers = CASE
                    WHEN excluded.personalized_openers != '[]' THEN excluded.personalized_openers
                    ELSE leads.personalized_openers
                END,
                website_summary = CASE
                    WHEN excluded.website_summary != '' THEN excluded.website_summary
                    ELSE leads.website_summary
                END,
                source = excluded.source,
                raw_payload = excluded.raw_payload,
                updated_at = excluded.updated_at,
                last_seen_at = excluded.last_seen_at
        """
