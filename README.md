# Elsewhere — Global Lifestyle & Cost Intelligence Dashboard

**Live dashboard:** [public.tableau.com/app/profile/jesse4370/viz/ElsewhereGlobalLifestyleCostIntelligenceDashboard/Title](https://public.tableau.com/app/profile/jesse4370/viz/ElsewhereGlobalLifestyleCostIntelligenceDashboard/Title)

A parameter-driven Tableau Public dashboard that answers: *given your salary and priorities, where in the world could you live better, cheaper, or both?*

Every number on every page recalculates live around your own salary, home city, and lifestyle priorities — this isn't a static cost-of-living comparison table.

## What this project demonstrates

- A Python data pipeline that scrapes, fetches, and joins 5 independent data sources into one clean dataset
- Handling real-world scraping obstacles (bot-blocked sites, inconsistent page structures, rate limits) with graceful fallbacks and honest documentation of what didn't work
- Verifying claims against actual data rather than assuming a plan is correct (several findings on the Data Story page were revised after checking the real numbers — see Methodology below)
- A fully parameter-driven Tableau workbook: salary, home city, and comparison city all drive live recalculation across every chart
- Free-tier tooling throughout: Python, GitHub Actions, and Tableau Public — no paid services

## The 5 dashboard pages

| Page | What it shows |
|---|---|
| **World Map** | Every city colored by whether you'd be better or worse off there, given your salary |
| **Shortlist** | Your top 30 matches, ranked, with a detail matrix showing exactly why each city scores where it does |
| **City Deep Dive** | Head-to-head comparison of any two cities — radar chart, cost breakdown, plain-language callouts |
| **Seoul Spotlight** | A personal case study — my own relocation question, answered with the same tooling |
| **Data Story** | Five findings from analyzing the dataset, each verified against the actual numbers (not assumed) |

## Data pipeline

| Script | Purpose |
|---|---|
| `pipeline/scrape_numbeo.py` | Scrapes 6 Numbeo rankings pages (cost of living, quality of life, safety, healthcare, pollution, traffic) — 618 cities |
| `pipeline/fetch_worldbank.py` | Pulls PPP conversion rates from the World Bank's free public API — 197 countries |
| `pipeline/fetch_speedtest.py` | Internet speed data via Wikipedia's Speedtest-sourced table (Ookla no longer offers a direct CSV) |
| `pipeline/geocode_cities.py` | Adds lat/long via OpenStreetMap's free Nominatim API, with local caching |
| `pipeline/build_master.py` | Joins everything into `data/master_data.csv`, the file Tableau reads |

Static reference files: `data/visa_list_nz.csv` (NZ visa-free destinations, manually curated) and `data/country_regions.csv` (continent/region mapping for grouping in the Data Story charts).

## Running the pipeline locally

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

python pipeline/scrape_numbeo.py
python pipeline/fetch_worldbank.py
python pipeline/fetch_speedtest.py
python pipeline/geocode_cities.py
python pipeline/build_master.py
```

This produces an updated `data/master_data.csv`.

## Keeping the data current

**Automated (via GitHub Actions):** `.github/workflows/monthly_refresh.yml` runs on the 1st of every month, re-running the full pipeline and committing an updated `master_data.csv` automatically. You can also trigger it manually from the Actions tab.

**What's NOT automated, and why:** Tableau Public doesn't support `tabcmd` (Tableau's command-line publish tool only works with paid Tableau Server/Cloud), so republishing the dashboard itself still requires a manual step:
1. Open `tableau/elsewhere.twb` in Tableau Public Desktop
2. Right-click the data source → **Refresh** (pulls in the latest `master_data.csv`)
3. **File → Save to Tableau Public As...** → overwrite the existing dashboard

This takes about 2 minutes and is worth doing after each automated data refresh, or whenever you've manually added new data (see below).

**Adding data for a new country/city manually:** if Numbeo adds coverage for a city that's missing, or you want to patch in data from another source:
1. Add the new rows directly to `data/master_data.csv` (or, cleaner: add them to `data/raw/numbeo_combined.csv` and re-run `build_master.py` so they get processed the same way as everything else)
2. If the city's country isn't in `data/country_regions.csv` yet, add a row there too — `build_master.py` will log a warning listing any unmapped countries so you'll know if one's missing
3. Re-run `python pipeline/build_master.py`
4. Refresh and republish in Tableau (see above)

## Methodology and honesty notes

- **Expatistan was planned as a supplementary data source** but the site blocks automated scraping (bot protection). Numbeo alone provides the full 618-city dataset used throughout.
- **The NZ visa accessibility list is a representative, manually-curated list**, not an exhaustive official source — treat it as broadly indicative rather than authoritative for actual visa planning.
- **Automated republishing to Tableau Public isn't possible** with free tooling (see above) — data refresh is automated, publishing the updated workbook is a 2-minute manual step.

## Stack

Python (requests, BeautifulSoup, pandas, geopy) for the data pipeline · GitHub Actions for scheduled data refresh · Tableau Public for the dashboard and free permanent hosting.
