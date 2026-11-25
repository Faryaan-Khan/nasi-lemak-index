-- 04_insights.sql
-- Small result tables that answer the four Phase 5 questions. They are rebuilt every night, so the
-- numbers in docs/insights.md can be re-checked against fresh data at any time.
-- Run with:  .\.venv\Scripts\python.exe src\build.py   (after 01-03)
--
-- Outputs (data/marts/, all committed, all small)
--   insight_basket_state_quarter.csv     basket cost per state, last 13 complete weeks
--   insight_basket_district_quarter.csv  basket cost per district, last 13 complete weeks
--   insight_festive_rise.csv             pre-festival rise per item and festival, with a placebo check
--   insight_storetype_premium.csv        store-type premium vs supermarkets, like-for-like
--   insight_east_west_item.csv           East Malaysia vs Peninsular price per item, last 13 weeks


-- "Last quarter" = the 13 most recent COMPLETE weeks (the current week is still being collected).
CREATE OR REPLACE TEMP TABLE quarter AS
SELECT CAST(MAX(week_start) - INTERVAL 13 WEEK AS DATE) AS first_week,
       CAST(MAX(week_start) - INTERVAL 1 WEEK  AS DATE) AS last_week
FROM 'data/marts/item_national_week.csv';

CREATE OR REPLACE TEMP TABLE baskets AS
SELECT basket, item_code, quantity FROM read_csv('data/reference/baskets.csv', header = true);

CREATE OR REPLACE TEMP TABLE basket_size AS
SELECT basket, COUNT(*) AS items_in_basket FROM baskets GROUP BY 1;


-- 1. Where is each basket cheapest? ---------------------------------------------------------
-- For each item and place: the median of its weekly medians over the quarter (needs >= 4 weeks).
-- Basket cost = sum of (item price x quantity), only when every basket item is priced there.
-- Quarterly item medians are steadier than single weeks, and let places with patchy weeks count.

COPY (
    WITH item_q AS (
        SELECT s.item_code, s.state, s.region, median(s.median_price) AS price
        FROM 'data/marts/item_state_week.parquet' AS s, quarter AS q
        WHERE s.week_start BETWEEN q.first_week AND q.last_week
        GROUP BY ALL
        HAVING COUNT(*) >= 4
    ),
    costs AS (
        SELECT b.basket, i.state, i.region,
               round(SUM(CAST(i.price * b.quantity AS DECIMAL(12, 4))), 2) AS basket_cost
        FROM item_q AS i JOIN baskets AS b USING (item_code)
        GROUP BY ALL
        HAVING COUNT(*) = (SELECT items_in_basket FROM basket_size z WHERE z.basket = b.basket)
    )
    SELECT basket, state, region, basket_cost,
           rank() OVER (PARTITION BY basket ORDER BY basket_cost) AS rank_cheapest,
           round(basket_cost - MIN(basket_cost) OVER (PARTITION BY basket), 2) AS rm_above_cheapest,
           (SELECT first_week FROM quarter) AS first_week,
           (SELECT last_week FROM quarter)  AS last_week
    FROM costs
    ORDER BY basket, basket_cost
) TO 'data/marts/insight_basket_state_quarter.csv' (HEADER);

COPY (
    WITH item_q AS (
        SELECT d.item_code, d.state, d.district, d.region, median(d.median_price) AS price
        FROM 'data/marts/item_district_week.parquet' AS d, quarter AS q
        WHERE d.week_start BETWEEN q.first_week AND q.last_week
        GROUP BY ALL
        HAVING COUNT(*) >= 4
    ),
    costs AS (
        SELECT b.basket, i.state, i.district, i.region,
               round(SUM(CAST(i.price * b.quantity AS DECIMAL(12, 4))), 2) AS basket_cost
        FROM item_q AS i JOIN baskets AS b USING (item_code)
        GROUP BY ALL
        HAVING COUNT(*) = (SELECT items_in_basket FROM basket_size z WHERE z.basket = b.basket)
    )
    SELECT basket, state, district, region, basket_cost,
           rank() OVER (PARTITION BY basket ORDER BY basket_cost, state, district) AS rank_cheapest,
           round(basket_cost - MIN(basket_cost) OVER (PARTITION BY basket), 2) AS rm_above_cheapest
    FROM costs
    ORDER BY basket, basket_cost, state, district
) TO 'data/marts/insight_basket_district_quarter.csv' (HEADER);


