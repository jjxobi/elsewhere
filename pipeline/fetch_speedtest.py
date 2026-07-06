"""
fetch_speedtest.py

Ookla no longer publishes a simple country-level CSV of the Speedtest
Global Index (only raw geospatial tile data now). Instead we use
Wikipedia's "List of countries by Internet connection speeds" page,
which is sourced directly from Speedtest.net data and kept up to date.
"""

import io
import logging
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
URL = "https://en.wikipedia.org/wiki/List_of_countries_by_Internet_connection_speeds"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def fetch_speed_tables():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Fetching %s", URL)
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    wiki_tables = soup.find_all("table", {"class": "wikitable"})

    if len(wiki_tables) < 2:
        raise RuntimeError(
            f"Expected at least 2 wikitables (fixed + mobile), found {len(wiki_tables)}. "
            "Wikipedia page structure may have changed."
        )

    fixed_df = pd.read_html(io.StringIO(str(wiki_tables[0])))[0]
    mobile_df = pd.read_html(io.StringIO(str(wiki_tables[1])))[0]

    for df, label in ((fixed_df, "fixed"), (mobile_df, "mobile")):
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        log.info("%s table: %d rows, columns: %s", label, len(df), list(df.columns))

    fixed_path = RAW_DIR / "internet_speed_fixed.csv"
    mobile_path = RAW_DIR / "internet_speed_mobile.csv"
    fixed_df.to_csv(fixed_path, index=False)
    mobile_df.to_csv(mobile_path, index=False)
    log.info("Saved -> %s", fixed_path)
    log.info("Saved -> %s", mobile_path)

    return fixed_df, mobile_df


if __name__ == "__main__":
    fetch_speed_tables()
