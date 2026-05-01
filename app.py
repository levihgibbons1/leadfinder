from __future__ import annotations

import html
import random

import pandas as pd
import streamlit as st

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
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}
STATE_ABBR_TO_NAME = {abbr: name for name, abbr in STATE_NAME_TO_ABBR.items()}
STATE_OPTIONS = list(STATE_NAME_TO_ABBR.keys())
STATE_PLACEHOLDER = "Select a state"

STATUS_OPTIONS = ["All", "New", "Contacted", "Client", "Dead"]
WEBSITE_FILTER_OPTIONS = ["Any", "Has website", "No website"]
OPPORTUNITY_FILTER_OPTIONS = ["Any", "Hot", "Warm", "Low"]
SIGNAL_FILTER_OPTIONS = [
    "Any",
    "No website",
    "Outdated website",
    "Mobile issues",
    "Family-owned angle",
    "Low reviews",
]
SORT_OPTIONS = [
    "Best opportunity first",
    "Lowest reviews first",
    "Highest rating first",
    "Business name A-Z",
]

SMALL_TOWN_MARKETS = [
    ("Bozeman", "MT"),
    ("Cody", "WY"),
    ("Laramie", "WY"),
    ("Sheridan", "WY"),
    ("Sandpoint", "ID"),
    ("Twin Falls", "ID"),
    ("Lewiston", "ID"),
    ("Bend", "OR"),
    ("Roseburg", "OR"),
    ("Grants Pass", "OR"),
    ("Wenatchee", "WA"),
    ("Ellensburg", "WA"),
    ("Yakima", "WA"),
    ("St. George", "UT"),
    ("Cedar City", "UT"),
    ("Durango", "CO"),
    ("Montrose", "CO"),
    ("Grand Junction", "CO"),
    ("Farmington", "NM"),
    ("Carlsbad", "NM"),
    ("Pueblo", "CO"),
    ("Hutchinson", "KS"),
    ("Salina", "KS"),
    ("Manhattan", "KS"),
    ("Joplin", "MO"),
    ("Branson", "MO"),
    ("Cape Girardeau", "MO"),
    ("Bentonville", "AR"),
    ("Russellville", "AR"),
    ("Pine Bluff", "AR"),
    ("Muskogee", "OK"),
    ("Stillwater", "OK"),
    ("Enid", "OK"),
    ("Waco", "TX"),
    ("Abilene", "TX"),
    ("Nacogdoches", "TX"),
    ("Lake Charles", "LA"),
    ("Monroe", "LA"),
    ("Hattiesburg", "MS"),
    ("Meridian", "MS"),
    ("Dothan", "AL"),
    ("Gadsden", "AL"),
    ("Rome", "GA"),
    ("Valdosta", "GA"),
    ("Tifton", "GA"),
    ("Ocala", "FL"),
    ("Sebring", "FL"),
    ("Punta Gorda", "FL"),
    ("Kingsport", "TN"),
    ("Cookeville", "TN"),
    ("Bowling Green", "KY"),
    ("Paducah", "KY"),
    ("Muncie", "IN"),
    ("Kokomo", "IN"),
    ("Lima", "OH"),
    ("Mansfield", "OH"),
    ("Erie", "PA"),
    ("Altoona", "PA"),
    ("Johnstown", "PA"),
    ("Morgantown", "WV"),
    ("Beckley", "WV"),
    ("Traverse City", "MI"),
    ("Midland", "MI"),
    ("Eau Claire", "WI"),
    ("La Crosse", "WI"),
    ("Mankato", "MN"),
    ("Bemidji", "MN"),
    ("Sioux City", "IA"),
    ("Dubuque", "IA"),
    ("Bismarck", "ND"),
    ("Minot", "ND"),
    ("Rapid City", "SD"),
    ("Brookings", "SD"),
    ("Augusta", "ME"),
    ("Bangor", "ME"),
    ("Burlington", "VT"),
    ("Rutland", "VT"),
    ("Concord", "NH"),
    ("Keene", "NH"),
]