-- 2. Which items rise before each festival? -------------------------------------------------
-- For every festival-year and item (national weekly medians):
--   baseline = median of weeks -12 to -9 (before festive buying)   [needs >= 3 of 4 weeks]
--   pre      = average of weeks -2 to 0 (the run-up)                [needs >= 2 of 3 weeks]
--   rise %   = pre / baseline - 1
--   peak     = the week (-8 to 0) with the highest price
-- Placebo check: the same calculation anchored 13 weeks AFTER each festival, when nothing is
-- being celebrated. An item whose "rise" is just as big in the placebo window is seasonal or
-- noisy, not festive. net_rise_pct = festive rise - placebo rise.
-- Only items seen in >= 3 festival years with >= 100 shops in every week are kept.

CREATE OR REPLACE TEMP TABLE anchors AS
SELECT festival, year, 'festival' AS kind,
       CAST(date_trunc('week', CAST(date AS DATE)) AS DATE) AS anchor_week
FROM read_csv('data/reference/festive_calendar.csv', header = true)
UNION ALL
SELECT festival, year, 'placebo' AS kind,
       CAST(date_trunc('week', CAST(date AS DATE)) AS DATE) + 91 AS anchor_week   -- 13 weeks later
FROM read_csv('data/reference/festive_calendar.csv', header = true);

CREATE OR REPLACE TEMP TABLE runup AS
SELECT a.festival, a.year, a.kind, n.item_code,
       median(n.median_price) FILTER (WHERE n.week_start BETWEEN a.anchor_week - 84 AND a.anchor_week - 63) AS baseline,
       COUNT(*)               FILTER (WHERE n.week_start BETWEEN a.anchor_week - 84 AND a.anchor_week - 63) AS baseline_weeks,
       AVG(n.median_price)    FILTER (WHERE n.week_start BETWEEN a.anchor_week - 14 AND a.anchor_week)      AS pre,
       COUNT(*)               FILTER (WHERE n.week_start BETWEEN a.anchor_week - 14 AND a.anchor_week)      AS pre_weeks,
       arg_max(CAST((n.week_start - a.anchor_week) / 7 AS INTEGER), n.median_price)
                              FILTER (WHERE n.week_start BETWEEN a.anchor_week - 56 AND a.anchor_week)      AS peak_week,
       MIN(n.n_shops)                                                                                       AS min_shops
FROM anchors AS a
JOIN 'data/marts/item_national_week.csv' AS n
  ON n.week_start BETWEEN a.anchor_week - 84 AND a.anchor_week
GROUP BY ALL
HAVING baseline_weeks >= 3 AND pre_weeks >= 2;

COPY (
    WITH fest AS (
        SELECT festival, item_code,
               COUNT(*)                                   AS years,
               AVG(100 * (pre / baseline - 1))            AS avg_rise_pct,
               SUM((pre / baseline - 1 >= 0.05)::INT)     AS years_up_5pct,
               median(peak_week)                          AS median_peak_week,
               MIN(min_shops)                             AS min_shops
        FROM runup WHERE kind = 'festival'
        GROUP BY ALL
    ),
    placebo AS (
        SELECT festival, item_code, AVG(100 * (pre / baseline - 1)) AS placebo_rise_pct
        FROM runup WHERE kind = 'placebo'
        GROUP BY ALL
    )
    SELECT f.festival, f.item_code, i.item, i.unit, i.item_group, f.years,
           round(f.avg_rise_pct, 1)                       AS avg_rise_pct,
           round(p.placebo_rise_pct, 1)                   AS placebo_rise_pct,
           round(f.avg_rise_pct - p.placebo_rise_pct, 1)  AS net_rise_pct,
           f.median_peak_week, f.years_up_5pct, f.min_shops
    FROM fest AS f
    JOIN placebo AS p USING (festival, item_code)
    JOIN read_csv('data/marts/dim_item.csv', header = true) AS i USING (item_code)
    WHERE f.years >= 3 AND f.min_shops >= 100
    ORDER BY f.festival, f.avg_rise_pct DESC, f.item_code
) TO 'data/marts/insight_festive_rise.csv' (HEADER);


