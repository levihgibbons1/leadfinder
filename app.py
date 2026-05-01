from __future__ import annotations

import hashlib
import html
import random
from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as st_components

from leadfinder.config import get_settings
from leadfinder.database import LeadDatabase
from leadfinder.models import SearchInput
from leadfinder.pipeline import LeadPipeline
from leadfinder.services.ai_enrichment import LeadAIEnricher
from leadfinder.services.business_search import RapidAPIBusinessSearch
from leadfinder.services.website_analyzer import WebsiteAnalyzer


SUGGESTED_CATEGORIES = [
    "roofing contractor",
    "HVAC contractor",
    "pool builder",
    "general contractor",
    "siding contractor",
    "excavation contractor",
    "concrete contractor",
    "ventilation contractor",
    "remodeling contractor",
    "insulation contractor",
]

STATE_NAME_TO_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}
STATE_ABBR_TO_NAME = {abbr: name for name, abbr in STATE_NAME_TO_ABBR.items()}
STATE_OPTIONS = list(STATE_NAME_TO_ABBR.keys())
STATE_PLACEHOLDER = "Select a state"

LEAD_STATUS_OPTIONS = [
    "New", "Qualified", "Pending", "Contacted", "Follow Up",
    "Interested", "Client", "Not Fit", "No Response", "Failed", "Dead",
]
STATUS_FILTER_OPTIONS = ["All", *LEAD_STATUS_OPTIONS]
ACTIVE_STATUS_OPTIONS = {"New", "Qualified", "Pending", "Contacted", "Follow Up", "Interested", "No Response"}
PRIORITY_OPTIONS = ["Low", "Medium", "High", "Urgent"]
CONTACT_METHOD_OPTIONS = ["", "Email", "Call", "Text", "Website Form", "In Person"]
WEBSITE_FILTER_OPTIONS = ["Any", "Has website", "No website"]
OPPORTUNITY_FILTER_OPTIONS = ["Any", "Hot", "Warm", "Low"]
SIGNAL_FILTER_OPTIONS = [
    "Any", "No website", "Outdated website", "Mobile issues",
    "Family-owned angle", "Low reviews",
]
SORT_OPTIONS = [
    "Best opportunity first", "Lowest reviews first",
    "Highest rating first", "Business name A-Z",
]

PROJECT_TYPE_OPTIONS = ["Build", "Optimize", "Fix", "Maintain", "Redesign", "SEO", "Other"]
PROJECT_STATUS_OPTIONS = ["Planning", "In Progress", "Review", "Complete", "On Hold"]

PIPELINE_STAGES = ["New", "Qualified", "Contacted", "Follow Up", "Interested", "Client"]

SMALL_TOWN_MARKETS = [
    ("Bozeman", "MT"), ("Cody", "WY"), ("Laramie", "WY"), ("Sheridan", "WY"),
    ("Sandpoint", "ID"), ("Twin Falls", "ID"), ("Lewiston", "ID"), ("Bend", "OR"),
    ("Roseburg", "OR"), ("Grants Pass", "OR"), ("Wenatchee", "WA"), ("Ellensburg", "WA"),
    ("Yakima", "WA"), ("St. George", "UT"), ("Cedar City", "UT"), ("Durango", "CO"),
    ("Montrose", "CO"), ("Grand Junction", "CO"), ("Farmington", "NM"), ("Carlsbad", "NM"),
    ("Pueblo", "CO"), ("Hutchinson", "KS"), ("Salina", "KS"), ("Manhattan", "KS"),
    ("Joplin", "MO"), ("Branson", "MO"), ("Cape Girardeau", "MO"), ("Bentonville", "AR"),
    ("Russellville", "AR"), ("Pine Bluff", "AR"), ("Muskogee", "OK"), ("Stillwater", "OK"),
    ("Enid", "OK"), ("Waco", "TX"), ("Abilene", "TX"), ("Nacogdoches", "TX"),
    ("Lake Charles", "LA"), ("Monroe", "LA"), ("Hattiesburg", "MS"), ("Meridian", "MS"),
    ("Dothan", "AL"), ("Gadsden", "AL"), ("Rome", "GA"), ("Valdosta", "GA"),
    ("Tifton", "GA"), ("Ocala", "FL"), ("Sebring", "FL"), ("Punta Gorda", "FL"),
    ("Kingsport", "TN"), ("Cookeville", "TN"), ("Bowling Green", "KY"), ("Paducah", "KY"),
    ("Muncie", "IN"), ("Kokomo", "IN"), ("Lima", "OH"), ("Mansfield", "OH"),
    ("Erie", "PA"), ("Altoona", "PA"), ("Johnstown", "PA"), ("Morgantown", "WV"),
    ("Beckley", "WV"), ("Traverse City", "MI"), ("Midland", "MI"), ("Eau Claire", "WI"),
    ("La Crosse", "WI"), ("Mankato", "MN"), ("Bemidji", "MN"), ("Sioux City", "IA"),
    ("Dubuque", "IA"), ("Bismarck", "ND"), ("Minot", "ND"), ("Rapid City", "SD"),
    ("Brookings", "SD"), ("Augusta", "ME"), ("Bangor", "ME"), ("Burlington", "VT"),
    ("Rutland", "VT"), ("Concord", "NH"), ("Keene", "NH"),
]

CATEGORY_KEY = "search_category"
CUSTOM_CATEGORY_KEY = "search_custom_category"
CITY_KEY = "search_city"
STATE_KEY = "search_state"
LIMIT_KEY = "search_limit"


# ── Styles ─────────────────────────────────────────────────────────────────


