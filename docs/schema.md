# PriceCatcher schema and known quirks

All figures below were checked on 24 Nov 2026 with DuckDB reading the files directly from
`https://storage.data.gov.my/pricecatcher/` (see `src/check_remote.py`).

## Files (URL pattern confirmed working)
| File | URL | Size | Rows |
|---|---|---|---|
| Item lookup | `.../lookup_item.parquet` | 17 KB | 797 |
| Premise lookup | `.../lookup_premise.parquet` | 142 KB | 3,932 |
| Monthly prices | `.../pricecatcher_YYYY-MM.parquet` | ~2–3 MB | ~1.4–2.5M per month |

Monthly files exist from `2022-01` up to the current month (`2026-11` responded, partial month).

## Columns
**pricecatcher_YYYY-MM** (fact table, one row = one price seen at one shop on one day)
| column | type | meaning |
|---|---|---|
| date | DATE | day the price was collected |
| premise_code | BIGINT | shop ID, joins to lookup_premise |
| item_code | BIGINT | product ID, joins to lookup_item |
| price | DOUBLE | price in RM for the item's stated unit |

**lookup_item**: item_code, item, unit, item_group, item_category

**lookup_premise**: premise_code, premise, address, premise_type, state, district

## Sample numbers
| Month | Rows | First day | Last day | Days with data |
|---|---|---|---|---|
| 2022-01 | 2,454,101 | 2022-01-01 | 2022-01-31 | 30 |
| 2026-09 | 1,742,320 | 2026-09-01 | 2026-09-29 | 28 |
| 2026-10 | 1,359,706 | 2026-10-10 | 2026-10-31 | 22 |

2026-10 covers 339 distinct items at 2,141 premises; median price RM 8.99.
Premise lookup: 16 states/territories; biggest types are Pasar Mini (926), Pasar Raya / Supermarket
(888) and Kedai Runcit (623), plus 181 Hypermarkets.

## Quirks and how `sql/01_clean.sql` handles them
Checked on the last 24 months (Dec 2024 to Nov 2026, 47,365,287 rows). Details in
`notebooks/01_profile.ipynb`.

| # | Quirk | Handling |
|---|---|---|
| 1 | **Placeholder rows**: premise_code `-1` "Unknown Premise" (no type/state) and item_code `-1` (no name). No price rows actually use them. | Dropped from the dimension tables |
| 2 | **Trailing spaces**: premise_type has `Pasar Basah ` (338 shops, with a space) and `Pasar Basah` (22). | `trim()` on every text column |
| 3 | **Item codes missing from the lookup**: 41 codes, 896,671 rows (1.9%). Every premise_code matched. | Kept, `item_known = false` |
| 4 | **Missing days**: e.g. no data for 1–9 Oct 2026 or 30 Sep 2026; Feb 2026 has 25 of 28 days. | Marts will carry observation counts |
| 5 | **Survey redesign mid-2025**: shops ~1,670 → ~2,390 (Jul 2025), items ~515 → ~345 (Aug 2025). | Compare like with like across the break |
| 6 | **No cooked food in recent data**: restaurants, food courts and medan selera are in the lookup but have 0 prices in these 24 months. | Nothing to do; noted for the dashboard |
| 7 | **100x typos**: e.g. baby formula at RM 8,245 vs a RM 79 median (missing decimal point). | Flagged `is_outlier`; `price_to_median` shows the ratio |
| 8 | **Price-controlled items** (eggs): most shops charge the same price, so IQR is often 0. | Outlier spread has a floor of 10% of the median |
| 9 | No duplicate (date, shop, item) rows; no null or zero prices. | None needed |

## Clean table: `data/staging/prices_clean.parquet`
| column | meaning |
|---|---|
| date, week_start (Monday), month | when the price was collected |
| premise_code, premise_type, state, district, region | the shop; region = East Malaysia (Sabah, Sarawak, Labuan) or Peninsular Malaysia |
| item_code, item, unit, item_group, item_category | the product (NULL if `item_known` is false) |
| price | RM, as collected |
| item_month_median | median price of that item across Malaysia that month |
| price_to_median | price ÷ item_month_median (≈100 means a missing decimal point) |
| item_known | false if the item code isn't in the item lookup |
| is_outlier | true if price is more than 3 × spread from the monthly median (spread = max(IQR, 10% of median)) |

0.71% of rows (336,323) are flagged as outliers.
