-- 01_clean.sql
-- Turns the raw PriceCatcher files into clean, analysis-ready tables in data/staging/.
-- Run it with:  .\.venv\Scripts\python.exe src\build.py
-- (paths are relative to the project folder; build.py runs from there)
--
-- Outputs
--   data/staging/dim_item.parquet      one row per item, tidy text
--   data/staging/dim_premise.parquet   one row per shop, tidy text + region
--   data/staging/prices_clean.parquet  one row per price, joined to item and shop, with outlier flags


-- 1. Items -----------------------------------------------------------------------------
-- Drop the placeholder row (item_code -1, no name) and trim stray spaces from every text column.
CREATE OR REPLACE TABLE dim_item AS
SELECT
    item_code,
    trim(item)          AS item,
    trim(unit)          AS unit,
    trim(item_group)    AS item_group,
    trim(item_category) AS item_category
FROM read_parquet('data/raw/lookup_item.parquet')
WHERE item_code > 0
  AND item IS NOT NULL;


-- 2. Shops (premises) ------------------------------------------------------------------
-- Drop the placeholder row (premise_code -1, "Unknown Premise", no state).
-- trim() fixes "Pasar Basah " (with a trailing space) so it groups with "Pasar Basah".
-- region splits Peninsular Malaysia from East Malaysia (Sabah, Sarawak, Labuan) for Phase 5.
CREATE OR REPLACE TABLE dim_premise AS
SELECT
    premise_code,
    trim(premise)      AS premise,
    trim(address)      AS address,
    trim(premise_type) AS premise_type,
    trim(state)        AS state,
    trim(district)     AS district,
    CASE WHEN trim(state) IN ('Sabah', 'Sarawak', 'W.P. Labuan')
         THEN 'East Malaysia' ELSE 'Peninsular Malaysia' END AS region
FROM read_parquet('data/raw/lookup_premise.parquet')
WHERE premise_code > 0
  AND state IS NOT NULL;


-- 3. Monthly price statistics per item --------------------------------------------------
-- For each item in each month: the median and the middle-50% range (Q1 to Q3).
-- These are used to decide whether a single price looks wrong.
CREATE OR REPLACE TABLE item_month_stats AS
SELECT
    item_code,
    date_trunc('month', date)    AS month,
    quantile_cont(price, 0.25)   AS q1,
    median(price)                AS median_price,
    quantile_cont(price, 0.75)   AS q3,
    COUNT(*)                     AS n_obs
FROM read_parquet('data/raw/pricecatcher_*.parquet')
GROUP BY ALL;


-- 4. Clean price table -------------------------------------------------------------------
-- Outlier rule (flag, never delete):
--   spread  = the larger of (Q3 - Q1) and 10% of the median
--   outlier = price below median - 3*spread, or above median + 3*spread
-- Why the 10% floor: items with a controlled price (e.g. eggs) often have Q1 = Q3, so the plain
-- IQR is zero and even a 10-sen difference would be flagged. The floor stops that.
-- price_to_median helps spot typos: ~100 means a missing decimal point (RM 8245 instead of 82.45).
--
-- Rows whose item_code is not in the item lookup (~1.9%) are KEPT with item_known = false,
-- because we can't name those items but shouldn't pretend they don't exist.
COPY (
    SELECT
        f.date,
        date_trunc('week', f.date)  AS week_start,   -- weeks start on Monday
        date_trunc('month', f.date) AS month,
        f.premise_code,
        p.premise_type,
        p.state,
        p.district,
        p.region,
        f.item_code,
        i.item,
        i.unit,
        i.item_group,
        i.item_category,
        f.price,
        s.median_price                       AS item_month_median,
        round(f.price / s.median_price, 3)   AS price_to_median,
        (i.item_code IS NOT NULL)            AS item_known,
        (f.price < s.median_price - 3 * greatest(s.q3 - s.q1, 0.10 * s.median_price)
         OR f.price > s.median_price + 3 * greatest(s.q3 - s.q1, 0.10 * s.median_price))
                                             AS is_outlier
    FROM read_parquet('data/raw/pricecatcher_*.parquet') AS f
    JOIN dim_premise AS p
        ON f.premise_code = p.premise_code                 -- drops placeholder / unknown shops
    LEFT JOIN dim_item AS i
        ON f.item_code = i.item_code                       -- keeps unknown items, flagged
    JOIN item_month_stats AS s
        ON f.item_code = s.item_code
       AND date_trunc('month', f.date) = s.month

) TO 'data/staging/prices_clean.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);


-- 5. Save the small dimension tables too ----------------------------------------------
COPY dim_item    TO 'data/staging/dim_item.parquet'    (FORMAT PARQUET);
COPY dim_premise TO 'data/staging/dim_premise.parquet' (FORMAT PARQUET);
