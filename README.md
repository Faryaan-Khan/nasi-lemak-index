# Nasi Lemak Index: Malaysia's grocery prices, decoded

Build a shopping basket and see where in Malaysia it's cheapest, which items spike before
Hari Raya and CNY, and which store types charge more for the same item.

> **Status:** Phase 0 (setup) done. Dashboard, insights and screenshots will land here in later phases.

## What it shows (planned)
1. **Where it's cheapest**: basket cost by state and district (map + ranking)
2. **Festive spikes**: which items rise before Hari Raya Aidilfitri, CNY and Deepavali, and by how much
3. **Store-type premium**: hypermarket vs minimart vs wet market for the same item, same district
4. **Simple forecast**: 4–8 weeks ahead for a few key items, with uncertainty bands

## Tech
Python · DuckDB (SQL straight on parquet files) · pandas (small tables only) · statsmodels ·
Power BI Desktop · Streamlit (optional web version)

## How to run
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\check_remote.py   # smoke test: reads PriceCatcher over HTTPS
```

## Project layout
```
data/raw, data/staging   downloaded and cleaned parquet (git-ignored)
data/marts               small aggregated tables for Power BI / Streamlit
data/reference           festive calendar, basket definitions
sql/                     numbered DuckDB SQL files
src/                     download, build, forecast, checks
docs/                    notes.md (how and why), schema.md, insights.md
dashboard/, app/         Power BI file, Streamlit app
```

## Important caveat
PriceCatcher is built for **price surveillance of specific items in specific places**, not for
measuring inflation. The Consumer Price Index (CPI) is Malaysia's official inflation measure.
"Nasi Lemak Index" is a playful basket name, not an inflation index.

## Data source and licence
PriceCatcher, Ministry of Domestic Trade and Cost of Living (KPDN) and the Department of
Statistics Malaysia (DOSM), via [OpenDOSM](https://open.dosm.gov.my/data-catalogue/pricecatcher)
and [data.gov.my](https://data.gov.my). Licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Limitations
To be written as the analysis progresses (see `docs/schema.md` for known data quirks).

---
Built with AI-assisted development.
