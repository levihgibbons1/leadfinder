from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv()


def get_secret(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value not in (None, ""):
        return value
    try:
        return str(st.secrets.get(name, default))
    except Exception:  # noqa: BLE001
        return default


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path
    database_url: str
    excel_path: Path
    rapidapi_key: str
    rapidapi_host: str
    rapidapi_base_url: str
    rapidapi_timeout_seconds: int
    openai_api_key: str
    openai_model: str
    request_timeout_seconds: int
    user_agent: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings(
        sqlite_path=DATA_DIR / "leads.db",
        database_url=get_secret("DATABASE_URL", ""),
        excel_path=DATA_DIR / "leads.xlsx",
        rapidapi_key=get_secret("RAPIDAPI_KEY", ""),
        rapidapi_host=get_secret("RAPIDAPI_HOST", "local-business-data.p.rapidapi.com"),
        rapidapi_base_url=get_secret("RAPIDAPI_BASE_URL", "https://local-business-data.p.rapidapi.com"),
        rapidapi_timeout_seconds=int(get_secret("RAPIDAPI_TIMEOUT_SECONDS", "25")),
        openai_api_key=get_secret("OPENAI_API_KEY", ""),
        openai_model=get_secret("OPENAI_MODEL", "gpt-4o-mini"),
        request_timeout_seconds=int(get_secret("REQUEST_TIMEOUT_SECONDS", "10")),
        user_agent=get_secret(
            "LEADFINDER_USER_AGENT",
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        ),
    )
