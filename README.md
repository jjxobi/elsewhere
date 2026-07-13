# Elsewhere — Global Lifestyle & Cost Intelligence Dashboard

**Live dashboard:** [public.tableau.com/app/profile/jesse4370/viz/ElsewhereGlobalLifestyleCostIntelligenceDashboard_17839807135540/Title](https://public.tableau.com/app/profile/jesse4370/viz/ElsewhereGlobalLifestyleCostIntelligenceDashboard_17839807135540/Title)

A parameter-driven Tableau Public dashboard that answers: *given your salary and priorities, where in the world could you live better, cheaper, or both?*

Every number on every page recalculates live around your own salary, home city, and lifestyle priorities — this isn't a static cost-of-living comparison table.

## What this project demonstrates

- A Python data pipeline that scrapes, fetches, and joins 5 independent data sources into one clean dataset
- Handling real-world scraping obstacles (bot-blocked sites, inconsistent page structures, rate limits) with graceful fallbacks and honest documentation of what didn't work
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

**Automated refresh was attempted and doesn't work:** `.github/workflows/monthly_refresh.yml` exists and is mechanically correct (permissions, current action versions, caching all verified working), but **Numbeo blocks requests from GitHub Actions' hosted-runner IP ranges** — confirmed by actually running the workflow, not assumed. This is the same fundamental issue as Expatistan's bot-blocking (documented above), just presenting as a 503 error instead of a 403. It's a network-level block that request headers can't work around. The workflow is kept in the repo for reference only.

**The real, working refresh process is local:**
1. Run the full pipeline locally (commands above) — this works fine from a normal home/residential IP
2. Commit the updated `data/master_data.csv`
3. Open `tableau/elsewhere.twb` in Tableau Public Desktop → right-click the data source → **Refresh**
4. **File → Save to Tableau Public As...** → overwrite the existing dashboard

This whole cycle takes about 15-20 minutes (mostly the geocoding step, which is cached so only new cities take time) and needs to be done manually whenever you want fresh data — there wasn't a way to make this fully hands-off with free tooling.

**Adding data for a new country/city manually:** if Numbeo adds coverage for a city that's missing, or you want to patch in data from another source:
1. Add the new rows directly to `data/master_data.csv` (or, cleaner: add them to `data/raw/numbeo_combined.csv` and re-run `build_master.py` so they get processed the same way as everything else)
2. If the city's country isn't in `data/country_regions.csv` yet, add a row there too — `build_master.py` will log a warning listing any unmapped countries so you'll know if one's missing
3. Re-run `python pipeline/build_master.py`
4. Refresh and republish in Tableau (see above)

## Methodology and honesty notes

A few things worth being upfront about:

- **Expatistan was planned as a supplementary data source** but the site blocks automated scraping (bot protection). Numbeo alone provides the full 618-city dataset used throughout.
- **The Data Story findings were fact-checked against the real dataset**, not written from assumption. Several original hypotheses turned out to be wrong or imprecise once checked — for example, the "internet speed has no correlation with cost" hypothesis was revised after finding a real moderate correlation (r = 0.54).
- **The NZ visa accessibility list is a representative, manually-curated list**, not an exhaustive official source — treat it as broadly indicative rather than authoritative for actual visa planning.
- **Full automation isn't possible with free tooling, and that's documented rather than hidden.** GitHub Actions can't run the Numbeo scraper (its IP ranges are blocked - confirmed by testing, not assumed) and Tableau Public doesn't support command-line republishing. Both the data refresh and the dashboard republish are manual steps, done locally (see "Keeping the data current" above).

## Stack

Python (requests, BeautifulSoup, pandas, geopy) for the data pipeline · GitHub Actions available for manual/local-runner use · Tableau Public for the dashboard and free permanent hosting.
