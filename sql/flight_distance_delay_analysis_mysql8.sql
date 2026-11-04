CREATE DATABASE IF NOT EXISTS flight_delay_analytics
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE flight_delay_analytics;

-- Uses the flights table from flight_delay_analysis_mysql8.sql:
-- airline_code, departure_airport_code, arrival_airport_code,
-- departure_actual, dep_delay_minutes, arr_delay_minutes, distance_miles.
-- Load enriched data first; the current project CSVs do not include delays,
-- airline codes, or distances.

-- 1-3. One row per destination, flight count, number of distinct distances,
-- mean distance (for harmonization when routes to the same destination differ),
-- and mean departure/arrival delays.
CREATE OR REPLACE VIEW destination_delay_distance AS
SELECT
    arrival_airport_code AS destination,
    COUNT(*) AS flight_count,
    COUNT(DISTINCT distance_miles) AS distinct_distance_count,
    AVG(distance_miles) AS mean_distance_miles,
    MIN(distance_miles) AS min_distance_miles,
    MAX(distance_miles) AS max_distance_miles,
    AVG(arr_delay_minutes) AS mean_arr_delay_minutes,
    AVG(dep_delay_minutes) AS mean_dep_delay_minutes,
    SUM(arr_delay_minutes > 15) AS arrivals_over_15_minutes_late,
    100.0 * SUM(arr_delay_minutes > 15) / COUNT(*)
        AS arrival_delay_over_15_percent
FROM flights
GROUP BY arrival_airport_code;

SELECT *
FROM destination_delay_distance
ORDER BY destination;

-- Pearson correlation between destination mean distance and mean arrival delay,
-- excluding HNL as requested. This returns the grouped values; calculate Pearson
-- r in the visualization/analysis client or with a MySQL statistical extension.
SELECT
    destination,
    flight_count,
    distinct_distance_count,
    mean_distance_miles,
    mean_arr_delay_minutes
FROM destination_delay_distance
WHERE destination <> 'HNL'
ORDER BY mean_distance_miles;

-- 4. Identify long/medium/short destination bands using explicit, adjustable
-- thresholds: short < 1000, medium 1000-2999, long >= 3000 statute miles.
SELECT
    CASE
        WHEN mean_distance_miles < 1000 THEN 'Short (<1000 miles)'
        WHEN mean_distance_miles < 3000 THEN 'Medium (1000-2999 miles)'
        ELSE 'Long (>=3000 miles)'
    END AS distance_band,
    COUNT(*) AS destination_count,
    SUM(flight_count) AS flight_count,
    AVG(mean_arr_delay_minutes) AS mean_arrival_delay_minutes
FROM destination_delay_distance
WHERE destination <> 'HNL'
GROUP BY distance_band
ORDER BY MIN(mean_distance_miles);

-- Check whether HNL exists and how far it is from the next farthest destination.
SELECT destination, flight_count, mean_distance_miles
FROM destination_delay_distance
ORDER BY mean_distance_miles DESC;

SELECT
    hnl.mean_distance_miles AS hnl_mean_distance_miles,
    second_far.mean_distance_miles AS second_farthest_mean_distance_miles,
    hnl.mean_distance_miles / NULLIF(second_far.mean_distance_miles, 0)
        AS hnl_to_second_farthest_ratio
FROM destination_delay_distance AS hnl
JOIN (
    SELECT mean_distance_miles
    FROM destination_delay_distance
    WHERE destination <> 'HNL'
    ORDER BY mean_distance_miles DESC
    LIMIT 1
) AS second_far
WHERE hnl.destination = 'HNL';

-- 5. Destinations with highest average arrival delay.
SELECT
    destination,
    flight_count,
    mean_arr_delay_minutes,
    arrivals_over_15_minutes_late,
    arrival_delay_over_15_percent
FROM destination_delay_distance
ORDER BY mean_arr_delay_minutes DESC, flight_count DESC;

-- Airline/destination pairs most affected, ranked by mean arrival delay.
SELECT
    airline_code,
    arrival_airport_code AS destination,
    COUNT(*) AS flight_count,
    AVG(arr_delay_minutes) AS mean_arr_delay_minutes,
    SUM(arr_delay_minutes > 15) AS arrivals_over_15_minutes_late,
    100.0 * SUM(arr_delay_minutes > 15) / COUNT(*)
        AS arrival_delay_over_15_percent
FROM flights
GROUP BY airline_code, arrival_airport_code
ORDER BY mean_arr_delay_minutes DESC, flight_count DESC;

-- 6. Descriptive statistics for arrival and departure delays.
SELECT 'arr_delay_minutes' AS variable,
       COUNT(*) AS flight_count,
       AVG(arr_delay_minutes) AS mean_minutes,
       MIN(arr_delay_minutes) AS min_minutes,
       MAX(arr_delay_minutes) AS max_minutes,
       STDDEV_SAMP(arr_delay_minutes) AS sample_std_dev_minutes
FROM flights
UNION ALL
SELECT 'dep_delay_minutes',
       COUNT(*),
       AVG(dep_delay_minutes),
       MIN(dep_delay_minutes),
       MAX(dep_delay_minutes),
       STDDEV_SAMP(dep_delay_minutes)
FROM flights;

-- Median, first quartile, and third quartile (MySQL 8 window functions).
WITH delay_values AS (
    SELECT 'arr_delay_minutes' AS variable, arr_delay_minutes AS delay_minutes
    FROM flights
    UNION ALL
    SELECT 'dep_delay_minutes', dep_delay_minutes
    FROM flights
)
SELECT DISTINCT
    variable,
    COUNT(*) OVER (PARTITION BY variable) AS flight_count,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY delay_minutes)
        OVER (PARTITION BY variable) AS q1_minutes,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY delay_minutes)
        OVER (PARTITION BY variable) AS median_minutes,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY delay_minutes)
        OVER (PARTITION BY variable) AS q3_minutes
FROM delay_values;

-- 7. Departure airport with the lowest average arrival delay.
SELECT
    departure_airport_code AS departure_airport,
    COUNT(*) AS flight_count,
    AVG(arr_delay_minutes) AS mean_arr_delay_minutes
FROM flights
GROUP BY departure_airport_code
ORDER BY mean_arr_delay_minutes ASC
LIMIT 1;

-- 8. Mean arrival delay by departure hour.
SELECT
    HOUR(departure_actual) AS departure_hour,
    COUNT(*) AS flight_count,
    AVG(arr_delay_minutes) AS mean_arr_delay_minutes,
    AVG(dep_delay_minutes) AS mean_dep_delay_minutes
FROM flights
WHERE departure_actual IS NOT NULL
GROUP BY HOUR(departure_actual)
ORDER BY departure_hour;

-- Flight-level points for a scatter plot of departure hour vs arrival delay.
SELECT
    flight_id,
    airline_code,
    departure_airport_code,
    arrival_airport_code,
    HOUR(departure_actual) AS departure_hour,
    arr_delay_minutes
FROM flights
WHERE departure_actual IS NOT NULL
ORDER BY departure_hour, flight_id;