CATEGORY_KEY = "search_category"
CUSTOM_CATEGORY_KEY = "search_custom_category"
CITY_KEY = "search_city"
STATE_KEY = "search_state"
LIMIT_KEY = "search_limit"


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1440px;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid #e5e7eb;
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 1.25rem;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 0.5rem;
            min-height: 2.75rem;
            font-weight: 600;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 0.75rem;
            padding: 0.75rem 1rem;
        }

        div[data-testid="stMetricValue"] {
            color: #111111;
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 0.75rem;
        }

        .helper-text {
            color: #4b5563;
            font-size: 0.95rem;
        }

        .lead-card {
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-left-width: 6px;
            border-radius: 8px;
            padding: 1rem;
            min-height: 220px;
        }

        .lead-card.hot {
            border-left-color: #16a34a;
        }

        .lead-card.warm {
            border-left-color: #ca8a04;
        }

        .lead-card.low {
            border-left-color: #6b7280;
        }

        .lead-title {
            color: #111111;
            font-size: 1.02rem;
            font-weight: 700;
            line-height: 1.25;
            margin: 0;
        }

        .lead-meta {
            color: #4b5563;
            font-size: 0.85rem;
            line-height: 1.35;
            margin: 0.45rem 0 0.85rem;
        }

        .lead-card-header {
            align-items: flex-start;
            display: flex;
            gap: 0.75rem;
            justify-content: space-between;
        }

        .lead-score {
            background: #111111;
            border-radius: 6px;
            color: #ffffff;
            flex: 0 0 auto;
            font-size: 0.85rem;
            font-weight: 700;
            padding: 0.25rem 0.45rem;
        }

        .lead-tier {
            display: inline-block;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 700;
            margin-bottom: 0.65rem;
            padding: 0.18rem 0.55rem;
        }

        .lead-tier.hot {
            background: #dcfce7;
            color: #14532d;
        }

        .lead-tier.warm {
            background: #fef3c7;
            color: #713f12;
        }

        .lead-tier.low {
            background: #f3f4f6;
            color: #111827;
        }

        .lead-facts {
            border-bottom: 1px solid #e5e7eb;
            border-top: 1px solid #e5e7eb;
            display: grid;
            gap: 0.65rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin-bottom: 0.85rem;
            padding: 0.75rem 0;
        }

        .lead-fact-label {
            color: #6b7280;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
        }

        .lead-fact-value {
            color: #111111;
            font-size: 0.88rem;
            font-weight: 600;
            margin-top: 0.1rem;
        }

        .lead-signal {
            color: #111111;
            font-size: 0.9rem;
            line-height: 1.35;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def init_state() -> None:
    st.session_state.setdefault("last_results", pd.DataFrame())
    st.session_state.setdefault("last_run_summary", "")
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault(CATEGORY_KEY, SUGGESTED_CATEGORIES[0])
    st.session_state.setdefault(CUSTOM_CATEGORY_KEY, "")
    st.session_state.setdefault(CITY_KEY, "")
    st.session_state.setdefault(STATE_KEY, STATE_PLACEHOLDER)
    st.session_state.setdefault(LIMIT_KEY, 30)


def state_name(value: str) -> str:
    if value in STATE_ABBR_TO_NAME:
        return STATE_ABBR_TO_NAME[value]
    return value


def state_abbr(value: str) -> str:
    if value in STATE_NAME_TO_ABBR:
        return STATE_NAME_TO_ABBR[value]
    return value


def render_note(message: str) -> None:
    with st.container(border=True):
        st.write(message)


def require_password() -> bool:
    settings = get_settings()
    if not settings.app_password:
        return True
    if st.session_state.get("authenticated", False):
        return True

    st.title("LeadFinder")
    st.caption("Enter the team password to continue.")
    password = st.text_input("Password", type="password")
    if st.button("Unlock", type="primary"):
        if password == settings.app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


def pick_random_market(preferred_state: str = "") -> tuple[str, str]:
    markets = SMALL_TOWN_MARKETS
    if preferred_state:
        preferred_state = state_abbr(preferred_state)
        state_matches = [market for market in SMALL_TOWN_MARKETS if market[1] == preferred_state]
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
        return any(
            phrase in normalized
            for phrase in ("stale", "dated", "table-heavy", "thin", "modern image formats")
        )
    if selected_signal == "Mobile issues":
        return any(phrase in normalized for phrase in ("mobile", "viewport"))
    if selected_signal == "Family-owned angle":
        return any(phrase in normalized for phrase in ("family-owned", "family owned", "locally rooted"))
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
    return f"{text[: limit - 3].rstrip()}..."


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
    if any(term in signal_text for term in ("stale", "dated", "table-heavy", "thin", "modern image formats")):
        score += 20
    if any(term in signal_text for term in ("mobile", "viewport")):
        score += 15
    if any(term in signal_text for term in ("family-owned", "family owned", "locally rooted")):
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
        lambda value: "Has website" if value else "No website"
    )
    prepared["Primary Signal"] = prepared["Key Signals"].apply(first_line)
    return sort_results(prepared, "Best opportunity first").reset_index(drop=True)


