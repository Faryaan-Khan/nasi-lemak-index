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

## Quirks found so far (to handle in Phase 2)
1. **Placeholder rows**: premise_code `-1` "Unknown Premise" with no type/state, and item_code `-1`
   with no name. Drop these.
2. **Trailing spaces in category names**: premise_type has both `Pasar Basah` (338) and
   `Pasar Basah ` (22). Trim all text columns.
3. **Item codes missing from the lookup**: 19,798 rows in 2026-10 (~1.5%) have an item_code that is
   not in lookup_item. Every premise_code matched. Keep them flagged, not silently dropped.
4. **Missing days**: 2026-10 has no data for 1–9 October; 2026-09 has no 30 September. Weekly
   aggregates need an observation count so thin weeks are visible.
5. **Volume falls over time**: ~2.45M rows in Jan 2022 vs ~1.4–1.7M in late 2026.
6. **Restaurants and food courts** (Restoran Melayu, Medan Selera, Foodcourt...) are premise types
   too. They likely sell cooked food, so the store-type premium analysis should probably focus on
   grocery retail types. To confirm in Phase 2.
7. No null or zero prices in the sampled months. Outliers (unit mix-ups, typos) still to be checked.
