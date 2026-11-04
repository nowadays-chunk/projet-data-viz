CREATE DATABASE IF NOT EXISTS flight_custom_sort
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE flight_custom_sort;

CREATE TABLE IF NOT EXISTS flights (
    flight_id VARCHAR(40) NOT NULL,
    flight_date DATE NULL,
    dep_time SMALLINT UNSIGNED NULL,
    sched_dep_time SMALLINT UNSIGNED NULL,
    dep_delay DECIMAL(8, 2) NULL,
    arr_time SMALLINT UNSIGNED NULL,
    air_time DECIMAL(8, 2) NULL,
    origin CHAR(3) NULL,
    dest CHAR(3) NULL,
    PRIMARY KEY (flight_id),
    CONSTRAINT chk_dep_time_hhmm
        CHECK (
            dep_time IS NULL
            OR dep_time = 2400
            OR (
                dep_time BETWEEN 0 AND 2359
                AND MOD(dep_time, 100) < 60
            )
        ),
    CONSTRAINT chk_sched_dep_time_hhmm
        CHECK (
            sched_dep_time IS NULL
            OR sched_dep_time = 2400
            OR (
                sched_dep_time BETWEEN 0 AND 2359
                AND MOD(sched_dep_time, 100) < 60
            )
        ),
    CONSTRAINT chk_arr_time_hhmm
        CHECK (
            arr_time IS NULL
            OR arr_time = 2400
            OR (
                arr_time BETWEEN 0 AND 2359
                AND MOD(arr_time, 100) < 60
            )
        ),
    INDEX idx_custom_sort_dep_delay (dep_delay)
) ENGINE = InnoDB;

-- Import HHMM columns as integers; empty fields should be NULL.
-- LOAD DATA LOCAL INFILE 'C:\\path\\to\\flights.csv'
-- INTO TABLE flights
-- CHARACTER SET utf8mb4
-- FIELDS TERMINATED BY ','
-- OPTIONALLY ENCLOSED BY '"'
-- LINES TERMINATED BY '\r\n'
-- IGNORE 1 LINES
-- (flight_id, flight_date, @dep_time, @sched_dep_time, @dep_delay,
--  @arr_time, @air_time, @origin, @dest)
-- SET dep_time = NULLIF(@dep_time, ''),
--     sched_dep_time = NULLIF(@sched_dep_time, ''),
--     dep_delay = NULLIF(@dep_delay, ''),
--     arr_time = NULLIF(@arr_time, ''),
--     air_time = NULLIF(@air_time, ''),
--     origin = NULLIF(@origin, ''),
--     dest = NULLIF(@dest, '');

-- 1. Convert HHMM integers to minutes since midnight.
-- 2400 is normalized to 00:00. Values should otherwise be valid HHMM.
CREATE OR REPLACE VIEW flight_time_metrics AS
SELECT
    f.*,
    CASE
        WHEN dep_time IS NULL THEN NULL
        WHEN dep_time = 2400 THEN 0
        ELSE FLOOR(dep_time / 100) * 60 + MOD(dep_time, 100)
    END AS dep_time_minutes,
    CASE
        WHEN sched_dep_time IS NULL THEN NULL
        WHEN sched_dep_time = 2400 THEN 0
        ELSE FLOOR(sched_dep_time / 100) * 60 + MOD(sched_dep_time, 100)
    END AS sched_dep_time_minutes,
    CASE
        WHEN arr_time IS NULL THEN NULL
        WHEN arr_time = 2400 THEN 0
        ELSE FLOOR(arr_time / 100) * 60 + MOD(arr_time, 100)
    END AS arr_time_minutes
FROM flights AS f;

SELECT
    flight_id,
    dep_time,
    dep_time_minutes,
    sched_dep_time,
    sched_dep_time_minutes,
    dep_delay,
    CASE
        WHEN dep_time_minutes IS NULL OR sched_dep_time_minutes IS NULL THEN NULL
        ELSE MOD(
            dep_time_minutes - sched_dep_time_minutes + 720 + 1440,
            1440
        ) - 720
    END AS calculated_dep_delay_minutes,
    dep_delay - CASE
        WHEN dep_time_minutes IS NULL OR sched_dep_time_minutes IS NULL THEN NULL
        ELSE MOD(
            dep_time_minutes - sched_dep_time_minutes + 720 + 1440,
            1440
        ) - 720
    END AS reported_minus_calculated_delay_minutes
FROM flight_time_metrics;

-- 2. min_rank(descending dep_delay): ties share their minimum rank. Filtering
-- rank <= 10 may return more than 10 flights when there is a tie at the cutoff.
WITH ranked_flights AS (
    SELECT
        flight_id,
        dep_time,
        sched_dep_time,
        dep_delay,
        RANK() OVER (ORDER BY dep_delay DESC) AS delay_rank
    FROM flights
    WHERE dep_delay IS NOT NULL
)
SELECT *
FROM ranked_flights
WHERE delay_rank <= 10
ORDER BY delay_rank, flight_id;

-- Alternative: exactly 10 rows, deterministically breaking ties by flight_id.
-- Use this only when exactly ten results are required.
SELECT
    flight_id,
    dep_time,
    sched_dep_time,
    dep_delay,
    ROW_NUMBER() OVER (ORDER BY dep_delay DESC, flight_id) AS row_number_rank
FROM flights
WHERE dep_delay IS NOT NULL
ORDER BY row_number_rank
LIMIT 10;

-- 3. Compare air_time with the difference of the two clock times.
-- The modulo corrects midnight rollover, but this remains a clock-time
-- comparison: if airports are in different time zones, it is not elapsed time.
SELECT
    flight_id,
    dep_time_minutes,
    arr_time_minutes,
    MOD(arr_time_minutes - dep_time_minutes + 1440, 1440)
        AS clock_elapsed_minutes_mod_24h,
    air_time,
    MOD(arr_time_minutes - dep_time_minutes + 1440, 1440) - air_time
        AS clock_elapsed_minus_air_time_minutes
FROM flight_time_metrics
WHERE dep_time_minutes IS NOT NULL
  AND arr_time_minutes IS NOT NULL
  AND air_time IS NOT NULL;

-- To compare true elapsed time, store departure/arrival instants in UTC.
-- Local dep_time/arr_time clocks alone cannot correct timezone differences or DST.
-- Even corrected elapsed gate-to-gate time exceeds air_time because air_time
-- excludes taxi-out and taxi-in.
