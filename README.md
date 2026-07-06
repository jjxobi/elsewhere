# Elsewhere — Global Lifestyle & Cost Intelligence Dashboard

A parameter-driven Tableau Public dashboard answering: given my salary and
priorities, where in the world could I live better, cheaper, or both?

- Live dashboard: (link added after Tableau publish)
- Data: Numbeo, Expatistan, World Bank PPP, Speedtest Global Index
- Refresh: Automated monthly via GitHub Actions
- Stack: Python (requests, BeautifulSoup, pandas, geopy) + Tableau Public

## Running the pipeline locally

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python pipeline/scrape_numbeo.py
