# Data Sources & Methodology

Numbeo: cost of living, quality of life, safety, healthcare, pollution, traffic - scraped
Expatistan: supplementary cities - scraped
World Bank: PPP conversion rates - free API
Speedtest Global Index: internet speeds - CSV download
NZ MFAT: visa-free country list - manual annual extraction

Dedup rule: Numbeo takes precedence over Expatistan where both have a city.
Quality filter: cities with fewer than 5 Numbeo contributors are excluded.
Update cadence: monthly via GitHub Actions.
