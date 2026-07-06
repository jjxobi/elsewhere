"""
build_master.py

Joins all scraped/fetched sources into the final master_data.csv that
the Tableau dashboard reads:

  - data/raw/numbeo_combined.csv     (6 index types, long format)
  - data/raw/worldbank_ppp.csv       (country-level PPP rates)
  - data/raw/internet_speed_fixed.csv (country-level, from Wikipedia/Speedtest)
  - data/raw/internet_speed_mobile.csv
  - data/raw/cities_geocoded.csv     (city/country -> lat/lon)
  - data/visa_list_nz.csv            (static, manually curated)

Output:
  data/master_data.csv
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
DATA_DIR = BASE_DIR / "data"

# Numbeo index types we don't already have a well-named column for -
# each of these tables should have ONE primary index column. We find
# it by keyword match since Numbeo's exact naming varies by page.
INDEX_TYPE_KEYWORDS = {
    "quality_of_life": ["quality_of_life"],
    "safety": ["crime", "safety"],
    "healthcare": ["health"],
    "pollution": ["pollution"],
    "traffic": ["traffic"],
}


def find_index_column(columns, keywords):
    for col in columns:
        for kw in keywords:
            if kw in col and "index" in col:
                return col
    # fallback: any column containing the keyword
    for col in columns:
        for kw in keywords:
            if kw in col:
                return col
    return None


def load_numbeo_wide() -> pd.DataFrame:
    path = RAW_DIR / "numbeo_combined.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run scrape_numbeo.py first.")
    df = pd.read_csv(path)

    frames = []

    col_subset = df[df["index_type"] == "cost_of_living"].copy()
    col_subset = col_subset.dropna(axis=1, how="all")
    exclude = {"rank", "city", "country", "index_type"}
    col_value_cols = [c for c in col_subset.columns if c not in exclude]
    col_data = {"city": col_subset["city"].values, "country": col_subset["country"].values}
    for c in col_value_cols:
        col_data[c] = col_subset[c].values
    frames.append(("cost_of_living", pd.DataFrame(col_data)))

    for index_type, keywords in INDEX_TYPE_KEYWORDS.items():
        subset = df[df["index_type"] == index_type].copy()
        subset = subset.dropna(axis=1, how="all")
        if subset.empty:
            log.warning("No rows found for index_type '%s' — skipping", index_type)
            continue
        col = find_index_column(subset.columns, keywords)
        if col is None:
            log.warning(
                "Could not find index column for '%s' (columns: %s) — skipping",
                index_type, list(subset.columns),
            )
            continue

        out_name = f"{index_type}_index"
        values = subset[col].values

        if index_type == "safety" and "crime" in col:
            values = 100 - values
            log.info("Inverted crime index to safety index (higher = safer)")

        renamed = pd.DataFrame({
            "city": subset["city"].values,
            "country": subset["country"].values,
            out_name: values,
        })
        frames.append((index_type, renamed))

    master = frames[0][1]
    for name, frame in frames[1:]:
        master = master.merge(frame, on=["city", "country"], how="outer")
        log.info("Merged %s -> %d rows, %d cols so far", name, len(master), len(master.columns))

    if master.columns.duplicated().any():
        dupes = master.columns[master.columns.duplicated()].tolist()
        log.warning("Dropping duplicate columns: %s", dupes)
        master = master.loc[:, ~master.columns.duplicated()]

    return master


def merge_worldbank(master: pd.DataFrame) -> pd.DataFrame:
    path = RAW_DIR / "worldbank_ppp.csv"
    if not path.exists():
        log.warning("%s not found — skipping PPP merge", path)
        return master
    ppp = pd.read_csv(path)[["country", "ppp_conversion_rate"]]
    merged = master.merge(ppp, on="country", how="left")
    missing = merged["ppp_conversion_rate"].isna().sum()
    log.info("Merged World Bank PPP (%d rows missing a match)", missing)
    return merged


def merge_internet_speed(master: pd.DataFrame) -> pd.DataFrame:
    fixed_path = RAW_DIR / "internet_speed_fixed.csv"
    if not fixed_path.exists():
        log.warning("%s not found — skipping internet speed merge", fixed_path)
        return master

    fixed = pd.read_csv(fixed_path)
    country_col = next((c for c in fixed.columns if "countr" in c), fixed.columns[0])
    speed_col = next((c for c in fixed.columns if "download" in c), fixed.columns[-1])
    fixed = fixed[[country_col, speed_col]].rename(
        columns={country_col: "country", speed_col: "internet_speed_mbps"}
    )
    fixed["internet_speed_mbps"] = pd.to_numeric(
        fixed["internet_speed_mbps"].astype(str).str.extract(r"([\d.]+)")[0],
        errors="coerce",
    )

    merged = master.merge(fixed, on="country", how="left")
    missing = merged["internet_speed_mbps"].isna().sum()
    log.info("Merged internet speed data (%d rows missing a match)", missing)
    return merged


def merge_geocoding(master: pd.DataFrame) -> pd.DataFrame:
    path = RAW_DIR / "cities_geocoded.csv"
    if not path.exists():
        log.warning("%s not found — skipping geocoding merge", path)
        return master
    geo = pd.read_csv(path)[["city", "country", "latitude", "longitude"]]
    merged = master.merge(geo, on=["city", "country"], how="left")
    missing = merged["latitude"].isna().sum()
    log.info("Merged geocoding (%d rows missing coordinates)", missing)
    return merged


def merge_visa_list(master: pd.DataFrame) -> pd.DataFrame:
    path = DATA_DIR / "visa_list_nz.csv"
    if not path.exists():
        log.warning("%s not found — skipping visa list merge", path)
        master["nz_accessible"] = None
        return master
    visa = pd.read_csv(path)
    merged = master.merge(visa, on="country", how="left")
    merged["nz_accessible"] = merged["nz_visa_free_or_simple"].fillna(False)
    merged = merged.drop(columns=["nz_visa_free_or_simple"])
    log.info("Merged NZ visa list (%d cities flagged accessible)", merged["nz_accessible"].sum())
    return merged


def build_master() -> pd.DataFrame:
    log.info("Building master dataset...")
    master = load_numbeo_wide()
    log.info("Base (Numbeo wide): %d city rows", len(master))

    master = merge_worldbank(master)
    master = merge_internet_speed(master)
    master = merge_geocoding(master)
    master = merge_visa_list(master)

    before = len(master)
    master = master.dropna(subset=["city"])
    if len(master) < before:
        log.info("Dropped %d rows with no city name", before - len(master))

    master = master.drop_duplicates(subset=["city", "country"])

    out_path = DATA_DIR / "master_data.csv"
    master.to_csv(out_path, index=False)
    log.info("Saved master dataset: %d rows, %d columns -> %s", len(master), len(master.columns), out_path)
    log.info("Columns: %s", list(master.columns))

    return master


if __name__ == "__main__":
    build_master()
