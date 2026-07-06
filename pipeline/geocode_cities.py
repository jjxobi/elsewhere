"""
geocode_cities.py

Adds latitude/longitude to each city by calling Nominatim
(OpenStreetMap) directly via requests - no geopy dependency for the
actual HTTP call, to keep behavior simple and predictable.
"""

import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CACHE_PATH = RAW_DIR / "geocode_cache.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "elsewhere_lifestyle_dashboard (contact: none)"}
MIN_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3


def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def geocode_query(query):
    params = {"q": query, "format": "json", "limit": 1}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                wait = 15 * attempt
                log.warning("Rate limited (429) for '%s' - waiting %ds", query, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
            return None, None
        except Exception as exc:
            log.warning("Attempt %d/%d failed for '%s': %s", attempt, MAX_RETRIES, query, exc)
            time.sleep(3 * attempt)
    log.warning("Giving up on '%s' after %d attempts", query, MAX_RETRIES)
    return None, None


def geocode_cities(df, city_col="city", country_col="country"):
    cache = load_cache()
    df = df.copy()
    unique_pairs = df[[city_col, country_col]].drop_duplicates()
    total = len(unique_pairs)
    log.info("Geocoding %d unique city/country pairs (already cached: %d)", total, len(cache))

    done = 0
    for _, row in unique_pairs.iterrows():
        city = str(row[city_col])
        country = str(row[country_col]) if pd.notna(row[country_col]) else ""
        key = f"{city}|{country}"

        if key not in cache:
            query = f"{city}, {country}" if country else city
            lat, lon = geocode_query(query)
            cache[key] = {"lat": lat, "lon": lon}
            if lat is not None:
                log.info("Geocoded: %s -> (%.4f, %.4f)", query, lat, lon)
            else:
                log.warning("No result for: %s", query)
            save_cache(cache)
            time.sleep(MIN_DELAY_SECONDS)

        done += 1
        if done % 50 == 0:
            log.info("Progress: %d/%d", done, total)

    df["latitude"] = df.apply(lambda r: cache.get(f"{r[city_col]}|{r[country_col]}", {}).get("lat"), axis=1)
    df["longitude"] = df.apply(lambda r: cache.get(f"{r[city_col]}|{r[country_col]}", {}).get("lon"), axis=1)

    missing = df["latitude"].isna().sum()
    if missing:
        log.warning("%d rows still missing coordinates after geocoding", missing)

    return df


if __name__ == "__main__":
    combined_path = RAW_DIR / "numbeo_combined.csv"
    if not combined_path.exists():
        raise FileNotFoundError(f"{combined_path} not found — run scrape_numbeo.py first.")
    df = pd.read_csv(combined_path)
    cities_only = df[["city", "country"]].drop_duplicates().reset_index(drop=True)
    geocoded = geocode_cities(cities_only)
    out_path = RAW_DIR / "cities_geocoded.csv"
    geocoded.to_csv(out_path, index=False)
    log.info("Saved %d geocoded cities -> %s", len(geocoded), out_path)


