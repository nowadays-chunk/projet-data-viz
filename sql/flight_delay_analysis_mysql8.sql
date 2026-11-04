CREATE DATABASE IF NOT EXISTS flight_delay_analytics
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE flight_delay_analytics;

CREATE TABLE IF NOT EXISTS airlines (
    airline_code VARCHAR(8) NOT NULL,
    airline_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (airline_code)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS airports (
    airport_code CHAR(3) NOT NULL,
    airport_name VARCHAR(100) NULL,
    PRIMARY KEY (airport_code)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS flights (
    flight_id VARCHAR(40) NOT NULL,
    airline_code VARCHAR(8) NOT NULL,
    aircraft_id VARCHAR(20) NULL,
    departure_airport_code CHAR(3) NOT NULL,
    arrival_airport_code CHAR(3) NOT NULL,
    departure_scheduled DATETIME NULL,
    departure_actual DATETIME NULL,
    arrival_scheduled DATETIME NULL,
    arrival_actual DATETIME NULL,
    dep_delay_minutes DECIMAL(8, 2) NOT NULL,
    arr_delay_minutes DECIMAL(8, 2) NOT NULL,
    air_time_minutes DECIMAL(8, 2) NOT NULL,
    distance_miles DECIMAL(10, 2) NOT NULL,
    gain_minutes DECIMAL(8, 2)
        GENERATED ALWAYS AS (arr_delay_minutes - dep_delay_minutes) STORED,
    speed_mph DECIMAL(10, 2)
        GENERATED ALWAYS AS (
            distance_miles * 60.0 / NULLIF(air_time_minutes, 0)
        ) STORED,
    PRIMARY KEY (flight_id),
    CONSTRAINT fk_delay_flight_airline
        FOREIGN KEY (airline_code) REFERENCES airlines (airline_code),
    CONSTRAINT fk_delay_flight_departure_airport
        FOREIGN KEY (departure_airport_code) REFERENCES airports (airport_code),
    CONSTRAINT fk_delay_flight_arrival_airport
        FOREIGN KEY (arrival_airport_code) REFERENCES airports (airport_code),
    CONSTRAINT chk_flight_air_time CHECK (air_time_minutes > 0),
    CONSTRAINT chk_flight_distance CHECK (distance_miles >= 0),
    INDEX idx_flight_departure_actual (departure_actual),
    INDEX idx_flight_arrival_delay (arr_delay_minutes),
    INDEX idx_flight_departure_delay (dep_delay_minutes),
    INDEX idx_flight_airline_destination
        (airline_code, arrival_airport_code)
) ENGINE = InnoDB;

-- Seed airports used by this project's generated routes.
INSERT INTO airports (airport_code, airport_name)
VALUES
    ('CDG', 'Paris Charles de Gaulle'),
    ('DXB', 'Dubai'),
    ('JFK', 'New York John F. Kennedy'),
    ('LHR', 'London Heathrow'),
    ('SIN', 'Singapore Changi'),
    ('MAD', 'Madrid'),
    ('MIA', 'Miami'),
    ('BKK', 'Bangkok'),
    ('AMS', 'Amsterdam')
ON DUPLICATE KEY UPDATE airport_name = VALUES(airport_name);

-- Insert the actual airline codes and names into airlines before importing flights.

-- Import enriched CSV files with headers:
-- flight_id,airline_code,aircraft_id,dep_airport,arr_airport,
-- departure_scheduled,departure_actual,arrival_scheduled,arrival_actual,
-- dep_delay_minutes,arr_delay_minutes,air_time_minutes,distance_miles
--
-- The current project CSVs do not contain the airline, schedule/delay,
-- air-time, or distance fields. Enrich them before running this import.
-- The Python script accepts the same information using either dep_delay/arr_delay
-- or dep_delay_minutes/arr_delay_minutes, and accepts departure_actual as the
-- actual departure date used to calculate daily averages.
-- Optionally derive delays when importing scheduled and actual timestamps:
-- dep_delay_minutes = TIMESTAMPDIFF(SECOND, departure_scheduled,
--                                    departure_actual) / 60.0
-- arr_delay_minutes = TIMESTAMPDIFF(SECOND, arrival_scheduled,
--                                    arrival_actual) / 60.0
--
-- Example after the source CSV has the schema above:
-- LOAD DATA LOCAL INFILE
--     'C:\\path\\to\\enriched_flights.csv'
-- INTO TABLE flights
-- CHARACTER SET utf8mb4
-- FIELDS TERMINATED BY ','
-- OPTIONALLY ENCLOSED BY '"'
-- LINES TERMINATED BY '\r\n'
-- IGNORE 1 LINES
-- (
--     flight_id,
--     airline_code,
--     @aircraft_id,
--     departure_airport_code,
--     arrival_airport_code,
--     @departure_scheduled,
--     @departure_actual,
--     @arrival_scheduled,
--     @arrival_actual,
--     dep_delay_minutes,
--     arr_delay_minutes,
--     air_time_minutes,
--     distance_miles
-- )
-- SET
--     aircraft_id = NULLIF(@aircraft_id, ''),
--     departure_scheduled = NULLIF(@departure_scheduled, ''),
--     departure_actual = NULLIF(@departure_actual, ''),
--     arrival_scheduled = NULLIF(@arrival_scheduled, ''),
--     arrival_actual = NULLIF(@arrival_actual, '');

-- Query 1a: flights with the greatest arrival delays.
SELECT flight_id, airline_code, arrival_airport_code, arr_delay_minutes
FROM flights
ORDER BY arr_delay_minutes DESC, flight_id
LIMIT 20;

-- Query 1b: flights with the greatest departure delays.
SELECT flight_id, airline_code, departure_airport_code, dep_delay_minutes
FROM flights
ORDER BY dep_delay_minutes DESC, flight_id
LIMIT 20;

-- Query 1c: flights delayed at both departure and arrival, ranked by combined delay.
SELECT
    flight_id,
    airline_code,
    dep_delay_minutes,
    arr_delay_minutes,
    dep_delay_minutes + arr_delay_minutes AS combined_delay_minutes
FROM flights
WHERE dep_delay_minutes > 0
  AND arr_delay_minutes > 0
ORDER BY combined_delay_minutes DESC, flight_id
LIMIT 20;

-- Query 2a: mean departure delay over all flights.
SELECT AVG(dep_delay_minutes) AS mean_departure_delay_minutes
FROM flights;

-- Query 2b: mean departure delay per calendar day.
SELECT
    DATE(departure_actual) AS departure_date,
    COUNT(*) AS flight_count,
    AVG(dep_delay_minutes) AS mean_departure_delay_minutes
FROM flights
WHERE departure_actual IS NOT NULL
GROUP BY DATE(departure_actual)
ORDER BY departure_date;

-- Query 2c: average of the daily means (each day has equal weight).
SELECT AVG(daily_mean_delay) AS mean_of_daily_mean_departure_delay_minutes
FROM (
    SELECT DATE(departure_actual) AS departure_date,
           AVG(dep_delay_minutes) AS daily_mean_delay
    FROM flights
    WHERE departure_actual IS NOT NULL
    GROUP BY DATE(departure_actual)
) AS daily;

-- Query 3a: arrived over 2 hours late despite departing on time or early.
SELECT COUNT(*) AS flight_count
FROM flights
WHERE arr_delay_minutes > 120
  AND dep_delay_minutes <= 0;

SELECT flight_id, airline_code, dep_delay_minutes, arr_delay_minutes
FROM flights
WHERE arr_delay_minutes > 120
  AND dep_delay_minutes <= 0
ORDER BY arr_delay_minutes DESC, flight_id;

-- Query 3b: neither departure nor arrival delay exceeded 2 hours.
SELECT COUNT(*) AS flight_count
FROM flights
WHERE dep_delay_minutes <= 120
  AND arr_delay_minutes <= 120;

SELECT flight_id, airline_code, dep_delay_minutes, arr_delay_minutes
FROM flights
WHERE dep_delay_minutes <= 120
  AND arr_delay_minutes <= 120
ORDER BY flight_id;
-- Query 4a: departed earlier than scheduled.
SELECT flight_id, airline_code, departure_airport_code, dep_delay_minutes
FROM flights
WHERE dep_delay_minutes < 0
ORDER BY dep_delay_minutes, flight_id;

-- Query 4b: arrived earlier than scheduled.
SELECT flight_id, airline_code, arrival_airport_code, arr_delay_minutes
FROM flights
WHERE arr_delay_minutes < 0
ORDER BY arr_delay_minutes, flight_id;

-- Query 5: departed at least 60 minutes late and recovered more than 30 minutes.
-- Given gain = arr_delay - dep_delay, a recovery is a negative gain.
SELECT
    flight_id,
    airline_code,
    dep_delay_minutes,
    arr_delay_minutes,
    gain_minutes,
    -gain_minutes AS recovered_minutes,
    gain_minutes / (air_time_minutes / 60.0) AS gain_per_hour
FROM flights
WHERE dep_delay_minutes >= 60
  AND gain_minutes < -30
ORDER BY recovered_minutes DESC, flight_id;

-- All partial or complete recoveries after a delayed departure.
SELECT
    flight_id,
    airline_code,
    dep_delay_minutes,
    arr_delay_minutes,
    gain_minutes,
    -gain_minutes AS recovered_minutes,
    gain_minutes / (air_time_minutes / 60.0) AS gain_per_hour
FROM flights
WHERE dep_delay_minutes > 0
  AND gain_minutes < 0
ORDER BY recovered_minutes DESC, flight_id;

-- Query 6a: destination reliability, using arrival delay > 15 minutes.
SELECT
    airline_code,
    arrival_airport_code AS destination,
    COUNT(*) AS flight_count,
    SUM(arr_delay_minutes > 15) AS delayed_arrival_count,
    ROUND(100.0 * SUM(arr_delay_minutes > 15) / COUNT(*), 2)
        AS delayed_arrival_rate_percent,
    ROUND(AVG(arr_delay_minutes), 2) AS mean_arrival_delay_minutes
FROM flights
GROUP BY airline_code, arrival_airport_code
ORDER BY delayed_arrival_rate_percent DESC, flight_count DESC;

-- Query 6b: create a view so gain and speed are available as named variables.
CREATE OR REPLACE VIEW flight_metrics AS
SELECT
    f.*,
    f.arr_delay_minutes - f.dep_delay_minutes AS calculated_gain_minutes,
    (f.arr_delay_minutes - f.dep_delay_minutes)
        / (f.air_time_minutes / 60.0) AS calculated_gain_per_hour,
    f.distance_miles / (f.air_time_minutes / 60.0) AS calculated_speed_mph
FROM flights AS f;

-- Query 6c: recovery details using the calculated variables in the view.
SELECT
    flight_id,
    airline_code,
    dep_delay_minutes,
    arr_delay_minutes,
    calculated_gain_minutes,
    -calculated_gain_minutes AS recovered_minutes,
    calculated_gain_per_hour
FROM flight_metrics
WHERE dep_delay_minutes >= 60
  AND calculated_gain_minutes < -30
ORDER BY recovered_minutes DESC;

-- Query 7a: rank by speed using the generated speed_mph column.
SELECT flight_id, airline_code, distance_miles, air_time_minutes, speed_mph
FROM flights
ORDER BY speed_mph DESC, flight_id;

-- Query 7b: same speed ranking calculated directly, without a stored variable.
SELECT
    flight_id,
    airline_code,
    distance_miles,
    air_time_minutes,
    distance_miles / (air_time_minutes / 60.0) AS speed_mph
FROM flights
ORDER BY speed_mph DESC, flight_id;

-- Query 7c: longest and shortest routes.
SELECT flight_id, airline_code, distance_miles
FROM flights
ORDER BY distance_miles DESC, flight_id
LIMIT 1;

SELECT flight_id, airline_code, distance_miles
FROM flights
ORDER BY distance_miles ASC, flight_id
LIMIT 1;
