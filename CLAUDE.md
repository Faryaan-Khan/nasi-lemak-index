# Nasi Lemak Index — Malaysia's grocery prices, decoded

## What this project is
An interactive analytics project on Malaysia's government PriceCatcher data. Users build a shopping
basket and see:
1. **Where it's cheapest**: basket cost by state and district, shown as a map and a ranking.
2. **Festive spikes**: which items rise before Hari Raya Aidilfitri, CNY and Deepavali, by how much, and how long before.
3. **Store-type premium**: how much more hypermarkets, minimarts, wet markets and other premise types charge for the same item in the same district.
4. **Simple forecast**: next 4–8 weeks of price for a few key items, with uncertainty bands.

Purpose: a portfolio project for data analyst / BI internship applications at retail, FMCG, banks
and consulting firms. It must show SQL on millions of rows, Power BI, a simple forecast, and clear
written insights.

## About me (the developer)
- Final-year CS student (data science track). I build with AI-assisted coding. I'm comfortable with
  Python basics and data concepts, but I'm **not** a strong software engineer.
- **Explain what you're doing in plain language as you go.** Keep code simple and readable. Choose
  boring, well-documented tools over clever ones. No over-engineering, no frameworks I don't need.
- I'm on **Windows**. Give PowerShell commands, not bash. Use `pathlib` for paths.
- I need to explain every part of this project in an interview, so after each phase write a short
  "what this does and why" note in `docs/notes.md`.

## Data (verify URLs before relying on them)
Source: OpenDOSM / data.gov.my PriceCatcher (Ministry of Domestic Trade + DOSM). Licence CC BY 4.0,
which requires attribution in the dashboard and README.
- Lookup tables:
  - `https://storage.data.gov.my/pricecatcher/lookup_premise.parquet`
    (premise_code, premise, address, premise_type, state, district)
  - `https://storage.data.gov.my/pricecatcher/lookup_item.parquet`
    (item_code, item, unit, item_group, item_category)
- Monthly price files: expected pattern `https://storage.data.gov.my/pricecatcher/pricecatcher_YYYY-MM.parquet`
  (columns: date, premise_code, item_code, price). Data starts around 2022-01. **Check the pattern
  against https://open.dosm.gov.my/data-catalogue/pricecatcher first.** If it's wrong, find the real one
  and update this file.
- Volume: roughly 1–2M+ rows per month, so ~100M rows in total. Don't load everything into pandas.
- Known quirks to handle and document: placeholder premise rows (e.g. premise_code -1 with an empty
  name), missing joins, price outliers (unit mix-ups, typos), and items or premises that appear or
  disappear over time.
- **Important caveat (put it in the dashboard):** DOSM says PriceCatcher is for price surveillance of
  specific items in specific places, not for measuring inflation. CPI is the official inflation
  measure. Never call this an inflation index. "Nasi Lemak Index" is a playful basket name only.
  Optional extra: compare our basket trend with the official CPI food series as a sanity check.

## Tech stack
- **Python 3.11+**, virtual env in `.venv`
- **DuckDB** for all heavy SQL, querying the parquet files directly. This is the main "SQL on
  millions of rows" skill being shown, so keep the SQL in readable `.sql` files in `sql/`, not hidden
  inside Python strings.
- **pandas** only for small, already-aggregated tables
- **statsmodels** for the forecast (seasonal naive baseline + ETS/Holt-Winters). No deep learning.
- **Power BI Desktop** for the main dashboard. It reads small aggregated CSV/parquet exports from
  `data/marts/`, never the raw 100M rows.
- **Streamlit** (later phase, optional): a lightweight public web version, because Power BI
  "Publish to web" may be blocked on a student account. Deploy to Streamlit Community Cloud.
- `requests` for downloads, `pytest` for a few data-quality tests.

## Folder structure
```
nasi-lemak-index/
  CLAUDE.md
  README.md
  requirements.txt
  .gitignore            # ignores data/raw, data/staging, .venv, *.pbix backups
  data/
    raw/                # downloaded parquet files (git-ignored)
    staging/            # cleaned parquet (git-ignored)
    marts/              # small aggregated tables for Power BI / Streamlit (committed if < ~50MB)
    reference/          # festive_calendar.csv, basket definitions
  sql/                  # numbered DuckDB SQL files: 01_clean.sql, 02_daily_item_district.sql ...
  src/
    download.py         # fetch lookups + monthly files, skip ones already downloaded
    build.py            # runs the sql/ files in order with DuckDB
    forecast.py
    checks.py           # data quality checks
  notebooks/            # exploration only
  dashboard/            # .pbix file + screenshots
  app/                  # Streamlit app (later)
  docs/
    notes.md            # plain-language notes per phase (for interviews)
    insights.md         # the 5–8 headline findings, written for a non-technical reader
  tests/
```

