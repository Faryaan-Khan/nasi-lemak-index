-- 02_marts.sql
-- Small aggregated tables ("marts") for Power BI and Streamlit, built from the clean table.
-- Run with:  .\.venv\Scripts\python.exe src\build.py   (after 01_clean.sql)
--
-- Rules used in every mart
--   * Only named items (item_known) and only prices NOT flagged as outliers.
--   * Medians, not means: one shop's typo can't drag a median around.
--   * A figure is only kept when at least 3 different shops back it (n_shops >= 3),
--     and every row carries its counts (n_obs = prices, n_shops = shops) so users can judge it.
--   * Text (item names, units, categories) lives in dim_item; marts keep item_code only, which
--     keeps them small. Join on item_code in Power BI.
--
-- Outputs (data/marts/)
--   dim_item.csv                                 item names, units, categories        (committed)
--   dim_district.csv                             state, district, region, shop counts (committed)
--   item_national_week.csv                       item x week, all Malaysia            (committed)
--   item_state_week.parquet                      item x state x week                  (GitHub release)
--   item_district_week.parquet                   item x district x week               (GitHub release)
--   item_premisetype_district_month.parquet      item x store type x district x month (GitHub release)


-- Only the rows the marts are allowed to use.
CREATE OR REPLACE TEMP VIEW usable AS
SELECT *
FROM read_parquet('data/staging/prices_clean.parquet')
WHERE item_known
  AND NOT is_outlier;


-- 1. Item lookup (only items that actually have prices) --------------------------------
COPY (
    SELECT i.item_code, i.item, i.unit, i.item_group, i.item_category
    FROM read_parquet('data/staging/dim_item.parquet') AS i
    WHERE i.item_code IN (SELECT DISTINCT item_code FROM usable)
    ORDER BY i.item_code
) TO 'data/marts/dim_item.csv' (HEADER);


-- 2. District lookup ------------------------------------------------------------------
-- How many shops of each type were surveyed in each district (last 24 months).
COPY (
    SELECT state, district, region,
           COUNT(DISTINCT premise_code) AS shops,
           COUNT(DISTINCT premise_code) FILTER (WHERE premise_type = 'Hypermarket')              AS hypermarkets,
           COUNT(DISTINCT premise_code) FILTER (WHERE premise_type = 'Pasar Raya / Supermarket') AS supermarkets,
           COUNT(DISTINCT premise_code) FILTER (WHERE premise_type = 'Pasar Mini')               AS minimarkets,
           COUNT(DISTINCT premise_code) FILTER (WHERE premise_type = 'Pasar Basah')              AS wet_markets,
           COUNT(DISTINCT premise_code) FILTER (WHERE premise_type = 'Kedai Runcit')             AS sundry_shops
    FROM usable
    GROUP BY ALL
    ORDER BY state, district
) TO 'data/marts/dim_district.csv' (HEADER);


-- 3. National weekly median per item (used for trends and the forecast) -------------------
COPY (
    SELECT item_code,
           week_start,
           round(median(price), 2)          AS median_price,
           quantile_disc(price, 0.25)       AS p25_price,  -- an actual observed price (no interpolation), so results are identical on every computer
           quantile_disc(price, 0.75)       AS p75_price,
           COUNT(*)                         AS n_obs,
           COUNT(DISTINCT premise_code)     AS n_shops,
           COUNT(DISTINCT date)             AS n_days   -- < 7 means a partial or patchy week
    FROM usable
    GROUP BY ALL
    HAVING COUNT(DISTINCT premise_code) >= 3
    ORDER BY item_code, week_start
) TO 'data/marts/item_national_week.csv' (HEADER);


-- 4. State weekly median per item (for the state map) --------------------------------------
COPY (
    SELECT item_code, state, region, week_start,
           round(median(price), 2)      AS median_price,
           COUNT(*)                     AS n_obs,
           COUNT(DISTINCT premise_code) AS n_shops
    FROM usable
    GROUP BY ALL
    HAVING COUNT(DISTINCT premise_code) >= 3
    ORDER BY item_code, state, week_start
) TO 'data/marts/item_state_week.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);


-- 5. District weekly median per item (the main table: "where is it cheapest?") ----------
COPY (
    SELECT item_code, state, district, region, week_start,
           round(median(price), 2)      AS median_price,
           COUNT(*)                     AS n_obs,
           COUNT(DISTINCT premise_code) AS n_shops
    FROM usable
    GROUP BY ALL
    HAVING COUNT(DISTINCT premise_code) >= 3
    ORDER BY item_code, state, district, week_start
) TO 'data/marts/item_district_week.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);


-- 6. Store-type monthly median per item and district (for the store-type premium) -------
-- Like-for-like comparison happens later: same item, same district, same month, different type.
COPY (
    SELECT item_code, premise_type, state, district, region, month,
           round(median(price), 2)      AS median_price,
           COUNT(*)                     AS n_obs,
           COUNT(DISTINCT premise_code) AS n_shops
    FROM usable
    GROUP BY ALL
    HAVING COUNT(DISTINCT premise_code) >= 3
    ORDER BY item_code, state, district, month, premise_type
) TO 'data/marts/item_premisetype_district_month.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
