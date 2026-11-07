-- Unified MySQL 8 schema and analyses for this project.
-- Run this file with the mysql CLI (source airport_analytics_mysql8.sql).
-- Existing flight rows are preserved. No tables or databases are dropped.

CREATE DATABASE IF NOT EXISTS       
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE airport_analytics;

-- Each entity is defined once. The existing airport_analytics database already
-- has airports and flights; CREATE IF NOT EXISTS preserves those existing rows.
CREATE TABLE IF NOT EXISTS airports (
    airport_code CHAR(3) NOT NULL,
    airport_name VARCHAR(120) NULL,
    city VARCHAR(80) NULL,
    country VARCHAR(80) NULL,
    latitude DECIMAL(9, 6) NULL,
    longitude DECIMAL(9, 6) NULL,
    PRIMARY KEY (airport_code),
    CONSTRAINT chk_airports_latitude
        CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_airports_longitude
        CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS airlines (
    airline_code VARCHAR(8) NOT NULL,
    airline_name VARCHAR(100) NULL,
    PRIMARY KEY (airline_code)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS flights (
    flight_id VARCHAR(40) NOT NULL,
    airport_code CHAR(3) NULL,
    aircraft_id VARCHAR(20) NULL,
    departure_airport_code CHAR(3) NULL,
    arrival_airport_code CHAR(3) NULL,
    departure_datetime DATETIME NULL,
    arrival_datetime DATETIME NULL,
    duration_hours DECIMAL(6, 2) NULL,
    flight_date DATE NULL,
    airline_code VARCHAR(8) NULL,
    departure_scheduled DATETIME NULL,
    arrival_scheduled DATETIME NULL,
    dep_time SMALLINT UNSIGNED NULL,
    sched_dep_time SMALLINT UNSIGNED NULL,
    arr_time SMALLINT UNSIGNED NULL,
    dep_delay_minutes DECIMAL(8, 2) NULL,
    arr_delay_minutes DECIMAL(8, 2) NULL,
    air_time_minutes DECIMAL(8, 2) NULL,
    distance_miles DECIMAL(10, 2) NULL,
    source_file VARCHAR(100) NULL,
    PRIMARY KEY (flight_id),
    CONSTRAINT fk_flights_source_airport
        FOREIGN KEY (airport_code) REFERENCES airports (airport_code),
    CONSTRAINT fk_flights_departure_airport
        FOREIGN KEY (departure_airport_code) REFERENCES airports (airport_code),
    CONSTRAINT fk_flights_arrival_airport
        FOREIGN KEY (arrival_airport_code) REFERENCES airports (airport_code),
    CONSTRAINT chk_flights_air_time
        CHECK (air_time_minutes IS NULL OR air_time_minutes > 0),
    CONSTRAINT chk_flights_distance
        CHECK (distance_miles IS NULL OR distance_miles >= 0),
    INDEX idx_flights_departure_datetime (departure_datetime),
    INDEX idx_flights_source_departure (airport_code, departure_datetime),
    INDEX idx_flights_route (departure_airport_code, arrival_airport_code),
    INDEX idx_flights_airline_destination (airline_code, arrival_airport_code)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS date_filters (
    filter_code VARCHAR(40) NOT NULL,
    filter_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (filter_code)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS special_calendar_days (
    month_number TINYINT UNSIGNED NOT NULL,
    day_number TINYINT UNSIGNED NOT NULL,
    day_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (month_number, day_number),
    CONSTRAINT chk_special_day_month CHECK (month_number BETWEEN 1 AND 12),
    CONSTRAINT chk_special_day_day CHECK (day_number BETWEEN 1 AND 31)
) ENGINE = InnoDB;

-- Upgrade the already-populated airport_analytics tables without dropping data.
-- This helper adds a column only when absent, so the file is safe to rerun.
DROP PROCEDURE IF EXISTS ensure_column;
DELIMITER $$
CREATE PROCEDURE ensure_column(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table_name
          AND COLUMN_NAME = p_column_name
    ) THEN
        SET @ddl = CONCAT(
            'ALTER TABLE `',
            REPLACE(p_table_name, '`', '``'),
            '` ADD COLUMN `',
            REPLACE(p_column_name, '`', '``'),
            '` ',
            p_column_definition
        );
        PREPARE add_column_statement FROM @ddl;
        EXECUTE add_column_statement;
        DEALLOCATE PREPARE add_column_statement;
    END IF;
END$$
DELIMITER ;

CALL ensure_column('airports', 'city', 'VARCHAR(80) NULL');
CALL ensure_column('airports', 'country', 'VARCHAR(80) NULL');
CALL ensure_column('airports', 'latitude', 'DECIMAL(9, 6) NULL');
CALL ensure_column('airports', 'longitude', 'DECIMAL(9, 6) NULL');
CALL ensure_column('flights', 'flight_date', 'DATE NULL');
CALL ensure_column('flights', 'airline_code', 'VARCHAR(8) NULL');
CALL ensure_column('flights', 'departure_scheduled', 'DATETIME NULL');
CALL ensure_column('flights', 'arrival_scheduled', 'DATETIME NULL');
CALL ensure_column('flights', 'dep_time', 'SMALLINT UNSIGNED NULL');
CALL ensure_column('flights', 'sched_dep_time', 'SMALLINT UNSIGNED NULL');
CALL ensure_column('flights', 'arr_time', 'SMALLINT UNSIGNED NULL');
CALL ensure_column('flights', 'dep_delay_minutes', 'DECIMAL(8, 2) NULL');
CALL ensure_column('flights', 'arr_delay_minutes', 'DECIMAL(8, 2) NULL');
CALL ensure_column('flights', 'air_time_minutes', 'DECIMAL(8, 2) NULL');
CALL ensure_column('flights', 'distance_miles', 'DECIMAL(10, 2) NULL');
CALL ensure_column('flights', 'source_file', 'VARCHAR(100) NULL');
DROP PROCEDURE ensure_column;

-- Allow rows with missing actual times and optional flight metadata.
ALTER TABLE airports
    MODIFY COLUMN airport_name VARCHAR(120) NULL;
ALTER TABLE flights
    MODIFY COLUMN airport_code CHAR(3) NULL,
    MODIFY COLUMN aircraft_id VARCHAR(20) NULL,
    MODIFY COLUMN departure_airport_code CHAR(3) NULL,
    MODIFY COLUMN arrival_airport_code CHAR(3) NULL,
    MODIFY COLUMN departure_datetime DATETIME NULL,
    MODIFY COLUMN arrival_datetime DATETIME NULL,
    MODIFY COLUMN duration_hours DECIMAL(6, 2) NULL;

-- Coordinates for airports used by the generated flight data. Airport names
-- and coordinates are refreshed on rerun; flight rows are not changed here.
INSERT INTO airports
    (airport_code, airport_name, city, country, latitude, longitude)
VALUES
    ('CDG', 'Charles de Gaulle Airport', 'Paris', 'France', 49.009700, 2.547900),
    ('DXB', 'Dubai International Airport', 'Dubai', 'United Arab Emirates', 25.253200, 55.365700),
    ('JFK', 'John F. Kennedy International Airport', 'New York', 'United States', 40.641300, -73.778100),
    ('LHR', 'Heathrow Airport', 'London', 'United Kingdom', 51.470000, -0.454300),
    ('SIN', 'Changi Airport', 'Singapore', 'Singapore', 1.364400, 103.991500),
    ('MAD', 'Adolfo Suarez Madrid-Barajas Airport', 'Madrid', 'Spain', 40.498300, -3.567600),
    ('MIA', 'Miami International Airport', 'Miami', 'United States', 25.795900, -80.287000),
    ('BKK', 'Suvarnabhumi Airport', 'Bangkok', 'Thailand', 13.690000, 100.750100),
    ('AMS', 'Amsterdam Airport Schiphol', 'Amsterdam', 'Netherlands', 52.310500, 4.768300)
ON DUPLICATE KEY UPDATE
    airport_name = VALUES(airport_name),
    city = VALUES(city),
    country = VALUES(country),
    latitude = VALUES(latitude),
    longitude = VALUES(longitude);

INSERT INTO date_filters (filter_code, filter_name)
VALUES
    ('JANUARY_1', 'January 1'),
    ('NOVEMBER_DECEMBER', 'November or December'),
    ('SPECIAL_DAYS', 'Special days'),
    ('SUMMER', 'Summer (July to September)'),
    ('EARLY_DEPARTURE', 'Departure between 00:00 and 06:00 inclusive')
ON DUPLICATE KEY UPDATE filter_name = VALUES(filter_name);

INSERT INTO special_calendar_days (month_number, day_number, day_name)
VALUES
    (1, 1, 'New Year''s Day'),
    (7, 4, 'Independence Day'),
    (11, 29, 'Thanksgiving Day (date specified: 29/11)'),
    (12, 25, 'Christmas Day')
ON DUPLICATE KEY UPDATE day_name = VALUES(day_name);

-- Fill date and HHMM helper fields from actual datetimes where possible.
UPDATE flights
SET flight_date = COALESCE(flight_date, DATE(departure_datetime)),
    dep_time = COALESCE(
        dep_time,
        HOUR(departure_datetime) * 100 + MINUTE(departure_datetime)
    ),
    arr_time = COALESCE(
        arr_time,
        HOUR(arrival_datetime) * 100 + MINUTE(arrival_datetime)
    )
WHERE departure_datetime IS NOT NULL OR arrival_datetime IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Shared derived views. Each view is defined once and is reused below.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW flight_time_metrics AS
SELECT
    f.*,
    COALESCE(
        f.dep_time,
        CASE WHEN f.departure_datetime IS NOT NULL
             THEN HOUR(f.departure_datetime) * 100 + MINUTE(f.departure_datetime)
        END
    ) AS dep_time_hhmm,
    COALESCE(
        f.sched_dep_time,
        CASE WHEN f.departure_scheduled IS NOT NULL
             THEN HOUR(f.departure_scheduled) * 100 + MINUTE(f.departure_scheduled)
        END
    ) AS sched_dep_time_hhmm,
    COALESCE(
        f.arr_time,
        CASE WHEN f.arrival_datetime IS NOT NULL
             THEN HOUR(f.arrival_datetime) * 100 + MINUTE(f.arrival_datetime)
        END
    ) AS arr_time_hhmm,
    CASE
        WHEN f.dep_time IS NOT NULL THEN
            FLOOR(f.dep_time / 100) * 60 + MOD(f.dep_time, 100)
        WHEN f.departure_datetime IS NOT NULL THEN
            HOUR(f.departure_datetime) * 60 + MINUTE(f.departure_datetime)
    END AS dep_time_minutes,
    CASE
        WHEN f.sched_dep_time IS NOT NULL THEN
            FLOOR(f.sched_dep_time / 100) * 60 + MOD(f.sched_dep_time, 100)
        WHEN f.departure_scheduled IS NOT NULL THEN
            HOUR(f.departure_scheduled) * 60 + MINUTE(f.departure_scheduled)
    END AS sched_dep_time_minutes,
    CASE
        WHEN f.arr_time IS NOT NULL THEN
            FLOOR(f.arr_time / 100) * 60 + MOD(f.arr_time, 100)
        WHEN f.arrival_datetime IS NOT NULL THEN
            HOUR(f.arrival_datetime) * 60 + MINUTE(f.arrival_datetime)
    END AS arr_time_minutes,
    CASE
        WHEN f.dep_time IS NULL AND f.departure_datetime IS NULL THEN 1
        ELSE 0
    END AS departure_time_missing,
    CASE
        WHEN f.arr_time IS NULL AND f.arrival_datetime IS NULL THEN 1
        ELSE 0
    END AS arrival_time_missing
FROM flights AS f;

CREATE OR REPLACE VIEW flight_metrics AS
SELECT
    ft.*,
    COALESCE(
        ft.dep_delay_minutes,
        CASE
            WHEN ft.departure_scheduled IS NOT NULL
             AND ft.departure_datetime IS NOT NULL
            THEN TIMESTAMPDIFF(SECOND, ft.departure_scheduled, ft.departure_datetime) / 60.0
            WHEN ft.dep_time_minutes IS NOT NULL
             AND ft.sched_dep_time_minutes IS NOT NULL
            THEN MOD(
                ft.dep_time_minutes - ft.sched_dep_time_minutes + 2160,
                1440
            ) - 720
        END
    ) AS effective_dep_delay_minutes,
    COALESCE(
        ft.arr_delay_minutes,
        CASE
            WHEN ft.arrival_scheduled IS NOT NULL
             AND ft.arrival_datetime IS NOT NULL
            THEN TIMESTAMPDIFF(SECOND, ft.arrival_scheduled, ft.arrival_datetime) / 60.0
        END
    ) AS effective_arr_delay_minutes,
    COALESCE(ft.flight_date, DATE(ft.departure_datetime), DATE(ft.departure_scheduled))
        AS effective_flight_date,
    CASE
        WHEN ft.air_time_minutes > 0
        THEN ft.distance_miles / (ft.air_time_minutes / 60.0)
    END AS calculated_speed_mph,
    CASE
        WHEN ft.dep_time_minutes IS NOT NULL
         AND ft.arr_time_minutes IS NOT NULL
        THEN MOD(ft.arr_time_minutes - ft.dep_time_minutes + 1440, 1440)
    END AS clock_elapsed_minutes_mod_24h
FROM flight_time_metrics AS ft;

CREATE OR REPLACE VIEW flight_route_coordinates AS
SELECT
    f.flight_id,
    f.departure_airport_code AS origin,
    f.arrival_airport_code AS destination,
    f.departure_datetime,
    origin_airport.longitude AS origin_lon,
    origin_airport.latitude AS origin_lat,
    destination_airport.longitude AS dest_lon,
    destination_airport.latitude AS dest_lat
FROM flights AS f
JOIN airports AS origin_airport
    ON origin_airport.airport_code = f.departure_airport_code
JOIN airports AS destination_airport
    ON destination_airport.airport_code = f.arrival_airport_code;

CREATE OR REPLACE VIEW destination_delay_distance AS
SELECT
    arrival_airport_code AS destination,
    COUNT(*) AS flight_count,
    COUNT(DISTINCT distance_miles) AS distinct_distance_count,
    AVG(distance_miles) AS mean_distance_miles,
    MIN(distance_miles) AS min_distance_miles,
    MAX(distance_miles) AS max_distance_miles,
    AVG(effective_arr_delay_minutes) AS mean_arr_delay_minutes,
    AVG(effective_dep_delay_minutes) AS mean_dep_delay_minutes,
    SUM(effective_arr_delay_minutes > 15) AS arrivals_over_15_minutes_late,
    100.0 * SUM(effective_arr_delay_minutes > 15) / COUNT(*)
        AS arrival_delay_over_15_percent
FROM flight_metrics
WHERE arrival_airport_code IS NOT NULL
GROUP BY arrival_airport_code;

-- ---------------------------------------------------------------------------
-- A. Traffic date filters and daily departure counts
-- ---------------------------------------------------------------------------

SELECT
    df.filter_code,
    df.filter_name,
    a.airport_code,
    COUNT(f.flight_id) AS flight_count
FROM date_filters AS df
CROSS JOIN airports AS a
LEFT JOIN flight_metrics AS f
    ON f.airport_code = a.airport_code
    AND (
        (df.filter_code = 'JANUARY_1'
            AND MONTH(f.effective_flight_date) = 1
            AND DAYOFMONTH(f.effective_flight_date) = 1)
        OR (df.filter_code = 'NOVEMBER_DECEMBER'
            AND MONTH(f.effective_flight_date) IN (11, 12))
        OR (df.filter_code = 'SPECIAL_DAYS'
            AND EXISTS (
                SELECT 1
                FROM special_calendar_days AS sd
                WHERE sd.month_number = MONTH(f.effective_flight_date)
                  AND sd.day_number = DAYOFMONTH(f.effective_flight_date)
            ))
        OR (df.filter_code = 'SUMMER'
            AND MONTH(f.effective_flight_date) IN (7, 8, 9))
        OR (df.filter_code = 'EARLY_DEPARTURE'
            AND f.dep_time_minutes BETWEEN 0 AND 360)
    )
WHERE a.airport_code IN ('CDG', 'DXB', 'JFK', 'LHR', 'SIN')
GROUP BY df.filter_code, df.filter_name, a.airport_code
ORDER BY df.filter_code, a.airport_code;

SELECT
    df.filter_code,
    df.filter_name,
    COUNT(f.flight_id) AS flight_count
FROM date_filters AS df
LEFT JOIN flight_metrics AS f
    ON (
        (df.filter_code = 'JANUARY_1'
            AND MONTH(f.effective_flight_date) = 1
            AND DAYOFMONTH(f.effective_flight_date) = 1)
        OR (df.filter_code = 'NOVEMBER_DECEMBER'
            AND MONTH(f.effective_flight_date) IN (11, 12))
        OR (df.filter_code = 'SPECIAL_DAYS'
            AND EXISTS (
                SELECT 1 FROM special_calendar_days AS sd
                WHERE sd.month_number = MONTH(f.effective_flight_date)
                  AND sd.day_number = DAYOFMONTH(f.effective_flight_date)
            ))
        OR (df.filter_code = 'SUMMER'
            AND MONTH(f.effective_flight_date) IN (7, 8, 9))
        OR (df.filter_code = 'EARLY_DEPARTURE'
            AND f.dep_time_minutes BETWEEN 0 AND 360)
    )
GROUP BY df.filter_code, df.filter_name
ORDER BY df.filter_code;

SELECT effective_flight_date AS departure_date, COUNT(*) AS flight_count
FROM flight_metrics
WHERE effective_flight_date IS NOT NULL
GROUP BY effective_flight_date
ORDER BY departure_date;

SELECT effective_flight_date AS departure_date,
       airport_code,
       COUNT(*) AS flight_count
FROM flight_metrics
WHERE effective_flight_date IS NOT NULL
  AND airport_code IN ('CDG', 'DXB', 'JFK', 'LHR', 'SIN')
GROUP BY effective_flight_date, airport_code
ORDER BY departure_date, airport_code;

-- ---------------------------------------------------------------------------
-- B. Delay analysis, quality ranking and route-distance relationship
-- ---------------------------------------------------------------------------

SELECT flight_id, airline_code, arrival_airport_code, effective_arr_delay_minutes
FROM flight_metrics
WHERE effective_arr_delay_minutes IS NOT NULL
ORDER BY effective_arr_delay_minutes DESC, flight_id
LIMIT 20;

SELECT flight_id, airline_code, departure_airport_code, effective_dep_delay_minutes
FROM flight_metrics
WHERE effective_dep_delay_minutes IS NOT NULL
ORDER BY effective_dep_delay_minutes DESC, flight_id
LIMIT 20;

SELECT flight_id,
       airline_code,
       effective_dep_delay_minutes,
       effective_arr_delay_minutes,
       effective_dep_delay_minutes + effective_arr_delay_minutes
           AS combined_delay_minutes
FROM flight_metrics
WHERE effective_dep_delay_minutes > 0
  AND effective_arr_delay_minutes > 0
ORDER BY combined_delay_minutes DESC, flight_id
LIMIT 20;

SELECT AVG(effective_dep_delay_minutes) AS mean_departure_delay_minutes
FROM flight_metrics;

SELECT effective_flight_date AS departure_date,
       COUNT(*) AS flight_count,
       AVG(effective_dep_delay_minutes) AS mean_departure_delay_minutes
FROM flight_metrics
WHERE effective_flight_date IS NOT NULL
  AND effective_dep_delay_minutes IS NOT NULL
GROUP BY effective_flight_date
ORDER BY departure_date;

SELECT AVG(daily_mean_delay) AS mean_of_daily_mean_departure_delay_minutes
FROM (
    SELECT effective_flight_date,
           AVG(effective_dep_delay_minutes) AS daily_mean_delay
    FROM flight_metrics
    WHERE effective_flight_date IS NOT NULL
      AND effective_dep_delay_minutes IS NOT NULL
    GROUP BY effective_flight_date
) AS daily;

SELECT COUNT(*) AS arrived_over_2_hours_late_but_departed_on_time
FROM flight_metrics
WHERE effective_arr_delay_minutes > 120
  AND effective_dep_delay_minutes <= 0;

SELECT COUNT(*) AS neither_delay_over_2_hours
FROM flight_metrics
WHERE effective_dep_delay_minutes <= 120
  AND effective_arr_delay_minutes <= 120;

SELECT flight_id, airline_code, effective_dep_delay_minutes
FROM flight_metrics
WHERE effective_dep_delay_minutes < 0
ORDER BY effective_dep_delay_minutes, flight_id;

SELECT flight_id, airline_code, effective_arr_delay_minutes
FROM flight_metrics
WHERE effective_arr_delay_minutes < 0
ORDER BY effective_arr_delay_minutes, flight_id;

SELECT flight_id,
       airline_code,
       effective_dep_delay_minutes,
       effective_arr_delay_minutes,
       effective_arr_delay_minutes - effective_dep_delay_minutes AS gain_minutes,
       effective_dep_delay_minutes - effective_arr_delay_minutes AS recovered_minutes,
       (effective_arr_delay_minutes - effective_dep_delay_minutes)
           / (air_time_minutes / 60.0) AS gain_per_hour
FROM flight_metrics
WHERE effective_dep_delay_minutes >= 60
  AND effective_arr_delay_minutes < effective_dep_delay_minutes - 30
  AND air_time_minutes > 0
ORDER BY recovered_minutes DESC, flight_id;

SELECT airline_code,
       arrival_airport_code AS destination,
       COUNT(*) AS flight_count,
       SUM(effective_arr_delay_minutes > 15) AS delayed_arrival_count,
       ROUND(100.0 * SUM(effective_arr_delay_minutes > 15) / COUNT(*), 2)
           AS delayed_arrival_rate_percent,
       ROUND(AVG(effective_arr_delay_minutes), 2) AS mean_arrival_delay_minutes
FROM flight_metrics
WHERE airline_code IS NOT NULL
  AND arrival_airport_code IS NOT NULL
  AND effective_arr_delay_minutes IS NOT NULL
GROUP BY airline_code, arrival_airport_code
ORDER BY delayed_arrival_rate_percent DESC, flight_count DESC;

SELECT flight_id, airline_code, distance_miles, air_time_minutes,
       calculated_speed_mph
FROM flight_metrics
WHERE calculated_speed_mph IS NOT NULL
ORDER BY calculated_speed_mph DESC, flight_id;

SELECT flight_id, airline_code, distance_miles
FROM flights
WHERE distance_miles IS NOT NULL
ORDER BY distance_miles DESC, flight_id
LIMIT 1;

SELECT flight_id, airline_code, distance_miles
FROM flights
WHERE distance_miles IS NOT NULL
ORDER BY distance_miles ASC, flight_id
LIMIT 1;

SELECT *
FROM destination_delay_distance
ORDER BY destination;

SELECT destination,
       flight_count,
       distinct_distance_count,
       mean_distance_miles,
       mean_arr_delay_minutes
FROM destination_delay_distance
WHERE destination <> 'HNL'
ORDER BY mean_distance_miles;

SELECT destination, flight_count, mean_distance_miles
FROM destination_delay_distance
ORDER BY mean_distance_miles DESC;

SELECT hnl.mean_distance_miles AS hnl_mean_distance_miles,
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

SELECT destination,
       flight_count,
       mean_arr_delay_minutes,
       arrivals_over_15_minutes_late,
       arrival_delay_over_15_percent
FROM destination_delay_distance
ORDER BY mean_arr_delay_minutes DESC, flight_count DESC;

SELECT airline_code,
       arrival_airport_code AS destination,
       COUNT(*) AS flight_count,
       AVG(effective_arr_delay_minutes) AS mean_arr_delay_minutes,
       SUM(effective_arr_delay_minutes > 15) AS arrivals_over_15_minutes_late,
       100.0 * SUM(effective_arr_delay_minutes > 15) / COUNT(*)
           AS arrival_delay_over_15_percent
FROM flight_metrics
WHERE airline_code IS NOT NULL
  AND effective_arr_delay_minutes IS NOT NULL
GROUP BY airline_code, arrival_airport_code
ORDER BY mean_arr_delay_minutes DESC, flight_count DESC;

SELECT 'arr_delay_minutes' AS variable,
       COUNT(effective_arr_delay_minutes) AS flight_count,
       AVG(effective_arr_delay_minutes) AS mean_minutes,
       MIN(effective_arr_delay_minutes) AS min_minutes,
       MAX(effective_arr_delay_minutes) AS max_minutes,
       STDDEV_SAMP(effective_arr_delay_minutes) AS sample_std_dev_minutes
FROM flight_metrics
UNION ALL
SELECT 'dep_delay_minutes',
       COUNT(effective_dep_delay_minutes),
       AVG(effective_dep_delay_minutes),
       MIN(effective_dep_delay_minutes),
       MAX(effective_dep_delay_minutes),
       STDDEV_SAMP(effective_dep_delay_minutes)
FROM flight_metrics;

WITH delay_values AS (
    SELECT 'arr_delay_minutes' AS variable,
           effective_arr_delay_minutes AS delay_minutes
    FROM flight_metrics
    WHERE effective_arr_delay_minutes IS NOT NULL
    UNION ALL
    SELECT 'dep_delay_minutes', effective_dep_delay_minutes
    FROM flight_metrics
    WHERE effective_dep_delay_minutes IS NOT NULL
), ranked_delay_values AS (
    SELECT variable,
           delay_minutes,
           ROW_NUMBER() OVER (PARTITION BY variable ORDER BY delay_minutes) AS row_num,
           COUNT(*) OVER (PARTITION BY variable) AS sample_size
    FROM delay_values
)
SELECT variable,
       MAX(sample_size) AS flight_count,
       MAX(CASE WHEN row_num = GREATEST(1, CEIL(sample_size * 0.25))
                THEN delay_minutes END) AS q1_minutes,
       AVG(CASE WHEN row_num IN (
                    GREATEST(1, FLOOR((sample_size + 1) / 2.0)),
                    GREATEST(1, CEIL((sample_size + 1) / 2.0))
                ) THEN delay_minutes END) AS median_minutes,
       MAX(CASE WHEN row_num = GREATEST(1, CEIL(sample_size * 0.75))
                THEN delay_minutes END) AS q3_minutes
FROM ranked_delay_values
GROUP BY variable;

SELECT departure_airport_code AS departure_airport,
       COUNT(*) AS flight_count,
       AVG(effective_arr_delay_minutes) AS mean_arr_delay_minutes
FROM flight_metrics
WHERE departure_airport_code IS NOT NULL
  AND effective_arr_delay_minutes IS NOT NULL
GROUP BY departure_airport_code
ORDER BY mean_arr_delay_minutes ASC
LIMIT 1;

SELECT HOUR(departure_datetime) AS departure_hour,
       COUNT(*) AS flight_count,
       AVG(effective_arr_delay_minutes) AS mean_arr_delay_minutes,
       AVG(effective_dep_delay_minutes) AS mean_dep_delay_minutes
FROM flight_metrics
WHERE departure_datetime IS NOT NULL
  AND effective_arr_delay_minutes IS NOT NULL
GROUP BY HOUR(departure_datetime)
ORDER BY departure_hour;

SELECT flight_id,
       airline_code,
       departure_airport_code,
       arrival_airport_code,
       HOUR(departure_datetime) AS departure_hour,
       effective_arr_delay_minutes
FROM flight_metrics
WHERE departure_datetime IS NOT NULL;

-- ---------------------------------------------------------------------------
-- C. Missing data and cancellation analysis
-- ---------------------------------------------------------------------------

SELECT 'airport_code' AS column_name, COUNT(*) - COUNT(airport_code) AS missing_count,
       COUNT(*) AS row_count,
       100.0 * (COUNT(*) - COUNT(airport_code)) / NULLIF(COUNT(*), 0) AS missing_percent
FROM flights
UNION ALL
SELECT 'aircraft_id', COUNT(*) - COUNT(aircraft_id), COUNT(*),
       100.0 * (COUNT(*) - COUNT(aircraft_id)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'departure_airport_code', COUNT(*) - COUNT(departure_airport_code), COUNT(*),
       100.0 * (COUNT(*) - COUNT(departure_airport_code)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'arrival_airport_code', COUNT(*) - COUNT(arrival_airport_code), COUNT(*),
       100.0 * (COUNT(*) - COUNT(arrival_airport_code)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'flight_date', COUNT(*) - COUNT(flight_date), COUNT(*),
       100.0 * (COUNT(*) - COUNT(flight_date)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'departure_datetime', COUNT(*) - COUNT(departure_datetime), COUNT(*),
       100.0 * (COUNT(*) - COUNT(departure_datetime)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'departure_scheduled', COUNT(*) - COUNT(departure_scheduled), COUNT(*),
       100.0 * (COUNT(*) - COUNT(departure_scheduled)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'arrival_datetime', COUNT(*) - COUNT(arrival_datetime), COUNT(*),
       100.0 * (COUNT(*) - COUNT(arrival_datetime)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'arrival_scheduled', COUNT(*) - COUNT(arrival_scheduled), COUNT(*),
       100.0 * (COUNT(*) - COUNT(arrival_scheduled)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'dep_delay_minutes', COUNT(*) - COUNT(dep_delay_minutes), COUNT(*),
       100.0 * (COUNT(*) - COUNT(dep_delay_minutes)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'arr_delay_minutes', COUNT(*) - COUNT(arr_delay_minutes), COUNT(*),
       100.0 * (COUNT(*) - COUNT(arr_delay_minutes)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'airline_code', COUNT(*) - COUNT(airline_code), COUNT(*),
       100.0 * (COUNT(*) - COUNT(airline_code)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'air_time_minutes', COUNT(*) - COUNT(air_time_minutes), COUNT(*),
       100.0 * (COUNT(*) - COUNT(air_time_minutes)) / NULLIF(COUNT(*), 0) FROM flights
UNION ALL
SELECT 'distance_miles', COUNT(*) - COUNT(distance_miles), COUNT(*),
       100.0 * (COUNT(*) - COUNT(distance_miles)) / NULLIF(COUNT(*), 0) FROM flights;

-- Cancellation rule: both actual departure and actual arrival are missing.
SELECT COUNT(*) AS cancelled_flight_count
FROM flight_metrics
WHERE departure_time_missing = 1
  AND arrival_time_missing = 1;

SELECT arrival_airport_code AS destination, COUNT(*) AS cancelled_flight_count
FROM flight_metrics
WHERE departure_time_missing = 1
  AND arrival_time_missing = 1
GROUP BY arrival_airport_code
ORDER BY cancelled_flight_count DESC, destination;

SELECT airline_code, COUNT(*) AS cancelled_flight_count
FROM flight_metrics
WHERE departure_time_missing = 1
  AND arrival_time_missing = 1
GROUP BY airline_code
ORDER BY cancelled_flight_count DESC, airline_code;

SELECT DATE_FORMAT(effective_flight_date, '%Y-%m') AS flight_month,
       COUNT(*) AS cancelled_flight_count
FROM flight_metrics
WHERE departure_time_missing = 1
  AND arrival_time_missing = 1
GROUP BY DATE_FORMAT(effective_flight_date, '%Y-%m')
ORDER BY flight_month;

SELECT DATE_FORMAT(effective_flight_date, '%Y-%m') AS flight_month,
       arrival_airport_code AS destination,
       airline_code,
       COUNT(*) AS cancelled_flight_count
FROM flight_metrics
WHERE departure_time_missing = 1
  AND arrival_time_missing = 1
GROUP BY DATE_FORMAT(effective_flight_date, '%Y-%m'),
         arrival_airport_code,
         airline_code
ORDER BY flight_month, cancelled_flight_count DESC;

SELECT flight_id,
       effective_flight_date,
       airline_code,
       departure_airport_code,
       arrival_airport_code,
       effective_dep_delay_minutes,
       effective_arr_delay_minutes,
       departure_time_missing,
       arrival_time_missing
FROM flight_metrics
ORDER BY (effective_dep_delay_minutes IS NOT NULL) ASC,
         effective_dep_delay_minutes DESC,
         flight_id;

SELECT flight_id,
       effective_flight_date,
       dep_time_hhmm,
       effective_dep_delay_minutes
FROM flight_metrics
ORDER BY (effective_dep_delay_minutes IS NOT NULL) ASC,
         effective_dep_delay_minutes DESC,
         (dep_time_minutes IS NOT NULL) ASC,
         dep_time_minutes ASC,
         flight_id;

-- ---------------------------------------------------------------------------
-- D. Custom HHMM sorting, min_rank ties, and air-time comparison
-- ---------------------------------------------------------------------------

SELECT flight_id,
       dep_time_hhmm,
       dep_time_minutes,
       sched_dep_time_hhmm,
       sched_dep_time_minutes,
       effective_dep_delay_minutes,
       CASE
           WHEN dep_time_minutes IS NULL OR sched_dep_time_minutes IS NULL THEN NULL
           ELSE MOD(dep_time_minutes - sched_dep_time_minutes + 2160, 1440) - 720
       END AS calculated_dep_delay_minutes,
       effective_dep_delay_minutes - CASE
           WHEN dep_time_minutes IS NULL OR sched_dep_time_minutes IS NULL THEN NULL
           ELSE MOD(dep_time_minutes - sched_dep_time_minutes + 2160, 1440) - 720
       END AS reported_minus_calculated_delay_minutes
FROM flight_metrics;

WITH ranked_flights AS (
    SELECT flight_id,
           dep_time_hhmm,
           sched_dep_time_hhmm,
           effective_dep_delay_minutes,
           RANK() OVER (ORDER BY effective_dep_delay_minutes DESC) AS delay_rank
    FROM flight_metrics
    WHERE effective_dep_delay_minutes IS NOT NULL
)
SELECT *
FROM ranked_flights
WHERE delay_rank <= 10
ORDER BY delay_rank, flight_id;

SELECT flight_id,
       dep_time_minutes,
       arr_time_minutes,
       clock_elapsed_minutes_mod_24h,
       air_time_minutes,
       clock_elapsed_minutes_mod_24h - air_time_minutes
           AS clock_elapsed_minus_air_time_minutes
FROM flight_metrics
WHERE dep_time_minutes IS NOT NULL
  AND arr_time_minutes IS NOT NULL
  AND air_time_minutes IS NOT NULL;

-- Clock HHMM values do not encode time zones or dates. Use UTC timestamps for
-- real elapsed time; gate-to-gate elapsed time also includes taxiing unlike air time.

-- ---------------------------------------------------------------------------
-- E. Geospatial routes and most frequent destinations
-- ---------------------------------------------------------------------------

SELECT COUNT(*) AS flights_with_both_airport_coordinates
FROM flight_route_coordinates;

SELECT origin,
       destination,
       COUNT(*) AS flight_count,
       MAX(origin_lon) AS origin_lon,
       MAX(origin_lat) AS origin_lat,
       MAX(dest_lon) AS dest_lon,
       MAX(dest_lat) AS dest_lat
FROM flight_route_coordinates
GROUP BY origin, destination
ORDER BY flight_count DESC, origin, destination
LIMIT 100;

SELECT arrival_airport_code AS destination,
       COUNT(*) AS flight_count
FROM flights
WHERE arrival_airport_code IS NOT NULL
GROUP BY arrival_airport_code
ORDER BY flight_count DESC, destination
LIMIT 5;

SELECT origin,
       destination,
       COUNT(*) AS flight_count,
       MAX(origin_lon) AS origin_lon,
       MAX(origin_lat) AS origin_lat,
       MAX(dest_lon) AS dest_lon,
       MAX(dest_lat) AS dest_lat
FROM flight_route_coordinates
WHERE origin_lon BETWEEN -126 AND -66
  AND dest_lon BETWEEN -126 AND -66
  AND origin_lat BETWEEN 23 AND 51
  AND dest_lat BETWEEN 23 AND 51
GROUP BY origin, destination
ORDER BY flight_count DESC, origin, destination
LIMIT 100;
