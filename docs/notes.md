# Project notes (plain language, for interviews)

## Phase 0: Setup

**What I did**
- Created the folder layout (`data/`, `sql/`, `src/`, `docs/`, `dashboard/`, `app/`, `tests/`).
- Made a Python virtual environment (`.venv`) and a `requirements.txt` with DuckDB, pandas,
  pyarrow, requests, statsmodels, jupyter, matplotlib and pytest.
- Added a `.gitignore` so the big raw data, the venv and any secrets never get committed.
- Wrote `src/check_remote.py`, a smoke test where DuckDB reads PriceCatcher parquet files straight
  over HTTPS without downloading them first.
- Documented the schema and the first data quirks in `docs/schema.md`.

**Why these choices**
- **DuckDB** is a database that runs inside Python with no server to install. It can run SQL
  directly on parquet files, which is perfect for ~100M rows on a laptop. pandas would need the
  whole dataset in memory; DuckDB only reads the columns and rows a query needs.
- **Parquet** is a compressed, column-based file format. A month of ~1.4M prices is only ~2 MB.
- **A venv** keeps this project's library versions separate from anything else on my machine, so
  anyone can rebuild the same setup from `requirements.txt`.

**What I checked**
- The URL pattern in CLAUDE.md is correct: lookups and monthly files from 2022-01 to 2026-11 all
  respond.
- DuckDB read 1,359,706 rows for October 2026 and summarised them in seconds.
- Early quirks: placeholder `-1` codes, a `Pasar Basah ` value with a trailing space, ~1.5% of rows
  with item codes not in the item lookup, and missing days (1â€“9 Oct 2026).

**Interview one-liner**
"I validated the government data source first, then used DuckDB so I could query millions of rows
with plain SQL on a laptop, and I wrote down every data quirk before cleaning anything."

## Phase 1: Download and daily auto-update

**What I did**
- `src/download.py` downloads both lookup tables and the monthly price files into `data/raw/`
  (last 24 months by default, `--all` for everything since January 2022).
- It prints, for each month, whether the file was new, updated or skipped, plus its size, row
  count and date range, and writes a one-row-per-month summary to `data/marts/coverage_monthly.csv`.
- `src/checks.py` checks the downloaded data: lookups not empty, the expected columns, no missing
  or zero prices, and the newest date is less than 14 days old.
- `tests/test_download.py` tests the month-list logic (e.g. crossing New Year).
- `.github/workflows/daily-update.yml` is a GitHub Action that runs every day at 10 pm Malaysia
  time on GitHub's servers: download, tests, checks, then commit the updated summary tables.

**Why these choices**
- **Only fetch what changed.** Before downloading, the script asks the server for each file's
  ETag (a fingerprint that changes whenever the file changes) and compares it with the one saved
  last time in `data/raw/_manifest.json`. Finished months never change, so they are skipped. The
  current month grows every day, so it is re-downloaded. A full 24-month re-run with nothing new takes about 10 seconds.
- **Resumable.** Each file is written as `.part` first and only renamed when complete, and the
  manifest is saved after every file, so an interrupted run just picks up where it stopped.
- **Checks before commit.** If the government data ever arrives broken, the Action fails and
  nothing is committed, so the dashboards never show bad numbers.
- **GitHub Actions** is free for public repos and needs no server of my own. Raw files are kept
  in the Actions cache, not in git, because git is for code and small tables, not 100M rows.

**What I saw (24 Nov 2026 run)**
- 24 months (Dec 2024 to Nov 2026) = **47,365,287 rows**, about 60 MB of parquet on disk.
- Monthly volume fell from ~2.6M rows in early 2025 to ~1.4 to 1.9M in 2026.
- Many months have missing days (e.g. Feb 2026 has 25 of 28 days; Oct 2026 starts on the 10th),
  so later weekly figures need observation counts.
- All checks passed: 0 bad prices, 0 missing keys, latest date 2026-11-24.

**Interview one-liner**
"The pipeline refreshes itself daily on GitHub Actions, downloads only what changed using ETags,
and refuses to publish if data-quality checks fail."

## Phase 2: Explore and clean

**What I did**
- `notebooks/01_profile.ipynb` profiles the 47M raw rows with DuckDB: date coverage, shops per
  type and state, items per category, price extremes, and the result of the outlier rule.
- `sql/01_clean.sql` builds the clean table `data/staging/prices_clean.parquet` (47,365,287 rows,
  ~270 MB) plus tidy `dim_item` and `dim_premise` tables.
- `src/build.py` runs every file in `sql/` in order. The whole clean step takes ~10 seconds.
- `tests/test_clean.py` adds 7 tests on the cleaned data (no placeholders, no rows lost, names
  trimmed, East Malaysia defined correctly, outlier share small, 100x typos all flagged).

**What the profiling found**
- **Survey changed in mid-2025:** shops covered jumped from ~1,670 to ~2,390 in July 2025, and
  the item list shrank from ~515 to ~345 in August 2025. Trends must compare like with like.