def inject_styles() -> None:
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@500;600;700;800&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>

        html, body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }

        .main .block-container {
            background: #F8FAFC;
            max-width: 1440px;
            padding: 1.75rem 2rem 3rem;
        }

        /* ── Sidebar ─────────────────────────────────── */
        [data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid #E2E8F0;
        }

        [data-testid="stSidebar"] .block-container {
            padding: 1.5rem 1rem 2rem;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {
            color: #0F172A;
        }

        [data-testid="stSidebar"] hr {
            border-color: #E2E8F0;
            margin: 1rem 0;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] > label {
            display: none;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] {
            gap: 0.1rem;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label {
            align-items: center;
            border: 1px solid transparent;
            border-radius: 8px;
            color: #475569;
            cursor: pointer;
            display: flex;
            font-size: 0.875rem;
            font-weight: 500;
            margin: 0;
            min-height: 2.4rem;
            padding: 0.45rem 0.75rem;
            transition: background 120ms ease, color 120ms ease;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background: #F1F5F9;
            color: #0F172A;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background: #EFF6FF;
            border-color: #BFDBFE;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p,
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) span {
            color: #1D4ED8 !important;
            font-weight: 700;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
            display: none;
        }

        /* ── Brand ───────────────────────────────────── */
        .vc-brand {
            align-items: center;
            display: flex;
            gap: 0.75rem;
            padding: 0.25rem 0.25rem 0.5rem;
        }

        .vc-mark {
            align-items: center;
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
            color: #FFFFFF;
            display: flex;
            font-family: 'Poppins', sans-serif;
            font-size: 0.875rem;
            font-weight: 800;
            height: 2.5rem;
            justify-content: center;
            letter-spacing: -0.02em;
            min-width: 2.5rem;
            width: 2.5rem;
        }

        .vc-name {
            color: #0F172A;
            font-family: 'Poppins', sans-serif;
            font-size: 0.9rem;
            font-weight: 700;
            line-height: 1.15;
        }

        .vc-tagline {
            color: #2563EB;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            margin-top: 0.1rem;
            text-transform: uppercase;
        }

        .sidebar-section-label {
            color: #94A3B8;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            margin-bottom: 0.35rem;
            padding: 0 0.25rem;
            text-transform: uppercase;
        }

        /* ── Page titles ─────────────────────────────── */
        .page-header {
            margin-bottom: 1.5rem;
        }

        .page-title {
            color: #0F172A;
            font-family: 'Poppins', sans-serif;
            font-size: 1.6rem;
            font-weight: 700;
            line-height: 1.2;
            margin: 0 0 0.25rem;
        }

        .page-subtitle {
            color: #64748B;
            font-size: 0.875rem;
            margin: 0;
        }

        /* ── Metric cards ────────────────────────────── */
        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
            padding: 1rem 1.25rem 1.1rem;
        }

        div[data-testid="stMetricLabel"] > div {
            color: #64748B !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        div[data-testid="stMetricValue"] > div {
            color: #0F172A !important;
            font-family: 'Poppins', sans-serif !important;
            font-size: 1.9rem !important;
            font-weight: 700 !important;
        }

        /* ── Data tables ─────────────────────────────── */
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            overflow: hidden;
        }

        /* ── Buttons ─────────────────────────────────── */
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            min-height: 2.5rem;
            transition: all 150ms ease;
        }

        /* ── Containers / expanders ──────────────────── */
        div[data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px;
        }

        /* ── Lead cards ──────────────────────────────── */
        .lead-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            min-height: 200px;
            overflow: hidden;
            padding: 1.25rem 1.25rem 1.25rem 1.5rem;
            position: relative;
        }

        .lead-card::before {
            bottom: 0;
            content: '';
            left: 0;
            position: absolute;
            top: 0;
            width: 4px;
        }

        .lead-card.hot::before  { background: #059669; }
        .lead-card.warm::before { background: #D97706; }
        .lead-card.low::before  { background: #CBD5E1; }

        .lead-card-header {
            align-items: flex-start;
            display: flex;
            gap: 0.75rem;
            justify-content: space-between;
        }

        .lead-title {
            color: #0F172A;
            font-family: 'Poppins', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            line-height: 1.3;
            margin: 0;
        }

        .lead-score {
            background: #F1F5F9;
            border-radius: 7px;
            color: #334155;
            flex: 0 0 auto;
            font-size: 0.82rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
        }

        .lead-meta {
            color: #64748B;
            font-size: 0.8rem;
            line-height: 1.35;
            margin: 0.3rem 0 0.65rem;
        }

        .lead-tier {
            border-radius: 999px;
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            margin-bottom: 0.65rem;
            padding: 0.2rem 0.6rem;
        }

        .lead-tier.hot  { background: #DCFCE7; color: #14532D; }
        .lead-tier.warm { background: #FEF3C7; color: #92400E; }
        .lead-tier.low  { background: #F1F5F9; color: #475569; }

        .lead-facts {
            border-bottom: 1px solid #F1F5F9;
            border-top: 1px solid #F1F5F9;
            display: grid;
            gap: 0.5rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin-bottom: 0.7rem;
            padding: 0.65rem 0;
        }

        .lead-fact-label {
            color: #94A3B8;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }

        .lead-fact-value {
            color: #0F172A;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 0.1rem;
        }

        .lead-signal {
            color: #475569;
            font-size: 0.8rem;
            line-height: 1.5;
        }

        /* ── CRM cards ───────────────────────────────── */
        .crm-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            padding: 1.25rem;
        }

        .crm-card-title {
            color: #0F172A;
            font-family: 'Poppins', sans-serif;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .crm-muted {
            color: #64748B;
            font-size: 0.875rem;
            line-height: 1.5;
        }

        /* ── Status chips ────────────────────────────── */
        .status-chip {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 999px;
            color: #475569;
            display: inline-block;
            font-size: 0.74rem;
            font-weight: 600;
            margin: 0 0.3rem 0.3rem 0;
            padding: 0.2rem 0.6rem;
        }

        /* ── Pipeline stage badges ───────────────────── */
        .stage-badge {
            border-radius: 6px;
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            padding: 0.2rem 0.55rem;
            text-transform: uppercase;
        }

        .stage-new        { background: #F0F9FF; color: #0369A1; }
        .stage-qualified  { background: #EFF6FF; color: #1D4ED8; }
        .stage-contacted  { background: #F3E8FF; color: #7C3AED; }
        .stage-follow-up  { background: #FEF3C7; color: #92400E; }
        .stage-interested { background: #FFF7ED; color: #C2410C; }
        .stage-client     { background: #DCFCE7; color: #14532D; }

        /* ── Project status badges ───────────────────── */
        .proj-badge {
            border-radius: 6px;
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            padding: 0.2rem 0.55rem;
            text-transform: uppercase;
        }

        .proj-planning    { background: #EFF6FF; color: #1D4ED8; }
        .proj-in-progress { background: #FEF3C7; color: #92400E; }
        .proj-review      { background: #F3E8FF; color: #7C3AED; }
        .proj-complete    { background: #DCFCE7; color: #14532D; }
        .proj-on-hold     { background: #F1F5F9; color: #475569; }

        /* ── Info / empty state ──────────────────────── */
        .info-box {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            color: #64748B;
            font-size: 0.9rem;
            line-height: 1.6;
            padding: 1rem 1.25rem;
        }

        /* ── Pipeline bar ────────────────────────────── */
        .pipeline-bar-wrap {
            background: #F1F5F9;
            border-radius: 999px;
            height: 8px;
            margin-top: 0.5rem;
            overflow: hidden;
            width: 100%;
        }

        .pipeline-bar-fill {
            background: linear-gradient(90deg, #2563EB, #059669);
            border-radius: 999px;
            height: 100%;
            transition: width 300ms ease;
        }

        /* ── Section divider label ───────────────────── */
        .section-label {
            color: #94A3B8;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            margin-bottom: 0.75rem;
            margin-top: 2rem;
            text-transform: uppercase;
        }

        /* Hide "Press Enter to submit form" */
        small[data-testid="InputInstructions"],
        .stForm .stButton small,
        [data-testid="stFormSubmitButton"] ~ small,
        .stForm small {
            display: none !important;
        }

        /* Primary buttons always blue */
        button[kind="primaryFormSubmit"],
        button[kind="primary"],
        [data-testid="stFormSubmitButton"] {
            background-color: #2563EB !important;
            border-color: #2563EB !important;
            color: #FFFFFF !important;
        }

        button[kind="primaryFormSubmit"]:hover,
        button[kind="primary"]:hover {
            background-color: #1D4ED8 !important;
            border-color: #1D4ED8 !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
    # If user just logged in, set the auth cookie on this render (after rerun).
    # st.markdown strips <script> via innerHTML; st_components.html() actually runs JS.
    token = st.session_state.pop("_set_auth_cookie", None)
    if token:
        st_components.html(
            f'<script>try{{parent.document.cookie="vc_auth={token};path=/;max-age=2592000;SameSite=Strict"}}catch(e){{document.cookie="vc_auth={token};path=/;max-age=2592000;SameSite=Strict"}}</script>',
            height=0,
        )


# ── Pipeline / App setup ───────────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def get_pipeline() -> LeadPipeline:
    settings = get_settings()
    database = LeadDatabase(settings.sqlite_path, settings.database_url)
    search_service = RapidAPIBusinessSearch(settings)
    website_analyzer = WebsiteAnalyzer(settings)
    ai_enricher = LeadAIEnricher(settings)
    return LeadPipeline(
        settings=settings,
        database=database,
        search_service=search_service,
        website_analyzer=website_analyzer,
        ai_enricher=ai_enricher,
    )


def ensure_dashboard_database(pipeline: LeadPipeline) -> None:
    required_methods = (
        "update_lead_management",
        "fetch_lead_events",
        "fetch_saved_searches",
        "record_saved_search",
    )
    if all(hasattr(pipeline.database, method_name) for method_name in required_methods):
        return
    st.cache_resource.clear()
    st.warning("LeadFinder refreshed its database connection. Reloading...")
    st.rerun()


def init_state() -> None:
    st.session_state.setdefault("last_results", pd.DataFrame())
    st.session_state.setdefault("last_run_summary", "")
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault(CATEGORY_KEY, SUGGESTED_CATEGORIES[0])
    st.session_state.setdefault(CUSTOM_CATEGORY_KEY, "")
    st.session_state.setdefault(CITY_KEY, "")
    st.session_state.setdefault(STATE_KEY, STATE_PLACEHOLDER)
    st.session_state.setdefault(LIMIT_KEY, 30)


# ── Helpers ────────────────────────────────────────────────────────────────


def state_name(value: str) -> str:
    if value in STATE_ABBR_TO_NAME:
        return STATE_ABBR_TO_NAME[value]
    return value


def state_abbr(value: str) -> str:
    if value in STATE_NAME_TO_ABBR:
        return STATE_NAME_TO_ABBR[value]
    return value


def render_note(message: str) -> None:
    st.markdown(f'<div class="info-box">{html.escape(message)}</div>', unsafe_allow_html=True)


def _auth_token(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()[:40]


def require_password() -> bool:
    settings = get_settings()
    if not settings.app_password:
        return True
    if st.session_state.get("authenticated", False):
        return True

    # Check persistent cookie — works across tabs and browser restarts
    expected = _auth_token(settings.app_password)
    if st.context.cookies.get("vc_auth", "") == expected:
        st.session_state["authenticated"] = True
        return True

    # Login screen — single centered column, everything in one block
    st.markdown(
        """
        <style>
        .main .block-container {
            background: #F0F4FF;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding-top: 0 !important;
        }
        /* Remove form border */
        .stForm { border: none !important; padding: 0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            """
            <div style="
                background:#FFFFFF;
                border:1px solid #E2E8F0;
                border-radius:20px;
                box-shadow:0 8px 40px rgba(37,99,235,0.1),0 2px 8px rgba(0,0,0,0.06);
                padding:2.5rem 2.25rem 1.75rem;
                margin-top:4rem;
            ">
                <div style="
                    display:flex;align-items:center;justify-content:center;
                    background:linear-gradient(135deg,#2563EB 0%,#1D4ED8 100%);
                    border-radius:14px;
                    box-shadow:0 4px 16px rgba(37,99,235,0.4);
                    color:#fff;
                    font-family:Poppins,sans-serif;
                    font-size:1.1rem;font-weight:800;
                    height:3.25rem;
                    letter-spacing:-0.02em;
                    margin:0 auto 1.25rem;
                    width:3.25rem;
                ">VC</div>
                <div style="
                    color:#0F172A;
                    font-family:Poppins,sans-serif;
                    font-size:1.35rem;font-weight:700;
                    margin-bottom:0.3rem;
                    text-align:center;
                ">Vanguard Creatives</div>
                <div style="color:#64748B;font-size:0.82rem;text-align:center;margin-bottom:1.75rem;">
                    Enter your team password to continue
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("password_gate", border=False):
            password = st.text_input(
                "Password", type="password",
                label_visibility="collapsed",
                placeholder="Team password",
            )
            submitted = st.form_submit_button(
                "Unlock Suite", type="primary", use_container_width=True,
            )
        if submitted:
            if password == settings.app_password:
                token = _auth_token(settings.app_password)
                st.session_state["authenticated"] = True
                # Store token — inject_styles() picks this up on the rerun and sets the browser cookie
                st.session_state["_set_auth_cookie"] = token
                st.rerun()
            else:
                st.error("Wrong password.")
    return False


def pick_random_market(preferred_state: str = "") -> tuple[str, str]:
    markets = SMALL_TOWN_MARKETS
    if preferred_state:
        preferred_state = state_abbr(preferred_state)
        state_matches = [m for m in SMALL_TOWN_MARKETS if m[1] == preferred_state]
        if state_matches:
            markets = state_matches
    return random.choice(markets)


def signal_matches(signal_text: str, reviews: int | float | None, website: str, selected_signal: str) -> bool:
    normalized = str(signal_text).lower()
    has_website = bool(str(website).strip())
    review_count = int(reviews) if pd.notna(reviews) and reviews not in ("", None) else None

    if selected_signal == "No website":
        return (not has_website) or "no website" in normalized
    if selected_signal == "Outdated website":
        return any(p in normalized for p in ("stale", "dated", "table-heavy", "thin", "modern image formats"))
    if selected_signal == "Mobile issues":
        return any(p in normalized for p in ("mobile", "viewport"))
    if selected_signal == "Family-owned angle":
        return any(p in normalized for p in ("family-owned", "family owned", "locally rooted"))
    if selected_signal == "Low reviews":
        return review_count is not None and review_count <= 15
    return True


def first_line(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.splitlines()[0].strip()


def truncate_text(value: object, limit: int = 170) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return f"{text[:limit - 3].rstrip()}..."


def calculate_opportunity_score(row: pd.Series) -> int:
    signal_text = str(row.get("Key Signals", "")).lower()
    website = str(row.get("Website", "")).strip()
    rating = row.get("Rating")
    reviews = row.get("Reviews")
    review_count = int(reviews) if pd.notna(reviews) and reviews not in ("", None) else None
    rating_value = float(rating) if pd.notna(rating) and rating not in ("", None) else 0.0

    score = 35
    if not website or "no website" in signal_text:
        score += 25
    if any(t in signal_text for t in ("stale", "dated", "table-heavy", "thin", "modern image formats")):
        score += 20
    if any(t in signal_text for t in ("mobile", "viewport")):
        score += 15
    if any(t in signal_text for t in ("family-owned", "family owned", "locally rooted")):
        score += 10
    if review_count is not None:
        if review_count <= 15:
            score += 15
        elif review_count <= 40:
            score += 8
        elif review_count >= 150:
            score -= 8
    if rating_value >= 4.7:
        score += 8
    elif rating_value and rating_value < 4.0:
        score -= 10
    return max(0, min(100, score))


def opportunity_tier(score: int) -> str:
    if score >= 75:
        return "Hot"
    if score >= 55:
        return "Warm"
    return "Low"


def prepare_results_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    prepared = df.copy()
    prepared["Opportunity Score"] = prepared.apply(calculate_opportunity_score, axis=1)
    prepared["Opportunity"] = prepared["Opportunity Score"].apply(opportunity_tier)
    prepared["Website Status"] = prepared["Website"].astype(str).str.strip().apply(
        lambda v: "Has website" if v else "No website"
    )
    prepared["Primary Signal"] = prepared["Key Signals"].apply(first_line)
    return sort_results(prepared, "Best opportunity first").reset_index(drop=True)


def tier_class(tier: str) -> str:
    t = str(tier).strip().lower()
    return t if t in {"hot", "warm", "low"} else "low"


def sort_results(df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
    if sort_by == "Best opportunity first" and "Opportunity Score" in df.columns:
        return df.sort_values(
            by=["Opportunity Score", "Reviews", "Business Name"],
            ascending=[False, True, True], na_position="last",
        )
    if sort_by == "Highest rating first":
        return df.sort_values(
            by=["Rating", "Reviews", "Business Name"],
            ascending=[False, False, True], na_position="last",
        )
    if sort_by == "Business name A-Z":
        return df.sort_values(by=["Business Name"], ascending=[True], na_position="last")
    return df.sort_values(by=["Reviews", "Business Name"], ascending=[True, True], na_position="last")


def filter_results(
    df: pd.DataFrame,
    keyword: str,
    max_reviews: int,
    min_rating: float,
    website_filter: str,
    signal_filter: str,
    opportunity_filter: str,
    sort_by: str,
) -> pd.DataFrame:
    filtered = df.copy()
    if keyword.strip():
        haystack = filtered.astype(str).agg(" ".join, axis=1).str.lower()
        filtered = filtered[haystack.str.contains(keyword.strip().lower(), na=False)]
    if "Reviews" in filtered.columns:
        filtered = filtered[filtered["Reviews"].fillna(0) <= max_reviews]
    if "Rating" in filtered.columns:
        filtered = filtered[filtered["Rating"].fillna(0) >= min_rating]
    if website_filter == "Has website":
        filtered = filtered[filtered["Website"].astype(str).str.strip() != ""]
    elif website_filter == "No website":
        filtered = filtered[filtered["Website"].astype(str).str.strip() == ""]
    if signal_filter != "Any":
        filtered = filtered[
            filtered.apply(
                lambda row: signal_matches(
                    row.get("Key Signals", ""), row.get("Reviews"),
                    row.get("Website", ""), signal_filter,
                ),
                axis=1,
            )
        ]
    if opportunity_filter != "Any" and "Opportunity" in filtered.columns:
        filtered = filtered[filtered["Opportunity"] == opportunity_filter]
    filtered = sort_results(filtered, sort_by)
    return filtered.reset_index(drop=True)


def filter_history(
    df: pd.DataFrame,
    keyword: str,
    status: str,
    priority: str,
    state: str,
    website_filter: str,
    due_only: bool,
) -> pd.DataFrame:
    filtered = df.copy()
    if status != "All":
        filtered = filtered[filtered["status"] == status]
    if priority != "All":
        filtered = filtered[filtered["priority"] == priority]
    if state != "All":
        filtered = filtered[filtered["state"].apply(state_name) == state]
    if website_filter == "Has website":
        filtered = filtered[filtered["website"].astype(str).str.strip() != ""]
    elif website_filter == "No website":
        filtered = filtered[filtered["website"].astype(str).str.strip() == ""]
    if due_only:
        due_dates = parse_date_series(filtered["next_follow_up_at"])
        filtered = filtered[due_dates.notna() & (due_dates <= pd.Timestamp(date.today()))]
    if keyword.strip():
        haystack = filtered.astype(str).agg(" ".join, axis=1).str.lower()
        filtered = filtered[haystack.str.contains(keyword.strip().lower(), na=False)]
    return filtered.reset_index(drop=True)


def parse_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.replace("", pd.NA), errors="coerce")


def count_due_followups(df: pd.DataFrame) -> int:
    if df.empty or "next_follow_up_at" not in df.columns:
        return 0
    due_dates = parse_date_series(df["next_follow_up_at"])
    return int((due_dates.notna() & (due_dates <= pd.Timestamp(date.today()))).sum())


def list_text(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if str(item).strip())
    return str(value or "")


def display_date(value: object) -> str:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return "-"
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return str(value)
    return parsed.date().isoformat()


def format_event_value(value: object) -> str:
    text = str(value or "").strip()
    return text if text else "blank"


def crm_table(history_df: pd.DataFrame) -> pd.DataFrame:
    table = history_df.copy()
    table["State"] = table["state"].apply(state_name)
    table["Website Status"] = table["website"].astype(str).str.strip().apply(
        lambda v: "Has website" if v else "No website"
    )
    table["Signals"] = table["key_signals"].apply(list_text)
    table["Openers"] = table["personalized_openers"].apply(list_text)
    return table.rename(
        columns={
            "id": "Lead ID",
            "business_name": "Business Name",
            "category": "Category",
            "city": "City",
            "location": "Location",
            "phone": "Phone",
            "website": "Website",
            "rating": "Rating",
            "reviews": "Reviews",
            "status": "Status",
            "priority": "Priority",
            "contact_method": "Contact Method",
            "email": "Email",
            "owner_name": "Owner Name",
            "last_contacted_at": "Last Contacted",
            "next_follow_up_at": "Next Follow Up",
            "status_reason": "Status Reason",
            "notes": "Notes",
            "created_at": "Created At",
            "updated_at": "Updated At",
            "last_seen_at": "Last Seen",
        }
    )


def management_update_frame(edited: pd.DataFrame) -> pd.DataFrame:
    updates = edited.rename(
        columns={
            "Lead ID": "id",
            "Status": "status",
            "Priority": "priority",
            "Contact Method": "contact_method",
            "Email": "email",
            "Owner Name": "owner_name",
            "Last Contacted": "last_contacted_at",
            "Next Follow Up": "next_follow_up_at",
            "Status Reason": "status_reason",
            "Notes": "notes",
        }
    )
    return updates[[
        "id", "status", "priority", "contact_method", "email", "owner_name",
        "last_contacted_at", "next_follow_up_at", "status_reason", "notes",
    ]]


def style_results_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    def opportunity_style(value: object) -> str:
        if value == "Hot":
            return "background-color: #DCFCE7; color: #14532D; font-weight: 700;"
        if value == "Warm":
            return "background-color: #FEF3C7; color: #713F12; font-weight: 700;"
        return "background-color: #F1F5F9; color: #334155; font-weight: 700;"

    def website_style(value: object) -> str:
        if value == "No website":
            return "background-color: #FEF2F2; color: #7F1D1D; font-weight: 700;"
        return "background-color: #F1F5F9; color: #334155;"

    return df.style.map(opportunity_style, subset=["Opportunity"]).map(website_style, subset=["Website Status"])


# ── Sidebar ────────────────────────────────────────────────────────────────


def render_suite_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="vc-brand">
                <div class="vc-mark">VC</div>
                <div>
                    <div class="vc-name">Vanguard Creatives</div>
                    <div class="vc-tagline">CPM Suite</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown('<div class="sidebar-section-label">Workspace</div>', unsafe_allow_html=True)
        page = st.radio(
            "Navigation",
            ["Dashboard", "Pipeline", "Leads", "Follow Ups", "Clients", "Projects", "LeadFinder", "Activity"],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown(
            '<div style="color:#94A3B8;font-size:0.72rem;padding:0 0.25rem;">'
            'Build &middot; Manage &middot; Optimize &middot; Fix'
            '</div>',
            unsafe_allow_html=True,
        )
    return page


# ── Dashboard ──────────────────────────────────────────────────────────────


def render_command_center(pipeline: LeadPipeline, history_df: pd.DataFrame) -> None:
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Dashboard</div>'
        '<div class="page-subtitle">Overview of your pipeline, follow-ups, and client activity</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    total = len(history_df)
    active_count = int(history_df["status"].isin(ACTIVE_STATUS_OPTIONS).sum()) if not history_df.empty else 0
    due_count = count_due_followups(history_df)
    client_count = int((history_df["status"] == "Client").sum()) if not history_df.empty else 0
    urgent_count = int(history_df["priority"].isin(["High", "Urgent"]).sum()) if not history_df.empty else 0

    try:
        projects_df = pipeline.database.fetch_projects()
        active_projects = int((projects_df["status"].isin(["Planning", "In Progress", "Review"])).sum()) if not projects_df.empty else 0
    except Exception:  # noqa: BLE001
        active_projects = 0

    m = st.columns(5)
    with m[0]:
        st.metric("Total Leads", f"{total:,}")
    with m[1]:
        st.metric("Active Pipeline", f"{active_count:,}")
    with m[2]:
        st.metric("Follow Ups Due", f"{due_count:,}")
    with m[3]:
        st.metric("Clients", f"{client_count:,}")
    with m[4]:
        st.metric("Active Projects", f"{active_projects:,}")

    st.write("")

    left, right = st.columns([1.35, 1])

    with left:
        st.markdown('<div class="section-label">Pipeline by Status</div>', unsafe_allow_html=True)
        if not history_df.empty:
            status_counts = (
                history_df["status"].fillna("New").value_counts()
                .rename_axis("Status").reset_index(name="Count")
            )
            st.dataframe(
                status_counts,
                hide_index=True,
                width="stretch",
                height=min(40 * len(status_counts) + 40, 380),
                column_config={"Count": st.column_config.ProgressColumn("Count", min_value=0, max_value=int(status_counts["Count"].max()), format="%d")},
            )
        else:
            render_note("No leads yet. Run a LeadFinder search to get started.")

    with right:
        st.markdown('<div class="section-label">Attention Queue</div>', unsafe_allow_html=True)
        no_website_count = int((history_df["website"].astype(str).str.strip() == "").sum()) if not history_df.empty else 0
        attention_rows = [
            {"Queue": "Follow-ups due today", "Count": due_count},
            {"Queue": "High / urgent priority", "Count": urgent_count},
            {"Queue": "Leads without website", "Count": no_website_count},
            {"Queue": "Active clients", "Count": client_count},
        ]
        st.dataframe(
            pd.DataFrame(attention_rows),
            hide_index=True,
            width="stretch",
            height=220,
        )

        if not history_df.empty:
            st.markdown('<div class="section-label" style="margin-top:1.25rem;">Funnel Progress</div>', unsafe_allow_html=True)
            pipeline_flow = ["New", "Qualified", "Contacted", "Interested", "Client"]
            for stage in pipeline_flow:
                n = int((history_df["status"] == stage).sum())
                pct = round(n / max(total, 1) * 100)
                st.markdown(
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'font-size:0.8rem;color:#475569;margin-bottom:0.4rem;">'
                    f'<span>{stage}</span><span style="font-weight:600;color:#0F172A;">{n}</span></div>'
                    f'<div class="pipeline-bar-wrap">'
                    f'<div class="pipeline-bar-fill" style="width:{pct}%;"></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.write("")

    st.markdown('<div class="section-label">Recent Leads</div>', unsafe_allow_html=True)
    if not history_df.empty:
        sheet = crm_table(history_df)
        preview_cols = [
            "Business Name", "Status", "Priority", "City", "State",
            "Contact Method", "Last Contacted", "Next Follow Up", "Status Reason", "Notes",
        ]
        st.dataframe(sheet[preview_cols].head(20), hide_index=True, width="stretch", height=400)

    searches = pipeline.database.fetch_saved_searches(limit=5)
    if not searches.empty:
        st.markdown('<div class="section-label">Recent LeadFinder Searches</div>', unsafe_allow_html=True)
        sd = searches.copy()
        sd["state"] = sd["state"].apply(state_name)
        st.dataframe(
            sd.rename(columns={
                "category": "Category", "city": "City", "state": "State",
                "result_count": "Results", "created_at": "Run At",
            })[["Run At", "Category", "City", "State", "Results"]],
            hide_index=True,
            width="stretch",
        )


# ── Pipeline View ──────────────────────────────────────────────────────────


def render_pipeline_tab(history_df: pd.DataFrame) -> None:
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Pipeline</div>'
        '<div class="page-subtitle">Leads organized by stage from prospect to client</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if history_df.empty:
        render_note("No leads in the pipeline yet.")
        return

    stage_colors = {
        "New": ("stage-new", "#0369A1"),
        "Qualified": ("stage-qualified", "#1D4ED8"),
        "Pending": ("stage-qualified", "#1D4ED8"),
        "Contacted": ("stage-contacted", "#7C3AED"),
        "Follow Up": ("stage-follow-up", "#92400E"),
        "Interested": ("stage-interested", "#C2410C"),
        "Client": ("stage-client", "#14532D"),
        "Not Fit": ("stage-new", "#64748B"),
        "No Response": ("stage-new", "#64748B"),
        "Failed": ("stage-new", "#64748B"),
        "Dead": ("stage-new", "#64748B"),
    }

    active_stages = PIPELINE_STAGES
    stage_dfs = {stage: history_df[history_df["status"] == stage] for stage in active_stages}

    m = st.columns(len(active_stages))
    for col, stage in zip(m, active_stages):
        n = len(stage_dfs[stage])
        badge_class, color = stage_colors.get(stage, ("stage-new", "#64748B"))
        with col:
            st.markdown(
                f'<div style="text-align:center;padding:0.75rem 0.5rem;">'
                f'<div class="stage-badge {badge_class}" style="margin-bottom:0.5rem;">{stage}</div>'
                f'<div style="font-family:Poppins,sans-serif;font-size:1.5rem;font-weight:700;color:#0F172A;">{n}</div>'
                f'<div style="font-size:0.72rem;color:#94A3B8;">'
                f'{"lead" if n == 1 else "leads"}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")
    st.markdown('<div class="section-label">Stage Details</div>', unsafe_allow_html=True)

    for stage in active_stages:
        df = stage_dfs[stage]
        if df.empty:
            continue
        badge_class, _ = stage_colors.get(stage, ("stage-new", "#64748B"))
        with st.expander(f"{stage}  ·  {len(df)} lead{'s' if len(df) != 1 else ''}", expanded=(stage in {"Follow Up", "Interested"})):
            sheet = crm_table(df)
            cols = ["Business Name", "City", "State", "Priority", "Contact Method", "Last Contacted", "Next Follow Up", "Notes"]
            st.dataframe(
                sheet[cols],
                hide_index=True,
                width="stretch",
                height=min(45 * len(df) + 45, 420),
                column_config={
                    "Priority": st.column_config.TextColumn("Priority"),
                },
            )

    st.markdown('<div class="section-label">Other Statuses</div>', unsafe_allow_html=True)
    other_statuses = [s for s in LEAD_STATUS_OPTIONS if s not in active_stages]
    other_rows = []
    for s in other_statuses:
        n = int((history_df["status"] == s).sum())
        if n > 0:
            other_rows.append({"Status": s, "Count": n})
    if other_rows:
        st.dataframe(pd.DataFrame(other_rows), hide_index=True, width="stretch")
    else:
        render_note("No leads in other statuses.")


# ── Leads ──────────────────────────────────────────────────────────────────


def render_leads_tab(pipeline: LeadPipeline) -> None:
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Leads</div>'
        '<div class="page-subtitle">All leads — filter, search, and update statuses inline</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    history_df = pipeline.database.fetch_all_leads()

    if history_df.empty:
        render_note("No leads found. Run a LeadFinder search to add leads.")
        return

    state_options = ["All", *sorted(history_df["state"].dropna().apply(state_name).unique())]
    filter_cols = st.columns([2.2, 0.9, 0.9, 0.9, 0.8])
    with filter_cols[0]:
        keyword = st.text_input("Search leads", key="lead_filter", placeholder="Business, city, phone, signals, opener, notes…")
    with filter_cols[1]:
        status = st.selectbox("Status", STATUS_FILTER_OPTIONS, index=0, key="lead_status_filter")
    with filter_cols[2]:
        priority = st.selectbox("Priority", ["All", *PRIORITY_OPTIONS], index=0, key="lead_priority_filter")
    with filter_cols[3]:
        selected_state = st.selectbox("State", state_options, index=0, key="lead_state_filter")
    with filter_cols[4]:
        website_filter = st.selectbox("Website", WEBSITE_FILTER_OPTIONS, index=0, key="lead_website_filter")

    due_only = st.checkbox("Show only follow-ups due today or earlier", key="lead_due_filter")
    filtered = filter_history(history_df, keyword, status, priority, selected_state, website_filter, due_only)

    m = st.columns(4)
    with m[0]:
        st.metric("Visible", f"{len(filtered):,}")
    with m[1]:
        st.metric("High Priority", f"{int(filtered['priority'].isin(['High', 'Urgent']).sum()):,}" if not filtered.empty else "0")
    with m[2]:
        st.metric("Follow Ups Due", f"{count_due_followups(filtered):,}")
    with m[3]:
        st.metric("No Website", f"{int((filtered['website'].astype(str).str.strip() == '').sum()):,}" if not filtered.empty else "0")

    if filtered.empty:
        render_note("No leads match the current filters.")
        return

    display_df = crm_table(filtered)
    editable_columns = [
        "Lead ID", "Business Name", "Category", "City", "State", "Phone",
        "Website", "Website Status", "Rating", "Reviews", "Status", "Priority",
        "Contact Method", "Email", "Owner Name", "Last Contacted",
        "Next Follow Up", "Status Reason", "Notes", "Created At",
    ]
    editable = display_df[editable_columns].copy()
    editable["Status"] = editable["Status"].where(editable["Status"].isin(LEAD_STATUS_OPTIONS), "New")
    editable["Priority"] = editable["Priority"].where(editable["Priority"].isin(PRIORITY_OPTIONS), "Medium")
    editable["Contact Method"] = editable["Contact Method"].where(editable["Contact Method"].isin(CONTACT_METHOD_OPTIONS), "")
    editable["Last Contacted"] = pd.to_datetime(editable["Last Contacted"].replace("", pd.NA), errors="coerce")
    editable["Next Follow Up"] = pd.to_datetime(editable["Next Follow Up"].replace("", pd.NA), errors="coerce")

    st.write("")
    edited = st.data_editor(
        editable,
        height=560,
        hide_index=True,
        width="stretch",
        disabled=["Lead ID", "Business Name", "Category", "City", "State", "Phone", "Website", "Website Status", "Rating", "Reviews", "Created At"],
        column_config={
            "Website": st.column_config.LinkColumn("Website", display_text="Open"),
            "Status": st.column_config.SelectboxColumn("Status", options=LEAD_STATUS_OPTIONS, required=True),
            "Priority": st.column_config.SelectboxColumn("Priority", options=PRIORITY_OPTIONS, required=True),
            "Contact Method": st.column_config.SelectboxColumn("Contact Method", options=CONTACT_METHOD_OPTIONS),
            "Last Contacted": st.column_config.DateColumn("Last Contacted", format="YYYY-MM-DD"),
            "Next Follow Up": st.column_config.DateColumn("Next Follow Up", format="YYYY-MM-DD"),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
            "Reviews": st.column_config.NumberColumn("Reviews", format="%d"),
        },
        key="lead_management_editor",
    )

    save_cols = st.columns([1.1, 4])
    with save_cols[0]:
        if st.button("Save Changes", type="primary", width="stretch"):
            pipeline.database.update_lead_management(management_update_frame(edited))
            st.success("Lead updates saved.")
            st.cache_resource.clear()
            st.rerun()

    st.write("")
    render_lead_detail(filtered, pipeline)


def render_lead_detail(filtered: pd.DataFrame, pipeline: LeadPipeline) -> None:
    st.markdown('<div class="section-label">Lead Detail</div>', unsafe_allow_html=True)
    options = {
        f"{row.business_name} · {row.city}, {state_name(row.state)} · #{row.id}": int(row.id)
        for row in filtered.itertuples()
    }
    selected_label = st.selectbox("Open a lead", list(options.keys()), key="lead_detail_select")
    selected_id = options[selected_label]
    lead = filtered[filtered["id"] == selected_id].iloc[0]

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown(
            f"""
            <div class="crm-card">
                <div class="crm-card-title">{html.escape(str(lead["business_name"]))}</div>
                <div class="crm-muted">{html.escape(str(lead["location"] or f'{lead["city"]}, {state_name(lead["state"])}'))}</div>
                <br>
                <span class="status-chip">{html.escape(str(lead["status"]))}</span>
                <span class="status-chip">{html.escape(str(lead["priority"]))} priority</span>
                <span class="status-chip">{html.escape(str(lead["reviews"] if pd.notna(lead["reviews"]) else 0))} reviews</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        details = {
            "Phone": lead["phone"] or "-",
            "Website": lead["website"] or "-",
            "Email": lead["email"] or "-",
            "Owner / Contact": lead["owner_name"] or "-",
            "Contact Method": lead["contact_method"] or "-",
            "Last Contacted": display_date(lead["last_contacted_at"]),
            "Next Follow Up": display_date(lead["next_follow_up_at"]),
            "Status Reason": lead["status_reason"] or "-",
            "Notes": lead["notes"] or "-",
        }
        st.dataframe(pd.DataFrame(details.items(), columns=["Field", "Value"]), hide_index=True, width="stretch")

    with right:
        st.markdown("**Website Signals**")
        signals = lead["key_signals"] if isinstance(lead["key_signals"], list) else []
        if signals:
            for sig in signals:
                st.write(f"- {sig}")
        else:
            st.caption("No signals saved for this lead.")

        st.markdown("**Personalized Openers**")
        openers = lead["personalized_openers"] if isinstance(lead["personalized_openers"], list) else []
        if openers:
            for opener in openers:
                st.write(f"- {opener}")
        else:
            st.caption("No openers saved for this lead.")

    events = pipeline.database.fetch_lead_events(limit=300)
    lead_events = events[events["lead_id"] == selected_id] if not events.empty else pd.DataFrame()
    if not lead_events.empty:
        st.markdown("**Activity Log**")
        event_display = lead_events[["created_at", "field_name", "old_value", "new_value"]].copy()
        event_display["Change"] = event_display.apply(
            lambda row: f"{row['field_name']}: {format_event_value(row['old_value'])} → {format_event_value(row['new_value'])}",
            axis=1,
        )
        st.dataframe(event_display[["created_at", "Change"]], hide_index=True, width="stretch", height=220)


# ── Follow Ups ─────────────────────────────────────────────────────────────


def render_followups_tab(pipeline: LeadPipeline) -> None:
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Follow Ups</div>'
        '<div class="page-subtitle">Leads that need a call, email, or check-in</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    history_df = pipeline.database.fetch_all_leads()

    if history_df.empty:
        render_note("No follow ups.")
        return

    due_dates = parse_date_series(history_df["next_follow_up_at"])
    today = date.today()
    mode = st.radio(
        "View",
        ["Due now", "All scheduled", "Needs a follow-up date"],
        horizontal=True,
        key="followup_mode",
    )

    if mode == "Due now":
        filtered = history_df[due_dates.notna() & (due_dates <= pd.Timestamp(today))].copy()
    elif mode == "All scheduled":
        filtered = history_df[due_dates.notna()].copy()
    else:
        filtered = history_df[history_df["status"].isin(ACTIVE_STATUS_OPTIONS) & due_dates.isna()].copy()

    if filtered.empty:
        render_note("No follow ups in this view.")
        return

    filtered = filtered.sort_values(
        by=["next_follow_up_at", "priority", "business_name"],
        ascending=[True, False, True], na_position="last",
    )
    display_df = crm_table(filtered)
    followup_columns = [
        "Lead ID", "Business Name", "City", "State", "Status", "Priority",
        "Contact Method", "Phone", "Website", "Last Contacted", "Next Follow Up",
        "Status Reason", "Notes",
    ]
    editable = display_df[followup_columns].copy()
    editable["Last Contacted"] = pd.to_datetime(editable["Last Contacted"].replace("", pd.NA), errors="coerce")
    editable["Next Follow Up"] = pd.to_datetime(editable["Next Follow Up"].replace("", pd.NA), errors="coerce")

    edited = st.data_editor(
        editable,
        height=580,
        hide_index=True,
        width="stretch",
        disabled=["Lead ID", "Business Name", "City", "State", "Phone", "Website"],
        column_config={
            "Website": st.column_config.LinkColumn("Website", display_text="Open"),
            "Status": st.column_config.SelectboxColumn("Status", options=LEAD_STATUS_OPTIONS, required=True),
            "Priority": st.column_config.SelectboxColumn("Priority", options=PRIORITY_OPTIONS, required=True),
            "Contact Method": st.column_config.SelectboxColumn("Contact Method", options=CONTACT_METHOD_OPTIONS),
            "Last Contacted": st.column_config.DateColumn("Last Contacted", format="YYYY-MM-DD"),
            "Next Follow Up": st.column_config.DateColumn("Next Follow Up", format="YYYY-MM-DD"),
        },
        key="followup_editor",
    )

    if st.button("Save Follow Up Updates", type="primary", width="stretch"):
        existing = crm_table(filtered)
        for column in ["Email", "Owner Name"]:
            edited[column] = existing[column].values
        pipeline.database.update_lead_management(management_update_frame(edited))
        st.success("Follow-up updates saved.")
        st.cache_resource.clear()
        st.rerun()


# ── Clients ────────────────────────────────────────────────────────────────


def render_clients_tab(pipeline: LeadPipeline) -> None:
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Clients</div>'
        '<div class="page-subtitle">Active clients and high-interest leads</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    history_df = pipeline.database.fetch_all_leads()

    if history_df.empty:
        render_note("No clients yet.")
        return

    clients = history_df[history_df["status"] == "Client"].copy()
    if clients.empty:
        render_note("No clients yet. Mark a lead as 'Client' in the Leads tab to see them here.")
        active = history_df[history_df["status"].isin(["Interested", "Follow Up", "Contacted", "Qualified"])].copy()
        if active.empty:
            return
        st.markdown('<div class="section-label">High-Interest Leads</div>', unsafe_allow_html=True)
        clients = active

    m = st.columns(3)
    with m[0]:
        st.metric("Clients", f"{len(clients):,}")
    with m[1]:
        has_email = int(clients["email"].astype(str).str.strip().ne("").sum())
        st.metric("Have Email", f"{has_email:,}")
    with m[2]:
        has_website = int(clients["website"].astype(str).str.strip().ne("").sum())
        st.metric("Have Website", f"{has_website:,}")

    st.write("")
    display_df = crm_table(clients)
    board_columns = [
        "Business Name", "Category", "City", "State", "Priority",
        "Owner Name", "Email", "Phone", "Website",
        "Last Contacted", "Next Follow Up", "Status Reason", "Notes",
    ]
    st.dataframe(
        display_df[board_columns],
        hide_index=True,
        width="stretch",
        height=560,
        column_config={"Website": st.column_config.LinkColumn("Website", display_text="Open")},
    )


# ── Projects ───────────────────────────────────────────────────────────────


def render_projects_tab(pipeline: LeadPipeline) -> None:
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Projects</div>'
        '<div class="page-subtitle">Track website builds, fixes, optimizations, and maintenance</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        projects_df = pipeline.database.fetch_projects()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load projects: {exc}")
        return

    active_statuses = {"Planning", "In Progress", "Review"}
    active_count = int(projects_df["status"].isin(active_statuses).sum()) if not projects_df.empty else 0
    complete_count = int((projects_df["status"] == "Complete").sum()) if not projects_df.empty else 0
    total_value = float(projects_df["value"].sum()) if not projects_df.empty else 0.0

    today_str = date.today().isoformat()
    overdue_count = 0
    if not projects_df.empty:
        overdue_count = int(
            (
                projects_df["due_date"].astype(str).str.strip().ne("")
                & (projects_df["due_date"].astype(str) < today_str)
                & projects_df["status"].isin(active_statuses)
            ).sum()
        )

    m = st.columns(4)
    with m[0]:
        st.metric("Total Projects", f"{len(projects_df):,}")
    with m[1]:
        st.metric("Active", f"{active_count:,}")
    with m[2]:
        st.metric("Overdue", f"{overdue_count:,}")
    with m[3]:
        st.metric("Total Value", f"${total_value:,.0f}")

    st.write("")

    with st.expander("+ Add New Project", expanded=projects_df.empty):
        with st.form("add_project_form"):
            col1, col2 = st.columns(2)
            with col1:
                proj_name = st.text_input("Project Name *", placeholder="Johnson Plumbing Website Rebuild")
                client = st.text_input("Client Name", placeholder="Johnson Plumbing Co.")
                proj_type = st.selectbox("Project Type", PROJECT_TYPE_OPTIONS)
                proj_value = st.number_input("Project Value ($)", min_value=0.0, step=100.0, format="%.0f")
            with col2:
                proj_status = st.selectbox("Status", PROJECT_STATUS_OPTIONS)
                proj_priority = st.selectbox("Priority", PRIORITY_OPTIONS, index=1)
                start_date = st.date_input("Start Date", value=None)
                due_date = st.date_input("Due Date", value=None)
            notes = st.text_area("Notes", placeholder="Project scope, deliverables, client notes…")
            submitted = st.form_submit_button("Add Project", type="primary")
            if submitted:
                if not proj_name.strip():
                    st.error("Project Name is required.")
                else:
                    pipeline.database.save_project({
                        "id": None,
                        "lead_id": None,
                        "project_name": proj_name.strip(),
                        "client_name": client.strip(),
                        "project_type": proj_type,
                        "status": proj_status,
                        "priority": proj_priority,
                        "start_date": start_date.isoformat() if start_date else "",
                        "due_date": due_date.isoformat() if due_date else "",
                        "completion_date": "",
                        "value": proj_value,
                        "notes": notes.strip(),
                    })
                    st.success(f"Project '{proj_name.strip()}' added.")
                    st.cache_resource.clear()
                    st.rerun()

    if projects_df.empty:
        render_note("No projects yet. Add your first project above.")
        return

    st.markdown('<div class="section-label">All Projects</div>', unsafe_allow_html=True)

    status_filter = st.selectbox("Filter by status", ["All", *PROJECT_STATUS_OPTIONS], key="proj_status_filter")
    type_filter = st.selectbox("Filter by type", ["All", *PROJECT_TYPE_OPTIONS], key="proj_type_filter")

    filtered = projects_df.copy()
    if status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]
    if type_filter != "All":
        filtered = filtered[filtered["project_type"] == type_filter]

    if filtered.empty:
        render_note("No projects match the current filters.")
        return

    display_df = filtered.rename(columns={
        "id": "ID",
        "project_name": "Project",
        "client_name": "Client",
        "project_type": "Type",
        "status": "Status",
        "priority": "Priority",
        "start_date": "Start",
        "due_date": "Due",
        "completion_date": "Completed",
        "value": "Value ($)",
        "notes": "Notes",
    })

    display_cols = ["ID", "Project", "Client", "Type", "Status", "Priority", "Start", "Due", "Value ($)", "Notes"]
    edited = st.data_editor(
        display_df[display_cols],
        hide_index=True,
        width="stretch",
        height=min(45 * len(display_df) + 45, 560),
        disabled=["ID"],
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=PROJECT_STATUS_OPTIONS, required=True),
            "Priority": st.column_config.SelectboxColumn("Priority", options=PRIORITY_OPTIONS, required=True),
            "Type": st.column_config.SelectboxColumn("Type", options=PROJECT_TYPE_OPTIONS, required=True),
            "Value ($)": st.column_config.NumberColumn("Value ($)", format="$%.0f", min_value=0),
            "Start": st.column_config.TextColumn("Start"),
            "Due": st.column_config.TextColumn("Due"),
        },
        key="projects_editor",
    )

    save_cols = st.columns([1, 4])
    with save_cols[0]:
        if st.button("Save Project Updates", type="primary", width="stretch"):
            for _, row in edited.iterrows():
                pipeline.database.save_project({
                    "id": int(row["ID"]),
                    "project_name": str(row["Project"]).strip(),
                    "client_name": str(row["Client"]).strip(),
                    "project_type": str(row["Type"]),
                    "status": str(row["Status"]),
                    "priority": str(row["Priority"]),
                    "start_date": str(row.get("Start", "") or ""),
                    "due_date": str(row.get("Due", "") or ""),
                    "completion_date": "",
                    "value": float(row.get("Value ($)") or 0),
                    "notes": str(row.get("Notes", "") or ""),
                })
            st.success("Projects updated.")
            st.cache_resource.clear()
            st.rerun()


# ── LeadFinder ─────────────────────────────────────────────────────────────


def render_leadfinder_controls() -> tuple[SearchInput | None, bool]:
    current_state = st.session_state.get(STATE_KEY, STATE_PLACEHOLDER)
    if current_state in STATE_ABBR_TO_NAME:
        st.session_state[STATE_KEY] = state_name(current_state)

    with st.container(border=True):
        st.markdown("**Search Parameters**")
        random_cols = st.columns(2)
        preferred_state = st.session_state.get(STATE_KEY, STATE_PLACEHOLDER)
        preferred_state = "" if preferred_state == STATE_PLACEHOLDER else preferred_state
        with random_cols[0]:
            if st.button("Random Town", width="stretch"):
                city, state = pick_random_market(preferred_state)
                st.session_state[CITY_KEY] = city
                st.session_state[STATE_KEY] = state_name(state)
        with random_cols[1]:
            if st.button("Random Market", width="stretch"):
                city, state = pick_random_market(preferred_state)
                st.session_state[CITY_KEY] = city
                st.session_state[STATE_KEY] = state_name(state)
                st.session_state[CATEGORY_KEY] = random.choice(SUGGESTED_CATEGORIES)
                st.session_state[CUSTOM_CATEGORY_KEY] = ""

        category = st.selectbox("Business category", SUGGESTED_CATEGORIES, key=CATEGORY_KEY)
        custom_category = st.text_input(
            "Custom search phrase (optional)",
            placeholder="Example: air conditioning repair",
            key=CUSTOM_CATEGORY_KEY,
        )
        city = st.text_input("Target city", placeholder="Example: Bozeman", key=CITY_KEY)
        state = st.selectbox("State", [STATE_PLACEHOLDER] + STATE_OPTIONS, key=STATE_KEY)
        limit = st.slider("Leads to return", min_value=5, max_value=100, step=5, key=LIMIT_KEY)
        run_search = st.button("Run Search", type="primary", width="stretch")

    if state == STATE_PLACEHOLDER:
        state = ""

    search_input = None
    if city.strip() and state:
        search_input = SearchInput(
            category=(custom_category.strip() or category.strip()),
            city=city.strip(),
            state=state_abbr(state.strip()),
            limit=limit,
        )
    return search_input, run_search


def render_priority_leads(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-label">Priority Leads</div>', unsafe_allow_html=True)
    cards = df.head(3)
    if cards.empty:
        render_note("No priority leads to show.")
        return

    columns = st.columns(len(cards))
    for column, (_, row) in zip(columns, cards.iterrows()):
        website = str(row.get("Website", "")).strip()
        website_label = "Yes" if website else "No"
        rating = row.get("Rating")
        reviews = row.get("Reviews")
        rating_label = f"{float(rating):.1f}" if pd.notna(rating) else "-"
        review_label = f"{int(reviews)}" if pd.notna(reviews) else "-"
        signal = truncate_text(row.get("Primary Signal", ""), 140)
        tier = str(row.get("Opportunity", "Low"))
        tier_style = tier_class(tier)

        with column:
            st.markdown(
                f"""
                <div class="lead-card {tier_style}">
                    <div class="lead-card-header">
                        <div class="lead-title">{html.escape(str(row.get("Business Name", "")))}</div>
                        <div class="lead-score">{int(row.get("Opportunity Score", 0))}</div>
                    </div>
                    <div class="lead-meta">{html.escape(str(row.get("Location", "")))}</div>
                    <span class="lead-tier {tier_style}">{html.escape(tier)} opportunity</span>
                    <div class="lead-facts">
                        <div>
                            <div class="lead-fact-label">Website</div>
                            <div class="lead-fact-value">{html.escape(website_label)}</div>
                        </div>
                        <div>
                            <div class="lead-fact-label">Rating</div>
                            <div class="lead-fact-value">{html.escape(rating_label)}</div>
                        </div>
                        <div>
                            <div class="lead-fact-label">Reviews</div>
                            <div class="lead-fact-value">{html.escape(review_label)}</div>
                        </div>
                    </div>
                    <div class="lead-signal">{html.escape(signal)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_search_tab(pipeline: LeadPipeline) -> None:
    settings = get_settings()

    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">LeadFinder</div>'
        '<div class="page-subtitle">Discover small businesses that need a website or site upgrade</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 2.5])
    with left:
        search_input, run_search = render_leadfinder_controls()

    with right:
        st.markdown('<div class="section-label">Search Results</div>', unsafe_allow_html=True)

        if run_search:
            if search_input is None:
                st.error("Enter a city and select a state before running a search.")
            elif not settings.rapidapi_key:
                st.error("`RAPIDAPI_KEY` is missing. Add it to your environment or `.env` file.")
            else:
                progress_box = st.empty()
                progress_bar = st.progress(0)

                def report(progress: float, message: str) -> None:
                    progress_bar.progress(int(progress * 100))
                    progress_box.info(message)

                try:
                    with st.spinner("Finding leads and analyzing websites…"):
                        records = pipeline.run_search(search_input, progress_callback=report)
                    results_df = pipeline.records_to_dataframe(records)
                    st.session_state["last_results"] = results_df
                    st.session_state["last_run_summary"] = (
                        f"{len(results_df)} leads processed for {search_input.category} in "
                        f"{search_input.city}, {state_name(search_input.state)}."
                    )
                    progress_bar.empty()
                    progress_box.success(st.session_state["last_run_summary"])
                except Exception as exc:  # noqa: BLE001
                    progress_bar.empty()
                    progress_box.empty()
                    st.exception(exc)

        results_df = prepare_results_for_display(st.session_state["last_results"])
        summary = st.session_state["last_run_summary"]

        if summary:
            render_note(f"Latest run: {summary}")

        if results_df.empty:
            render_note("Run a search above to discover leads.")
            return

        st.markdown('<div class="section-label">Filters</div>', unsafe_allow_html=True)
        row_one = st.columns([2.2, 0.9, 0.9, 1.2])
        with row_one[0]:
            keyword = st.text_input("Search within results", placeholder="Business name, location, phone, signals…")
        with row_one[1]:
            website_filter = st.selectbox("Website", WEBSITE_FILTER_OPTIONS, index=0)
        with row_one[2]:
            opportunity_filter = st.selectbox("Opportunity", OPPORTUNITY_FILTER_OPTIONS, index=0)
        with row_one[3]:
            signal_filter = st.selectbox("Signal", SIGNAL_FILTER_OPTIONS, index=0)

        row_two = st.columns([1, 1, 1.4])
        with row_two[0]:
            max_reviews = st.number_input(
                "Max reviews",
                min_value=0,
                value=int(results_df["Reviews"].fillna(0).max()) if "Reviews" in results_df.columns else 0,
                step=5,
            )
        with row_two[1]:
            min_rating = st.slider("Min rating", min_value=0.0, max_value=5.0, value=0.0, step=0.1)
        with row_two[2]:
            sort_by = st.selectbox("Sort by", SORT_OPTIONS, index=0)

        filtered = filter_results(results_df, keyword, int(max_reviews), float(min_rating), website_filter, signal_filter, opportunity_filter, sort_by)

        st.write("")
        hot_count = int((filtered["Opportunity"] == "Hot").sum()) if "Opportunity" in filtered.columns else 0
        no_website_count = int((filtered["Website Status"] == "No website").sum()) if "Website Status" in filtered.columns else 0
        mc = st.columns(3)
        with mc[0]:
            st.metric("Visible Leads", len(filtered))
        with mc[1]:
            st.metric("Hot Leads", hot_count)
        with mc[2]:
            st.metric("No Website", no_website_count)

        if filtered.empty:
            render_note("No leads match the current filters.")
            return

        render_priority_leads(filtered)

        st.markdown('<div class="section-label">Full Results</div>', unsafe_allow_html=True)
        table_df = filtered[[
            "Opportunity", "Opportunity Score", "Business Name", "Location",
            "Phone", "Website Status", "Website", "Rating", "Reviews",
            "Primary Signal", "Personalized Openers",
        ]].copy()
        st.dataframe(
            style_results_table(table_df),
            height=600,
            hide_index=True,
            width="stretch",
            column_config={
                "Website": st.column_config.LinkColumn("Website", display_text="Open site"),
                "Opportunity Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
                "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
                "Reviews": st.column_config.NumberColumn("Reviews", format="%d"),
            },
        )


# ── Activity ───────────────────────────────────────────────────────────────


def render_activity_tab(pipeline: LeadPipeline) -> None:
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Activity</div>'
        '<div class="page-subtitle">Lead update history and saved searches</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    events = pipeline.database.fetch_lead_events(limit=200)
    searches = pipeline.database.fetch_saved_searches(limit=100)

    st.markdown('<div class="section-label">Saved Searches</div>', unsafe_allow_html=True)
    if searches.empty:
        render_note("No saved searches yet.")
    else:
        sd = searches.copy()
        sd["state"] = sd["state"].apply(state_name)
        st.dataframe(
            sd.rename(columns={
                "category": "Category", "city": "City", "state": "State",
                "limit_count": "Limit", "result_count": "Results", "created_at": "Run At",
            })[["Run At", "Category", "City", "State", "Limit", "Results"]],
            hide_index=True,
            width="stretch",
            height=300,
        )

    st.markdown('<div class="section-label">Lead Updates</div>', unsafe_allow_html=True)
    if events.empty:
        render_note("No lead updates recorded yet.")
    else:
        ed = events.copy()
        ed["Change"] = ed.apply(
            lambda row: f"{row['field_name']}: {format_event_value(row['old_value'])} → {format_event_value(row['new_value'])}",
            axis=1,
        )
        st.dataframe(
            ed.rename(columns={"created_at": "Time", "business_name": "Business", "event_type": "Type"})[
                ["Time", "Business", "Type", "Change"]
            ],
            hide_index=True,
            width="stretch",
            height=420,
        )


# ── Main ───────────────────────────────────────────────────────────────────


def main() -> None:
    st.set_page_config(
        page_title="Vanguard Creatives",
        page_icon="V",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    init_state()

    # Warm the pipeline cache before the password gate so login is instant
    pipeline = get_pipeline()

    if not require_password():
        return

    ensure_dashboard_database(pipeline)
    history_df = pipeline.database.fetch_all_leads()

    page = render_suite_sidebar()

    if page == "Dashboard":
        render_command_center(pipeline, history_df)
    elif page == "Pipeline":
        render_pipeline_tab(history_df)
    elif page == "Leads":
        render_leads_tab(pipeline)
    elif page == "Follow Ups":
        render_followups_tab(pipeline)
    elif page == "Clients":
        render_clients_tab(pipeline)
    elif page == "Projects":
        render_projects_tab(pipeline)
    elif page == "LeadFinder":
        render_search_tab(pipeline)
    elif page == "Activity":
        render_activity_tab(pipeline)


if __name__ == "__main__":
    main()