## Phases (do one at a time, stop after each so I can review and commit)
**Phase 0 — Setup.** Create the venv, requirements.txt, .gitignore, README skeleton and the folder
structure. Check that DuckDB can read one remote parquet file.

**Phase 1 — Download.** `src/download.py` fetches both lookups and the monthly files (start with the
last 24 months, with an option for all). It must be resumable and print progress. Print the row
count and size per month.

**Phase 2 — Explore & clean.** Notebook profiling the data: items per category, premises per type and
state, date coverage, price distributions. Then `sql/01_clean.sql`:
- join the lookups, drop placeholder premises
- flag outliers per item (e.g. outside median ± k×IQR within item × month) instead of silently deleting them
- standardise state and district names
Write the findings to `docs/notes.md`.

**Phase 3 — Marts (aggregated tables).** DuckDB SQL producing small tables:
- `item_district_week`: median price per item × district × week (+ observation count)
- `item_premisetype_district_month`: median price per item × premise type × district × month
- `basket_cost_district_week`: cost of predefined baskets per district per week
- `festive_window`: each item's price index from 8 weeks before to 2 weeks after each festival,
  relative to its own baseline (weeks −12 to −9)
Use medians, not means. Only report a figure when enough observations back it, and show the count.

**Phase 4 — Baskets & festive calendar.**
- `data/reference/baskets.csv`: a "Nasi Lemak" basket (rice, coconut milk, eggs, ikan bilis,
  cucumber, chilli, onion, groundnuts) plus "Student weekly basket" and "Family weekly basket".
  Match them to real `item_code`s from lookup_item and confirm the units.
- `data/reference/festive_calendar.csv`: dates of Hari Raya Aidilfitri, CNY and Deepavali for 2022–2027.
  **Look up the official Malaysian public holiday dates. Don't guess.**

**Phase 5 — Analysis.** Answer, with numbers:
- Which states/districts have the cheapest and most expensive basket, and how big the gap is in RM
- The top 10 items with the biggest pre-Raya and pre-CNY rises: average % rise and when it peaks
- The store-type premium for the same item in the same district (keep it like-for-like)
- Whether East Malaysia is more expensive, and for which items
Write the results to `docs/insights.md` in plain English, one chart idea per insight.

**Phase 6 — Forecast.** For 3–5 key items (e.g. chicken, eggs, a rice item, onions, chilli),
forecast national weekly median price 4–8 weeks ahead. Compare ETS against a seasonal-naive
baseline on a holdout period and report MAPE. Keep it honest: if ETS doesn't beat the baseline, say so.

**Phase 7 — Power BI dashboard.** Pages: Overview (KPI cards + caveat), Basket Builder (pick items →
cost by state/district map + table), Festive Spikes, Store-Type Premium, Forecast. Guide me step by
step in Power BI Desktop, since that part isn't code: data model, relationships, DAX measures
(list each one with an explanation), and slicers. Use a consistent colour theme. Add a data source
and licence footer.

**Phase 8 — Streamlit version (optional).** The same core views (basket builder, festive spikes),
reading from `data/marts/`, deployable for free.

**Phase 9 — Polish.** README with a screenshot/GIF, key insights, how to run, data source and
licence, limitations, and "Built with AI-assisted development". Add a short LinkedIn-post draft
of the top 3 insights to `docs/`.

## Rules
- Never invent data, dates or numbers. If something isn't in the data, say so.
- Small, reviewable steps. After each phase: summarise what changed, how to run it, and what I
  should check.
- Run the code and show real output before saying something works.
- Keep memory in mind: never `SELECT *` the full raw data into pandas.
- **Git: I am the only author.** Never add "Co-Authored-By: Claude", a Claude session link, or a
  "Generated with Claude Code" footer to commits or PRs. Claude commits and pushes to my GitHub
  itself, but only after all tests and checks pass and it is confident the work is ready. Never
  commit secrets or large raw data files.
