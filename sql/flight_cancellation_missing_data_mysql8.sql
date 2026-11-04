CREATE DATABASE IF NOT EXISTS flight_cancellation_analysis
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE flight_cancellation_analysis;

CREATE TABLE IF NOT EXISTS flights (
    flight_id VARCHAR(40) NOT NULL,
    flight_date DATE NULL,
    dep_time TIME NULL,
    dep_delay DECIMAL(8, 2) NULL,
    arr_time TIME NULL,
    arr_delay DECIMAL(8, 2) NULL,
    dest CHAR(3) NULL,
    carrier VARCHAR(8) NULL,
    source_file VARCHAR(100) NULL,
    PRIMARY KEY (flight_id),
    INDEX idx_flight_date (flight_date),
    INDEX idx_cancel_destination (dest),
    INDEX idx_cancel_carrier (carrier)
) ENGINE = InnoDB;

-- Import enriched CSV data with optional/empty values retained as NULL.
-- Expected headers:
-- flight_id,flight_date,dep_time,dep_delay,arr_time,arr_delay,dest,carrier
-- Use NULLIF for fields represented as an empty string in CSV.
--
-- LOAD DATA LOCAL INFILE 'C:\\path\\to\\flights.csv'
-- INTO TABLE flights
-- CHARACTER SET utf8mb4
-- FIELDS TERMINATED BY ','
-- OPTIONALLY ENCLOSED BY '"'
-- LINES TERMINATED BY '\r\n'
-- IGNORE 1 LINES
-- (
--     flight_id,
--     @flight_date,
--     @dep_time,
--     @dep_delay,
--     @arr_time,
--     @arr_delay,
--     @dest,
--     @carrier
-- )
-- SET
--     flight_date = STR_TO_DATE(NULLIF(@flight_date, ''), '%Y-%m-%d'),
--     dep_time = NULLIF(@dep_time, ''),
--     dep_delay = NULLIF(@dep_delay, ''),
--     arr_time = NULLIF(@arr_time, ''),
--     arr_delay = NULLIF(@arr_delay, ''),
--     dest = NULLIF(@dest, ''),
--     carrier = NULLIF(@carrier, '');

-- 1. Missing count and proportion for every column.
SELECT 'flight_id' AS column_name, SUM(flight_id IS NULL) AS missing_count,
       COUNT(*) AS row_count,
       100.0 * SUM(flight_id IS NULL) / COUNT(*) AS missing_percent
FROM flights
UNION ALL
SELECT 'flight_date', SUM(flight_date IS NULL), COUNT(*),
       100.0 * SUM(flight_date IS NULL) / COUNT(*) FROM flights
UNION ALL
SELECT 'dep_time', SUM(dep_time IS NULL), COUNT(*),
       100.0 * SUM(dep_time IS NULL) / COUNT(*) FROM flights
UNION ALL
SELECT 'dep_delay', SUM(dep_delay IS NULL), COUNT(*),
       100.0 * SUM(dep_delay IS NULL) / COUNT(*) FROM flights
UNION ALL
SELECT 'arr_time', SUM(arr_time IS NULL), COUNT(*),
       100.0 * SUM(arr_time IS NULL) / COUNT(*) FROM flights
UNION ALL
SELECT 'arr_delay', SUM(arr_delay IS NULL), COUNT(*),
       100.0 * SUM(arr_delay IS NULL) / COUNT(*) FROM flights
UNION ALL
SELECT 'dest', SUM(dest IS NULL), COUNT(*),
       100.0 * SUM(dest IS NULL) / COUNT(*) FROM flights
UNION ALL
SELECT 'carrier', SUM(carrier IS NULL), COUNT(*),
       100.0 * SUM(carrier IS NULL) / COUNT(*) FROM flights;

-- 2. A flight is classified as cancelled only when both times are missing.
SELECT COUNT(*) AS cancelled_flight_count
FROM flights
WHERE dep_time IS NULL
  AND arr_time IS NULL;

-- Cancelled flights by destination.
SELECT dest, COUNT(*) AS cancelled_flight_count
FROM flights
WHERE dep_time IS NULL
  AND arr_time IS NULL
GROUP BY dest
ORDER BY cancelled_flight_count DESC, dest;

-- Cancelled flights by airline/carrier.
SELECT carrier, COUNT(*) AS cancelled_flight_count
FROM flights
WHERE dep_time IS NULL
  AND arr_time IS NULL
GROUP BY carrier
ORDER BY cancelled_flight_count DESC, carrier;

-- Cancelled flights by month.
SELECT DATE_FORMAT(flight_date, '%Y-%m') AS flight_month,
       COUNT(*) AS cancelled_flight_count
FROM flights
WHERE dep_time IS NULL
  AND arr_time IS NULL
GROUP BY DATE_FORMAT(flight_date, '%Y-%m')
ORDER BY flight_month;

-- Cancelled flights by destination, carrier, and month.
SELECT DATE_FORMAT(flight_date, '%Y-%m') AS flight_month,
       dest,
       carrier,
       COUNT(*) AS cancelled_flight_count
FROM flights
WHERE dep_time IS NULL
  AND arr_time IS NULL
GROUP BY DATE_FORMAT(flight_date, '%Y-%m'), dest, carrier
ORDER BY flight_month, cancelled_flight_count DESC;

-- 3. dep_delay descending, with NULL values first (MySQL puts NULL last in DESC
-- by default, so sort explicitly on the NULL indicator).
SELECT *
FROM flights
ORDER BY (dep_delay IS NOT NULL) ASC,
         dep_delay DESC;

-- 4. dep_delay descending, then dep_time ascending; NULLs first for both keys.
SELECT *
FROM flights
ORDER BY (dep_delay IS NOT NULL) ASC,
         dep_delay DESC,
         (dep_time IS NOT NULL) ASC,
         dep_time ASC;
