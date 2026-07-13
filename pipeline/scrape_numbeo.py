"""
scrape_numbeo.py

Scrapes Numbeo's public rankings pages (cost of living, quality of life,
crime/safety, healthcare, pollution, traffic) and saves one CSV per
index, plus a combined raw CSV, into data/raw/.

Numbeo's rankings pages return a single HTML table containing ALL cities
for that index in one request — so this is 6 requests total, not
one-request-per-city. Be polite: we sleep between requests and set a
real User-Agent.

Usage:
    python pipeline/scrape_numbeo.py

Output:
    data/raw/numbeo_cost_of_living.csv
    data/raw/numbeo_quality_of_life.csv
    data/raw/numbeo_safety.csv
    data/raw/numbeo_healthcare.csv
    data/raw/numbeo_pollution.csv
    data/raw/numbeo_traffic.csv
    data/raw/numbeo_combined.csv   (all six, long format)
"""

import io
import logging
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.numbeo.com/cost-of-living/",
    "Connection": "keep-alive",
}

# Each entry: (index_name, url)
RANKING_PAGES = {
    "cost_of_living": "https://www.numbeo.com/cost-of-living/rankings_current.jsp",
    "quality_of_life": "https://www.numbeo.com/quality-of-life/rankings_current.jsp",
    "safety": "https://www.numbeo.com/crime/rankings_current.jsp",
    "healthcare": "https://www.numbeo.com/health-care/rankings_current.jsp",
    "pollution": "https://www.numbeo.com/pollution/rankings_current.jsp",
    "traffic": "https://www.numbeo.com/traffic/rankings_current.jsp",
}

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
REQUEST_DELAY_SECONDS = 3  # politeness delay between requests
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5


def fetch_page(url: str) -> str:
    """Fetch a URL with retries and return raw HTML text."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            log.warning(
                "Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts") from last_exc


def extract_table(html: str) -> pd.DataFrame:
    """
    Extract the rankings table from a Numbeo page.

    Numbeo's markup changes over time. The most reliable anchor is the
    <td class="cityOrCountryInIndicesTable"> cell that appears in every
    row of the rankings table (each contains a link to that city's page).
    We find the table that CONTAINS such a cell, rather than relying on
    a specific table id/class, which has proven less stable.
    """
    soup = BeautifulSoup(html, "html.parser")

    marker_cell = soup.find("td", {"class": "cityOrCountryInIndicesTable"})
    table = marker_cell.find_parent("table") if marker_cell else None

    if table is None:
        # Older/alternate markup fallback
        table = soup.find("table", {"id": "cityRankingTable"}) or soup.find(
            "table", {"id": "t2"}
        )

    if table is not None:
        dfs = pd.read_html(io.StringIO(str(table)))
        if dfs:
            return dfs[0]

    # Last resort: pick the largest table on the page by row count
    all_tables = pd.read_html(io.StringIO(html))
    if not all_tables:
        raise ValueError("No tables found on page")
    largest = max(all_tables, key=lambda df: df.shape[0])
    log.warning(
        "Known table markers not found — used fallback (largest table, %d rows). "
        "Numbeo may have changed their markup; verify columns look sane.",
        largest.shape[0],
    )
    return largest


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names: lowercase, underscores, strip whitespace."""
    df = df.copy()
    df.columns = [
        str(c).strip().lower().replace(" ", "_").replace(".", "") for c in df.columns
    ]
    # Numbeo tables usually include an unwanted leading index/rank column
    # named 'rank' or 'unnamed:_0' — keep rank if present, drop pure index junk
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]
    return df


def split_city_country(df: pd.DataFrame) -> pd.DataFrame:
    """
    Numbeo's 'city' column is usually formatted as 'City, Country'.
    Split it into separate city and country columns for easier joining
    later in build_master.py.
    """
    df = df.copy()
    city_col = None
    for candidate in ("city", "city,_country", "town"):
        if candidate in df.columns:
            city_col = candidate
            break

    if city_col is None:
        log.warning("Could not find a city column to split; columns were: %s", list(df.columns))
        return df

    split = df[city_col].astype(str).str.rsplit(",", n=1, expand=True)
    df["city"] = split[0].str.strip()
    if split.shape[1] > 1:
        df["country"] = split[1].str.strip()
    return df


def scrape_all() -> pd.DataFrame:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    combined_frames = []

    for index_name, url in RANKING_PAGES.items():
        log.info("Scraping %s from %s", index_name, url)
        html = fetch_page(url)
        df = extract_table(html)
        df = clean_columns(df)
        df = split_city_country(df)
        df["index_type"] = index_name

        out_path = RAW_DIR / f"numbeo_{index_name}.csv"
        df.to_csv(out_path, index=False)
        log.info("Saved %s (%d rows) -> %s", index_name, len(df), out_path)

        combined_frames.append(df)
        time.sleep(REQUEST_DELAY_SECONDS)

    combined = pd.concat(combined_frames, ignore_index=True, sort=False)
    combined_path = RAW_DIR / "numbeo_combined.csv"
    combined.to_csv(combined_path, index=False)
    log.info("Saved combined file (%d rows) -> %s", len(combined), combined_path)
    return combined


if __name__ == "__main__":
    scrape_all()