def tier_class(tier: str) -> str:
    return str(tier).strip().lower() if str(tier).strip().lower() in {"hot", "warm", "low"} else "low"


def render_priority_leads(df: pd.DataFrame) -> None:
    st.markdown("#### Priority Leads")
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
        signal = truncate_text(row.get("Primary Signal", ""), 150)
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


def style_results_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    def opportunity_style(value: object) -> str:
        if value == "Hot":
            return "background-color: #dcfce7; color: #14532d; font-weight: 700;"
        if value == "Warm":
            return "background-color: #fef3c7; color: #713f12; font-weight: 700;"
        return "background-color: #f3f4f6; color: #111827; font-weight: 700;"

    def website_style(value: object) -> str:
        if value == "No website":
            return "background-color: #fee2e2; color: #7f1d1d; font-weight: 700;"
        return "background-color: #f3f4f6; color: #111827;"

    return df.style.map(opportunity_style, subset=["Opportunity"]).map(website_style, subset=["Website Status"])


def sort_results(df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
    if sort_by == "Best opportunity first" and "Opportunity Score" in df.columns:
        return df.sort_values(
            by=["Opportunity Score", "Reviews", "Business Name"],
            ascending=[False, True, True],
            na_position="last",
        )
    if sort_by == "Highest rating first":
        return df.sort_values(by=["Rating", "Reviews", "Business Name"], ascending=[False, False, True], na_position="last")
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
                    row.get("Key Signals", ""),
                    row.get("Reviews"),
                    row.get("Website", ""),
                    signal_filter,
                ),
                axis=1,
            )
        ]
    if opportunity_filter != "Any" and "Opportunity" in filtered.columns:
        filtered = filtered[filtered["Opportunity"] == opportunity_filter]
    filtered = sort_results(filtered, sort_by)
    return filtered.reset_index(drop=True)


def filter_history(df: pd.DataFrame, keyword: str, status: str) -> pd.DataFrame:
    filtered = df.copy()
    if status != "All":
        filtered = filtered[filtered["status"] == status]
    if keyword.strip():
        haystack = filtered.astype(str).agg(" ".join, axis=1).str.lower()
        filtered = filtered[haystack.str.contains(keyword.strip().lower(), na=False)]
    return filtered.reset_index(drop=True)


