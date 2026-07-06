"""fetch_worldbank.py - Pulls PPP conversion rates from World Bank API."""
import logging
import requests
import pandas as pd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://api.worldbank.org/v2/country/all/indicator/PA.NUS.PPP?format=json&per_page=20000&date=2023"


def fetch_ppp() -> pd.DataFrame:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Fetching World Bank PPP data")
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    if len(payload) < 2 or not payload[1]:
        raise RuntimeError("World Bank API returned no data")

    records = payload[1]
    rows = []
    for r in records:
        if r.get("value") is not None:
            rows.append({
                "country": r["country"]["value"],
                "country_code": r["countryiso3code"],
                "year": r["date"],
                "ppp_conversion_rate": r["value"],
            })

    df = pd.DataFrame(rows)
    df = df.sort_values("year", ascending=False).drop_duplicates("country_code")
    out_path = RAW_DIR / "worldbank_ppp.csv"
    df.to_csv(out_path, index=False)
    log.info("Saved %d countries -> %s", len(df), out_path)
    return df


if __name__ == "__main__":
    fetch_ppp()
