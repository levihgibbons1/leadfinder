from __future__ import annotations

import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from leadfinder.config import Settings
from leadfinder.models import WebsiteAnalysis
from leadfinder.utils import ensure_url


YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


class WebsiteAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent})

    def analyze(self, website: str) -> WebsiteAnalysis:
        normalized_url = ensure_url(website)
        if not normalized_url:
            return WebsiteAnalysis(
                signals=["No website is linked in the listing."],
                summary="The business listing does not include a website.",
                metrics={},
            )

        try:
            response = self.session.get(
                normalized_url,
                timeout=self.settings.request_timeout_seconds,
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.RequestException:
            return WebsiteAnalysis(
                final_url=normalized_url,
                signals=["The website could not be reached quickly, which is itself a sales signal."],
                summary="The site did not respond cleanly during a lightweight audit.",
                metrics={},
            )

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()

        text = soup.get_text(" ", strip=True)
        text_lower = text.lower()
        html_lower = response.text.lower()
        title = soup.title.get_text(strip=True) if soup.title else ""
        images = [img.get("src", "") for img in soup.find_all("img")]
        image_count = len(images)
        modern_image_count = sum(
            1
            for source in images
            if any(source.lower().endswith(ext) for ext in (".webp", ".svg", ".avif"))
        )
        viewport_present = bool(soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)}))
        table_count = len(soup.find_all("table"))
        text_length = len(text)
        latest_year = self._latest_year(text)
        family_owned = any(
            phrase in text_lower
            for phrase in (
                "family owned",
                "family-owned",
                "our family",
                "locally owned",
                "since 19",
                "since 20",
            )
        )
        stock_markers = any(
            marker in html_lower
            for marker in ("shutterstock", "istockphoto", "adobestock", "gettyimages", "stock photo")
        )

        signals: list[str] = []
        current_year = datetime.utcnow().year

        if latest_year and latest_year <= current_year - 2:
            signals.append(f"Footer or body copy appears stale; the latest year found on-site was {latest_year}.")
        if not viewport_present:
            signals.append("No viewport tag was detected, which often points to weak mobile optimization.")
        if stock_markers:
            signals.append("The source suggests stock photography is being used instead of custom local visuals.")
        if image_count > 0 and modern_image_count == 0:
            signals.append("The visual stack looks dated; no modern image formats were detected.")
        if table_count >= 3:
            signals.append("Layout appears table-heavy, a common sign of an older website build.")
        if text_length < 700:
            signals.append("Website copy is fairly thin, which usually means fewer trust-building details.")
        if family_owned:
            signals.append("Family-owned or locally rooted positioning is explicit on-site, which is a strong personalization angle.")

        if not signals:
            signals.append("The site is reachable, but there is still room to sharpen the presentation and conversion flow.")

        summary = " ".join(signals[:3])
        return WebsiteAnalysis(
            final_url=str(response.url),
            page_title=title,
            reachable=True,
            signals=signals[:6],
            summary=summary,
            metrics={
                "image_count": image_count,
                "modern_image_count": modern_image_count,
                "viewport_present": viewport_present,
                "table_count": table_count,
                "text_length": text_length,
                "latest_year": latest_year,
                "family_owned_terms": family_owned,
            },
        )

    @staticmethod
    def _latest_year(text: str) -> int | None:
        matches = [int(match.group()) for match in YEAR_PATTERN.finditer(text)]
        if not matches:
            return None
        return max(matches)