def render_header(history_df: pd.DataFrame) -> None:
    total = len(history_df)
    new_count = int((history_df["status"] == "New").sum()) if not history_df.empty else 0
    client_count = int((history_df["status"] == "Client").sum()) if not history_df.empty else 0
    states = int(history_df["state"].nunique()) if not history_df.empty else 0

    st.title("LeadFinder")
    st.markdown(
        '<div class="helper-text">Search smaller-town blue-collar businesses, flag weak websites, and keep all leads in one place.</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("Total Leads", f"{total:,}")
    with metric_cols[1]:
        st.metric("New Leads", f"{new_count:,}")
    with metric_cols[2]:
        st.metric("Clients", f"{client_count:,}")
    with metric_cols[3]:
        st.metric("States Covered", f"{states:,}")


def render_sidebar() -> tuple[SearchInput | None, bool]:
    settings = get_settings()
    current_state = st.session_state.get(STATE_KEY, STATE_PLACEHOLDER)
    if current_state in STATE_ABBR_TO_NAME:
        st.session_state[STATE_KEY] = state_name(current_state)

    with st.sidebar:
        st.header("Search")
        st.caption("Fill in the market you want to target, then run a search.")

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
        st.caption("Use the random buttons when you want a smaller-town idea instead of picking a city yourself.")

        category = st.selectbox(
            "Business category",
            SUGGESTED_CATEGORIES,
            key=CATEGORY_KEY,
            help="Choose the main type of business you want to find.",
        )
        custom_category = st.text_input(
            "Custom search phrase (optional)",
            placeholder="Example: air conditioning repair",
            help="Leave blank to use the category above. Use this only when you want a more specific search term.",
            key=CUSTOM_CATEGORY_KEY,
        )
        city = st.text_input(
            "Target city",
            placeholder="Example: Bozeman",
            help="Enter the town or city you want to search in.",
            key=CITY_KEY,
        )
        state = st.selectbox(
            "State",
            [STATE_PLACEHOLDER] + STATE_OPTIONS,
            key=STATE_KEY,
            help="Pick the state for the target city.",
        )
        limit = st.slider(
            "Number of leads to return",
            min_value=5,
            max_value=100,
            step=5,
            help="Start with 20 to 30 for faster results and lower API usage.",
            key=LIMIT_KEY,
        )
        run_search = st.button("Run Search", type="primary", width="stretch")

        st.divider()
        st.subheader("Storage")
        st.caption("Leads are saved automatically so the team can come back later.")
        st.caption(f"Database: `{settings.sqlite_path.name}`")

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


def render_search_tab(pipeline: LeadPipeline) -> None:
    search_input, run_search = render_sidebar()
    settings = get_settings()

    st.subheader("Search Results")
    st.caption("Every new search is saved automatically and de-duplicated.")

    if run_search:
        if search_input is None:
            st.error("Enter a city and pick a state before running a search.")
        elif not settings.rapidapi_key:
            st.error("`RAPIDAPI_KEY` is missing. Add it to your environment or `.env` file to run searches.")
        else:
            progress_box = st.empty()
            progress_bar = st.progress(0)

            def report(progress: float, message: str) -> None:
                progress_bar.progress(int(progress * 100))
                progress_box.info(message)

            try:
                with st.spinner("Finding leads and analyzing websites..."):
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
        render_note("Run a search from the left sidebar to load leads, website signals, and outreach openers.")
        return

    st.write("")
    st.markdown("#### Filters")
    row_one = st.columns([2.2, 0.9, 0.9, 1.2])
    with row_one[0]:
        keyword = st.text_input(
            "Search within results",
            placeholder="Search by business name, location, phone, signals, or opener text",
        )
    with row_one[1]:
        website_filter = st.selectbox("Website", WEBSITE_FILTER_OPTIONS, index=0)
    with row_one[2]:
        opportunity_filter = st.selectbox("Opportunity", OPPORTUNITY_FILTER_OPTIONS, index=0)
    with row_one[3]:
        signal_filter = st.selectbox("Opportunity signal", SIGNAL_FILTER_OPTIONS, index=0)

    row_two = st.columns([1, 1, 1.4])
    with row_two[0]:
        max_reviews = st.number_input(
            "Max reviews",
            min_value=0,
            value=int(results_df["Reviews"].fillna(0).max()) if "Reviews" in results_df.columns else 0,
            step=5,
        )
    with row_two[1]:
        min_rating = st.slider("Minimum rating", min_value=0.0, max_value=5.0, value=0.0, step=0.1)
    with row_two[2]:
        sort_by = st.selectbox("Sort results by", SORT_OPTIONS, index=0)

    filtered = filter_results(
        results_df,
        keyword,
        int(max_reviews),
        float(min_rating),
        website_filter,
        signal_filter,
        opportunity_filter,
        sort_by,
    )

    st.write("")
    hot_count = int((filtered["Opportunity"] == "Hot").sum()) if "Opportunity" in filtered.columns else 0
    no_website_count = int((filtered["Website Status"] == "No website").sum()) if "Website Status" in filtered.columns else 0
    action_cols = st.columns(3)
    with action_cols[0]:
        st.metric("Visible Leads", len(filtered))
    with action_cols[1]:
        st.metric("Hot Leads", hot_count)
    with action_cols[2]:
        st.metric("No Website", no_website_count)

    if filtered.empty:
        render_note("No leads match the current filters.")
        return

    st.write("")
    render_priority_leads(filtered)

    st.write("")
    st.markdown("#### Full Results")
    table_df = filtered[
        [
            "Opportunity",
            "Opportunity Score",
            "Business Name",
            "Location",
            "Phone",
            "Website Status",
            "Website",
            "Rating",
            "Reviews",
            "Primary Signal",
            "Personalized Openers",
        ]
    ].copy()
    st.dataframe(
        style_results_table(table_df),
        height=620,
        hide_index=True,
        width="stretch",
        column_config={
            "Website": st.column_config.LinkColumn("Website", display_text="Open site"),
            "Opportunity Score": st.column_config.ProgressColumn(
                "Score",
                min_value=0,
                max_value=100,
                format="%d",
            ),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
            "Reviews": st.column_config.NumberColumn("Reviews", format="%d"),
        },
    )


def render_history_tab(pipeline: LeadPipeline) -> None:
    st.subheader("All Leads")
    st.caption("This is the full saved history. Update status and notes here as your team works each lead.")
    history_df = pipeline.database.fetch_all_leads()

    if history_df.empty:
        render_note("No saved leads yet. Once you run a search, the full history will appear here.")
        return

    filters = st.columns([2, 1])
    with filters[0]:
        keyword = st.text_input(
            "Search saved leads",
            key="history_filter",
            placeholder="Search business name, notes, location, category, or signals",
        )
    with filters[1]:
        status = st.selectbox("Status", STATUS_OPTIONS, index=0, key="history_status")

    filtered = filter_history(history_df, keyword, status)
    editable = filtered[
        [
            "id",
            "business_name",
            "category",
            "city",
            "state",
            "phone",
            "website",
            "rating",
            "reviews",
            "status",
            "notes",
            "created_at",
        ]
    ].rename(
        columns={
            "id": "Lead ID",
            "business_name": "Business Name",
            "category": "Category",
            "city": "City",
            "state": "State",
            "phone": "Phone",
            "website": "Website",
            "rating": "Rating",
            "reviews": "Reviews",
            "status": "Status",
            "notes": "Notes",
            "created_at": "Created At",
        }
    )

    edited = st.data_editor(
        editable,
        height=620,
        hide_index=True,
        width="stretch",
        disabled=[
            "Lead ID",
            "Business Name",
            "Category",
            "City",
            "State",
            "Phone",
            "Website",
            "Rating",
            "Reviews",
            "Created At",
        ],
        column_config={
            "Website": st.column_config.LinkColumn("Website", display_text="Open site"),
            "Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS[1:]),
        },
        key="history_editor",
    )

    footer = st.columns([1, 1.2, 4])
    with footer[0]:
        st.metric("Visible Rows", len(filtered))
    with footer[1]:
        if st.button("Save Status + Notes", width="stretch"):
            update_df = edited.rename(
                columns={"Lead ID": "id", "Status": "status", "Notes": "notes"}
            )[["id", "status", "notes"]]
            pipeline.database.update_status_notes(update_df)
            st.success("Lead status and notes saved.")
            st.cache_resource.clear()
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="LeadFinder", page_icon="L", layout="wide", initial_sidebar_state="expanded")
    inject_styles()
    init_state()
    if not require_password():
        return

    pipeline = get_pipeline()
    history_df = pipeline.database.fetch_all_leads()

    render_header(history_df)

    search_tab, history_tab = st.tabs(["Search", "All Leads"])
    with search_tab:
        render_search_tab(pipeline)
    with history_tab:
        render_history_tab(pipeline)


if __name__ == "__main__":
    main()