-- 3. Store-type premium, like-for-like -----------------------------------------------------
-- Compare each store type with supermarkets (the most common type) for the SAME item, in the
-- SAME district, in the SAME month, over the last 12 months. Each such match is a "pair".
-- premium % = typical ratio across pairs (geometric median: exp of the median log-ratio).
-- Limitation: same item code doesn't guarantee same freshness or quality.

COPY (
    WITH m AS (
        SELECT * FROM 'data/marts/item_premisetype_district_month.parquet'
        WHERE month > (SELECT MAX(month) FROM 'data/marts/item_premisetype_district_month.parquet') - INTERVAL 12 MONTH
    ),
    pairs AS (
        SELECT a.premise_type, a.item_code, a.state, a.district, a.month,
               a.median_price AS price, s.median_price AS supermarket_price
        FROM m AS a
        JOIN m AS s
          ON a.item_code = s.item_code AND a.state = s.state AND a.district = s.district AND a.month = s.month
         AND s.premise_type = 'Pasar Raya / Supermarket'
        WHERE a.premise_type <> 'Pasar Raya / Supermarket'
    ),
    labelled AS (
        SELECT p.*, 'All items' AS item_group FROM pairs AS p
        UNION ALL
        SELECT p.*, i.item_group FROM pairs AS p
        JOIN read_csv('data/marts/dim_item.csv', header = true) AS i USING (item_code)
    )
    SELECT item_group, premise_type,
           COUNT(*)                                                        AS pairs,
           COUNT(DISTINCT item_code)                                       AS items,
           COUNT(DISTINCT state || '|' || district)                        AS districts,
           round(100 * (exp(median(ln(price / supermarket_price))) - 1), 1) AS median_premium_pct,
           round(100 * AVG((price > supermarket_price)::INT), 0)           AS pct_pairs_dearer,
           MIN(month) AS first_month, MAX(month) AS last_month
    FROM labelled
    GROUP BY item_group, premise_type
    HAVING COUNT(*) >= 200
    ORDER BY item_group = 'All items' DESC, item_group, median_premium_pct
) TO 'data/marts/insight_storetype_premium.csv' (HEADER);


-- 4. Is East Malaysia more expensive? ----------------------------------------------------------
-- For each item: the median across states of each state's quarterly median, separately for
-- East Malaysia (Sabah, Sarawak, Labuan) and Peninsular Malaysia. Only items sold in at least
-- 2 East states and 8 Peninsular states are compared, so the comparison is like-for-like.

COPY (
    WITH item_q AS (
        SELECT s.item_code, s.state, s.region, median(s.median_price) AS price
        FROM 'data/marts/item_state_week.parquet' AS s, quarter AS q
        WHERE s.week_start BETWEEN q.first_week AND q.last_week
        GROUP BY ALL
        HAVING COUNT(*) >= 4
    ),
    ew AS (
        SELECT item_code,
               median(price) FILTER (WHERE region = 'Peninsular Malaysia') AS peninsular_price,
               median(price) FILTER (WHERE region = 'East Malaysia')       AS east_price,
               COUNT(*) FILTER (WHERE region = 'Peninsular Malaysia')      AS peninsular_states,
               COUNT(*) FILTER (WHERE region = 'East Malaysia')            AS east_states
        FROM item_q
        GROUP BY 1
        HAVING east_states >= 2 AND peninsular_states >= 8
    )
    SELECT e.item_code, i.item, i.unit, i.item_group,
           round(e.peninsular_price, 2) AS peninsular_price,
           round(e.east_price, 2)       AS east_price,
           round(100 * (e.east_price / e.peninsular_price - 1), 1) AS east_gap_pct,
           e.peninsular_states, e.east_states
    FROM ew AS e
    JOIN read_csv('data/marts/dim_item.csv', header = true) AS i USING (item_code)
    ORDER BY east_gap_pct DESC, e.item_code
) TO 'data/marts/insight_east_west_item.csv' (HEADER);
