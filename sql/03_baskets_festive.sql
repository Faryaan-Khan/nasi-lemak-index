-- 03_baskets_festive.sql
-- Basket costs and festive price windows, built from the marts made by 02_marts.sql and the
-- reference files in data/reference/.
-- Run with:  .\.venv\Scripts\python.exe src\build.py
--
-- Outputs (data/marts/)
--   basket_cost_national_week.csv      basket x week, all Malaysia                (committed)
--   basket_cost_state_week.csv         basket x state x week                      (committed)
--   basket_cost_district_week.parquet  basket x district x week                   (GitHub release)
--   festive_window.csv                 festival x item x week -12..+2, price index (committed)


CREATE OR REPLACE TEMP TABLE baskets AS
SELECT basket, item_code, quantity
FROM read_csv('data/reference/baskets.csv', header = true);

CREATE OR REPLACE TEMP TABLE basket_size AS
SELECT basket, COUNT(*) AS items_in_basket FROM baskets GROUP BY 1;


-- 1. Basket cost ---------------------------------------------------------------------------
-- cost = sum over the basket's items of (median price x quantity).
-- The sum uses exact DECIMAL arithmetic: adding floating-point numbers in a different order
-- (DuckDB works in parallel) can change the last cent, which would cause noisy daily commits.
-- A basket cost is only reported when EVERY item in the basket has a price in that place and
-- week (each backed by >= 3 shops, as in 02_marts.sql). A partial basket would look cheaper than
-- it really is, so incomplete ones are dropped rather than shown.

COPY (
    SELECT b.basket, n.week_start,
           round(SUM(CAST(n.median_price * b.quantity AS DECIMAL(12, 4))), 2) AS basket_cost,
           COUNT(*)                                   AS items_priced,
           MIN(n.n_shops)                             AS min_shops_per_item
    FROM 'data/marts/item_national_week.csv' AS n
    JOIN baskets AS b USING (item_code)
    GROUP BY ALL
    HAVING COUNT(*) = (SELECT items_in_basket FROM basket_size s WHERE s.basket = b.basket)
    ORDER BY b.basket, n.week_start
) TO 'data/marts/basket_cost_national_week.csv' (HEADER);

COPY (
    SELECT b.basket, s.state, s.region, s.week_start,
           round(SUM(CAST(s.median_price * b.quantity AS DECIMAL(12, 4))), 2) AS basket_cost,
           COUNT(*)                                   AS items_priced,
           MIN(s.n_shops)                             AS min_shops_per_item
    FROM 'data/marts/item_state_week.parquet' AS s
    JOIN baskets AS b USING (item_code)
    GROUP BY ALL
    HAVING COUNT(*) = (SELECT items_in_basket FROM basket_size z WHERE z.basket = b.basket)
    ORDER BY b.basket, s.state, s.week_start
) TO 'data/marts/basket_cost_state_week.csv' (HEADER);

COPY (
    SELECT b.basket, d.state, d.district, d.region, d.week_start,
           round(SUM(CAST(d.median_price * b.quantity AS DECIMAL(12, 4))), 2) AS basket_cost,
           COUNT(*)                                   AS items_priced,
           MIN(d.n_shops)                             AS min_shops_per_item
    FROM 'data/marts/item_district_week.parquet' AS d
    JOIN baskets AS b USING (item_code)
    GROUP BY ALL
    HAVING COUNT(*) = (SELECT items_in_basket FROM basket_size z WHERE z.basket = b.basket)
    ORDER BY b.basket, d.state, d.district, d.week_start
) TO 'data/marts/basket_cost_district_week.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);


-- 2. Festive window ------------------------------------------------------------------------
-- For each festival and item: the national weekly median from 12 weeks before to 2 weeks after,
-- as an index where the item's own baseline = 100.
--   week_offset 0  = the Monday-starting week that contains the festival day
--   baseline       = median of the weekly medians in weeks -12 to -9 (well before festive buying)
-- An item-festival is only included when at least 3 of the 4 baseline weeks have a price,
-- otherwise the baseline itself would be unreliable.

CREATE OR REPLACE TEMP TABLE festivals AS
SELECT festival, year, CAST(date AS DATE) AS festival_date,
       CAST(date_trunc('week', CAST(date AS DATE)) AS DATE) AS festival_week
FROM read_csv('data/reference/festive_calendar.csv', header = true)
-- only festivals that have already happened (future ones would show a half-empty window)
WHERE CAST(date AS DATE) <= (SELECT MAX(week_start) FROM 'data/marts/item_national_week.csv');

CREATE OR REPLACE TEMP TABLE windowed AS
SELECT f.festival, f.year, f.festival_date,
       n.item_code, n.week_start,
       CAST((n.week_start - f.festival_week) / 7 AS INTEGER) AS week_offset,
       n.median_price, n.n_shops
FROM festivals AS f
JOIN 'data/marts/item_national_week.csv' AS n
  ON n.week_start BETWEEN f.festival_week - INTERVAL 12 WEEK AND f.festival_week + INTERVAL 2 WEEK;

CREATE OR REPLACE TEMP TABLE baselines AS
SELECT festival, year, item_code,
       median(median_price) AS baseline_price,
       COUNT(*)             AS baseline_weeks
FROM windowed
WHERE week_offset BETWEEN -12 AND -9
GROUP BY ALL
HAVING COUNT(*) >= 3;

COPY (
    SELECT w.festival, w.year, w.festival_date, w.item_code, w.week_offset, w.week_start,
           w.median_price,
           round(b.baseline_price, 2)                       AS baseline_price,
           round(100 * w.median_price / b.baseline_price, 1) AS price_index,
           w.n_shops
    FROM windowed AS w
    JOIN baselines AS b USING (festival, year, item_code)
    ORDER BY w.year, w.festival, w.item_code, w.week_offset
) TO 'data/marts/festive_window.csv' (HEADER);
