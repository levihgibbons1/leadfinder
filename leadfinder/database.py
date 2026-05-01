from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from leadfinder.models import LeadRecord, SearchInput


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

CRM_COLUMNS = {
    "priority": "TEXT NOT NULL DEFAULT 'Medium'",
    "contact_method": "TEXT NOT NULL DEFAULT ''",
    "email": "TEXT NOT NULL DEFAULT ''",
    "owner_name": "TEXT NOT NULL DEFAULT ''",
    "last_contacted_at": "TEXT NOT NULL DEFAULT ''",
    "next_follow_up_at": "TEXT NOT NULL DEFAULT ''",
    "status_reason": "TEXT NOT NULL DEFAULT ''",
}

MANAGEMENT_FIELDS = [
    "status",
    "priority",
    "contact_method",
    "email",
    "owner_name",
    "last_contacted_at",
    "next_follow_up_at",
    "status_reason",
    "notes",
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
            self._ensure_lead_columns(connection)
            connection.execute(text(self._lead_events_ddl()))
            connection.execute(text(self._saved_searches_ddl()))
            connection.execute(text(self._projects_ddl()))

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
                        priority,
                        contact_method,
                        email,
                        owner_name,
                        last_contacted_at,
                        next_follow_up_at,
                        status_reason,
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

    def update_lead_management(self, updates: pd.DataFrame) -> None:
        if updates.empty:
            return

        with self.engine.begin() as connection:
            for _, row in updates.iterrows():
                payload = {
                    "id": int(row["id"]),
                    "status": self._clean(row.get("status")) or "New",
                    "priority": self._clean(row.get("priority")) or "Medium",
                    "contact_method": self._clean(row.get("contact_method")),
                    "email": self._clean(row.get("email")),
                    "owner_name": self._clean(row.get("owner_name")),
                    "last_contacted_at": self._clean_date(row.get("last_contacted_at")),
                    "next_follow_up_at": self._clean_date(row.get("next_follow_up_at")),
                    "status_reason": self._clean(row.get("status_reason")),
                    "notes": self._clean(row.get("notes")),
                }

                current = (
                    connection.execute(
                        text(
                            """
                            SELECT
                                id,
                                status,
                                priority,
                                contact_method,
                                email,
                                owner_name,
                                last_contacted_at,
                                next_follow_up_at,
                                status_reason,
                                notes
                            FROM leads
                            WHERE id = :id
                            """
                        ),
                        {"id": payload["id"]},
                    )
                    .mappings()
                    .first()
                )

                if current is None:
                    continue

                connection.execute(
                    text(
                        """
                        UPDATE leads
                        SET
                            status = :status,
                            priority = :priority,
                            contact_method = :contact_method,
                            email = :email,
                            owner_name = :owner_name,
                            last_contacted_at = :last_contacted_at,
                            next_follow_up_at = :next_follow_up_at,
                            status_reason = :status_reason,
                            notes = :notes,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                        """
                    ),
                    payload,
                )

                events = []
                current_dict = dict(current)
                for field in MANAGEMENT_FIELDS:
                    old_value = self._clean(current_dict.get(field))
                    new_value = self._clean(payload.get(field))
                    if old_value != new_value:
                        events.append(
                            {
                                "lead_id": payload["id"],
                                "event_type": "field_update",
                                "field_name": field,
                                "old_value": old_value,
                                "new_value": new_value,
                                "note": "",
                            }
                        )

                if events:
                    connection.execute(text(self._insert_event_sql()), events)

    def update_status_notes(self, updates: pd.DataFrame) -> None:
        self.update_lead_management(updates)

    def record_saved_search(self, search_input: SearchInput, result_count: int) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO saved_searches (
                        category,
                        city,
                        state,
                        limit_count,
                        result_count,
                        created_at
                    ) VALUES (
                        :category,
                        :city,
                        :state,
                        :limit_count,
                        :result_count,
                        CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "category": search_input.category,
                    "city": search_input.city,
                    "state": search_input.state,
                    "limit_count": search_input.limit,
                    "result_count": result_count,
                },
            )

    def fetch_lead_events(self, limit: int = 200) -> pd.DataFrame:
        with self.engine.connect() as connection:
            return pd.read_sql_query(
                text(
                    """
                    SELECT
                        lead_events.id,
                        lead_events.lead_id,
                        leads.business_name,
                        lead_events.event_type,
                        lead_events.field_name,
                        lead_events.old_value,
                        lead_events.new_value,
                        lead_events.note,
                        lead_events.created_at
                    FROM lead_events
                    LEFT JOIN leads ON leads.id = lead_events.lead_id
                    ORDER BY lead_events.created_at DESC, lead_events.id DESC
                    LIMIT :limit
                    """
                ),
                connection,
                params={"limit": limit},
            )

    def fetch_saved_searches(self, limit: int = 100) -> pd.DataFrame:
        with self.engine.connect() as connection:
            return pd.read_sql_query(
                text(
                    """
                    SELECT
                        id,
                        category,
                        city,
                        state,
                        limit_count,
                        result_count,
                        created_at
                    FROM saved_searches
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                connection,
                params={"limit": limit},
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
    def _clean(value: Any) -> str:
        if value is None or pd.isna(value):
            return ""
        return str(value).strip()

    @classmethod
    def _clean_date(cls, value: Any) -> str:
        cleaned = cls._clean(value)
        if not cleaned:
            return ""
        try:
            return pd.to_datetime(cleaned).date().isoformat()
        except (TypeError, ValueError):
            return cleaned

    def _ensure_lead_columns(self, connection: Any) -> None:
        existing = self._existing_columns(connection, "leads")
        for column_name, definition in CRM_COLUMNS.items():
            if column_name not in existing:
                connection.execute(text(f"ALTER TABLE leads ADD COLUMN {column_name} {definition}"))

    def _existing_columns(self, connection: Any, table_name: str) -> set[str]:
        if self.engine.dialect.name == "postgresql":
            rows = connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    """
                ),
                {"table_name": table_name},
            )
            return {str(row[0]) for row in rows}

        rows = connection.execute(text(f"PRAGMA table_info({table_name})"))
        return {str(row[1]) for row in rows}

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
                priority TEXT NOT NULL DEFAULT 'Medium',
                contact_method TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                owner_name TEXT NOT NULL DEFAULT '',
                last_contacted_at TEXT NOT NULL DEFAULT '',
                next_follow_up_at TEXT NOT NULL DEFAULT '',
                status_reason TEXT NOT NULL DEFAULT '',
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
                priority TEXT NOT NULL DEFAULT 'Medium',
                contact_method TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                owner_name TEXT NOT NULL DEFAULT '',
                last_contacted_at TEXT NOT NULL DEFAULT '',
                next_follow_up_at TEXT NOT NULL DEFAULT '',
                status_reason TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'RapidAPI',
                raw_payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
        """

    def _lead_events_ddl(self) -> str:
        if self.engine.dialect.name == "postgresql":
            return """
                CREATE TABLE IF NOT EXISTS lead_events (
                    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    lead_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    field_name TEXT NOT NULL DEFAULT '',
                    old_value TEXT NOT NULL DEFAULT '',
                    new_value TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """

        return """
            CREATE TABLE IF NOT EXISTS lead_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                field_name TEXT NOT NULL DEFAULT '',
                old_value TEXT NOT NULL DEFAULT '',
                new_value TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """

    def _saved_searches_ddl(self) -> str:
        if self.engine.dialect.name == "postgresql":
            return """
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    category TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    limit_count INTEGER NOT NULL,
                    result_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """

        return """
            CREATE TABLE IF NOT EXISTS saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                limit_count INTEGER NOT NULL,
                result_count INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

    @staticmethod
    def _insert_event_sql() -> str:
        return """
            INSERT INTO lead_events (
                lead_id,
                event_type,
                field_name,
                old_value,
                new_value,
                note,
                created_at
            ) VALUES (
                :lead_id,
                :event_type,
                :field_name,
                :old_value,
                :new_value,
                :note,
                CURRENT_TIMESTAMP
            )
        """

    def _projects_ddl(self) -> str:
        if self.engine.dialect.name == "postgresql":
            return """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    lead_id INTEGER,
                    project_name TEXT NOT NULL,
                    client_name TEXT NOT NULL DEFAULT '',
                    project_type TEXT NOT NULL DEFAULT 'Build',
                    status TEXT NOT NULL DEFAULT 'Planning',
                    priority TEXT NOT NULL DEFAULT 'Medium',
                    start_date TEXT NOT NULL DEFAULT '',
                    due_date TEXT NOT NULL DEFAULT '',
                    completion_date TEXT NOT NULL DEFAULT '',
                    value DOUBLE PRECISION NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
        return """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                project_name TEXT NOT NULL,
                client_name TEXT NOT NULL DEFAULT '',
                project_type TEXT NOT NULL DEFAULT 'Build',
                status TEXT NOT NULL DEFAULT 'Planning',
                priority TEXT NOT NULL DEFAULT 'Medium',
                start_date TEXT NOT NULL DEFAULT '',
                due_date TEXT NOT NULL DEFAULT '',
                completion_date TEXT NOT NULL DEFAULT '',
                value REAL NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """

    def fetch_projects(self) -> pd.DataFrame:
        with self.engine.connect() as connection:
            return pd.read_sql_query(
                text(
                    """
                    SELECT
                        id, lead_id, project_name, client_name, project_type,
                        status, priority, start_date, due_date, completion_date,
                        value, notes, created_at, updated_at
                    FROM projects
                    ORDER BY created_at DESC, id DESC
                    """
                ),
                connection,
            )

    def save_project(self, data: dict[str, Any]) -> None:
        if data.get("id"):
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        UPDATE projects SET
                            project_name = :project_name,
                            client_name = :client_name,
                            project_type = :project_type,
                            status = :status,
                            priority = :priority,
                            start_date = :start_date,
                            due_date = :due_date,
                            completion_date = :completion_date,
                            value = :value,
                            notes = :notes,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                        """
                    ),
                    data,
                )
        else:
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO projects (
                            lead_id, project_name, client_name, project_type,
                            status, priority, start_date, due_date,
                            completion_date, value, notes
                        ) VALUES (
                            :lead_id, :project_name, :client_name, :project_type,
                            :status, :priority, :start_date, :due_date,
                            :completion_date, :value, :notes
                        )
                        """
                    ),
                    data,
                )

    def delete_project(self, project_id: int) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("DELETE FROM projects WHERE id = :id"),
                {"id": project_id},
            )