- **No cooked food in recent data:** restaurants and food courts are in the shop list but have
  zero prices in the last 24 months. Active shop types: supermarkets (53% of prices), wet markets,
  hypermarkets, minimarts, sundry shops, and a few wholesalers.
- **Fresh produce dominates:** chicken, fish, vegetables and eggs are ~61% of all named prices.
- **Unknown items:** 41 item codes (1.9% of rows) are not in the item lookup, so we can't name them.
- **Typos:** the highest prices (RM 6,000 to 8,000 for baby formula that normally costs ~RM 80) are
  missing decimal points, i.e. 100x too high.
- **Trailing spaces:** 338 wet markets are labelled `Pasar Basah ` (with a space) and 22 `Pasar Basah`.
- Clean on other fronts: no duplicate prices for the same shop, item and day, no zero or missing prices.

**Cleaning decisions and why**
| Decision | Why |
|---|---|
| Drop placeholder shop/item `-1` | They have no name or location, so they can't be analysed |
| `trim()` all text | Stops one category splitting into two because of a hidden space |
| Keep unknown items, flag `item_known = false` | Deleting real data silently is worse than labelling it |
| **Flag** outliers, never delete | The decision stays visible and reversible; marts simply filter `NOT is_outlier` |
| Outlier = more than 3 x spread from the item's monthly median | Medians and IQR aren't pulled around by the typos themselves |
| Spread = larger of IQR and 10% of median | Price-controlled items (eggs) often have IQR = 0, which would flag a 10-sen difference |
| Add `region` (East = Sabah, Sarawak, Labuan) | Needed for the "is East Malaysia more expensive?" question |
| Add `week_start` and `month` | Phase 3 marts group by these |

Result: **336,323 prices flagged (0.71%)**, including every 100x typo. The baby and dry goods
groups have the most flags (~2% and ~1%), which fits pack-size and unit mix-ups.

**Performance lesson**
The first version sorted all 47M rows before writing them and took 7 minutes. Removing the
unnecessary `ORDER BY` brought it to 10 seconds. Sorting is expensive; only do it when needed.

**Interview one-liner**
"I profiled 47 million rows before touching them, found that the survey's coverage changed in
mid-2025 and that some prices were 100 times too high, and flagged outliers with a robust
median-and-IQR rule instead of deleting them, so every cleaning decision is visible and reversible."

## Phase 3: Summary tables (marts)

**What I did**
- `sql/02_marts.sql` turns the 47M clean prices into six small tables in `data/marts/`:

| Table | One row per | Rows | Where it lives |
|---|---|---|---|
| `dim_item.csv` | item (name, unit, category) | 507 | git |
| `dim_district.csv` | district (region, shops of each type) | 169 | git |
| `item_national_week.csv` | item x week, all Malaysia (median, 25th/75th percentile) | ~34k | git |
| `item_state_week.parquet` | item x state x week | ~417k | GitHub release |
| `item_district_week.parquet` | item x district x week | ~2.2M | GitHub release |
| `item_premisetype_district_month.parquet` | item x store type x district x month | ~825k | GitHub release |

- `tests/test_marts.py` adds 18 tests (one row per key, at least 3 shops behind every figure,
  no missing or zero prices, every item and district has a name, percentiles in the right order).
- The daily GitHub Action now also cleans the data, rebuilds the marts and runs all 28 tests
  before publishing anything.

**Why these choices**
- **Medians, not means.** A few typo prices can drag an average a long way; a median barely moves.
- **At least 3 shops behind every figure**, with `n_obs` (prices) and `n_shops` (shops) on every
  row. One shop's price isn't a "district price". Counting shops, not prices, matters because
  one shop reports the same item every day.
- **Outliers and unnamed items are left out** of every mart (they stay flagged in staging).
- **Codes, not names, in the big tables.** Names live once in `dim_item`; Power BI joins them on
  `item_code`. This is a star schema: small dimension tables around fact tables.
- **`n_days` on the national table** shows partial weeks (e.g. the current week).
- **Big tables go to a GitHub release, not git.** Git keeps every version of every file forever.
  Committing ~8 MB of changed tables daily would add gigabytes a year. A release called
  `data-latest` is overwritten each night and has a fixed download link Power BI can read.

**Sanity checks on the numbers (week of 16 Nov 2026)**
- Chicken (standard, 1 kg): RM 8.49 national median; cheapest state Johor RM 7.99, dearest Sabah
  RM 12.89.
- Grade A eggs (30): RM 14.99; Indian onions (1 kg): RM 4.20.
- First hint for Phase 5: for chicken in the same district and month, wet markets charge more
  than hypermarkets (median gap ~20%). To be tested properly across items in Phase 5.

**Still to come in Phase 4:** the basket-cost and festive-window tables need the basket
definitions and the official festival dates first, so they are built in Phase 4.

**Interview one-liner**
"I aggregated 47 million prices into a small star schema of medians, only reporting a figure when
at least three shops back it, and published the large tables as nightly release files so the
git history stays small."

**Fix after the first cloud run:** the 25th/75th percentiles came out one cent different on
GitHub's Linux server than on my Windows laptop (floating-point rounding when interpolating
between two prices), which would have caused a noisy commit every day. They now use
`quantile_disc`, which returns an actual observed price, so results are identical everywhere.
Week and month columns are now plain dates instead of timestamps.

## Phase 4: Baskets and festive calendar

**What I did**
- `data/reference/festive_calendar.csv`: Chinese New Year, Hari Raya Aidilfitri and Deepavali for
  2022 to 2027, every row with its source. 2023 to 2027 come from the Prime Minister's Department
  federal holiday schedules (kabinet.gov.my). Hari Raya dates depend on moon sighting, so past
  years were checked against the Keeper of the Rulers' Seal's declaration (e.g. 2026 was declared
  on 19 March for Saturday 21 March). 2022 isn't on the JPM page, so it comes from the official
  declaration (Raya) and state holiday lists (CNY, Deepavali). 2027 dates are marked `scheduled`.
- `data/reference/baskets.csv`: three baskets (Nasi Lemak, Student weekly, Family weekly) with
  real `item_code`s, the exact unit from the government item list, and a quantity.
- `sql/03_baskets_festive.sql` builds:
  - `basket_cost_national_week.csv`, `basket_cost_state_week.csv`, `basket_cost_district_week.parquet`
  - `festive_window.csv`: for every festival and item, weekly price index from 12 weeks before to
    2 weeks after, where the item's own baseline (median of weeks -12 to -9) = 100.
- `tests/test_reference.py`: 10 tests (every festival has a dated, sourced row per year; spot checks
  against official dates; basket items and units match the government list; basket costs only for
  complete baskets; festive index averages 100 in the baseline weeks).
- **The pipeline now uses the full history since January 2022: 130.5M rows.** One extra year of
  festivals isn't enough to compare patterns; five years is.

**Decisions and why**
| Decision | Why |
|---|---|
| Ikan bilis is **not** in the Nasi Lemak basket | It was dropped from the survey in July 2025 (last price 14 Jul 2025), so the basket would break mid-way. Said openly rather than swapped for something else |
| Rice = Beras Super Cap Rambutan 5% 10 kg | There's no unbranded rice item. This one is priced every week since Jan 2022, so baskets compare across all years (another popular brand only starts in Apr 2024) |
| Quantities are illustrative | They are my assumptions about a household's needs, not data. Item codes, units and prices are data |
| A basket cost is only shown when every item has a price there that week | A partial basket would look falsely cheap. Trade-off: the 18-item Family basket is complete in 47 districts, the Nasi Lemak basket in 77 |
| Festive baseline = weeks -12 to -9 | Far enough before the festival that festive buying hasn't started yet |
| Only festivals that have already happened | A future festival would show a half-empty window |
| CNY 2022 has no window | Its baseline weeks are in late 2021, before the data starts |

**First numbers (national, weekly medians)**
- Nasi Lemak basket: RM 19.42 average in 2022 vs RM 21.50 in 2026 so far. Student weekly
  RM 51.91 vs RM 56.12. Family weekly RM 135.57 vs RM 143.49.
- Latest Family weekly basket by state ranges from RM 141.67 (Kedah) upward; Sabah is missing
  because not every item has 3+ shops there each week.

**Performance lesson: 130 million rows on a laptop**
- The first full-history build filled 62 GB of temporary disk and crashed. DuckDB spills to disk
  when a query needs more memory than the laptop has (16 GB).
- Cause: one query asked for two `COUNT(DISTINCT ...)` at once over 130M rows. Each one alone takes
  about a minute; together they blew up. Fix: compute them in two steps and join.
- The detailed district / state / store-type tables now use the latest 104 weeks; only the national
  table keeps the full history (that's all the festive analysis needs).
- `src/build.py` now caps DuckDB's temporary disk use at 20 GB, so a heavy query fails cleanly
  instead of filling the disk. Full build: ~6 to 7 minutes.

**Data quirks found in the older data**
- 156 rows (2022 to 2023) use the placeholder shop `-1`, 1 row (2022) the placeholder item `-1`,
  and 273 rows (2024) point to shops missing from the shop list. All dropped (no location or name).

**Interview one-liner**
"I took the festival dates from the Prime Minister's Department schedules and checked the moon-sighting
ones against the official declarations, built baskets from real item codes and said openly when an
item, ikan bilis, had been dropped from the survey, and then scaled the pipeline to 130 million
rows by finding the one query that blew the memory."

**Fixes after the first full-history cloud run:** the data-quality gate stopped the run (nothing
was published). The 2022 files store `date` as a midnight timestamp instead of a plain date,
which broke the freshness check; the clean table now casts every date to `DATE`, with a test.
Basket costs now add up in exact `DECIMAL` arithmetic, because adding floating-point numbers in a
different order (DuckDB works in parallel) changed the last cent between runs.
