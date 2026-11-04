CREATE DATABASE IF NOT EXISTS airport_analytics
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE airport_analytics;

CREATE TABLE IF NOT EXISTS airports (
    airport_code CHAR(3) NOT NULL,
    airport_name VARCHAR(100) NULL,
    PRIMARY KEY (airport_code)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS flights (
    flight_id VARCHAR(40) NOT NULL,
    airport_code CHAR(3) NOT NULL,
    aircraft_id VARCHAR(20) NOT NULL,
    departure_airport_code CHAR(3) NOT NULL,
    arrival_airport_code CHAR(3) NOT NULL,
    departure_datetime DATETIME NOT NULL,
    arrival_datetime DATETIME NOT NULL,
    duration_hours DECIMAL(5, 2) NOT NULL,
    PRIMARY KEY (flight_id),
    CONSTRAINT fk_flights_airport
        FOREIGN KEY (airport_code) REFERENCES airports (airport_code),
    CONSTRAINT fk_flights_departure_airport
        FOREIGN KEY (departure_airport_code) REFERENCES airports (airport_code),
    CONSTRAINT fk_flights_arrival_airport
        FOREIGN KEY (arrival_airport_code) REFERENCES airports (airport_code),
    INDEX idx_flights_departure_datetime (departure_datetime),
    INDEX idx_flights_airport_departure (airport_code, departure_datetime),
    INDEX idx_flights_departure_airport (departure_airport_code),
    INDEX idx_flights_arrival_airport (arrival_airport_code)
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

-- Import one source CSV at a time. Repeat for CDG, DXB, JFK, LHR, and SIN.
-- Change the filename in LOCAL INFILE for each airport.
-- Enable LOCAL INFILE in both the MySQL server and client if it is disabled.
--
-- LOAD DATA LOCAL INFILE
--     'C:\\Users\\DELL\\Documents\\flights\\data\\airports\\CDG_flights.csv'
-- INTO TABLE flights
-- CHARACTER SET utf8mb4
-- FIELDS TERMINATED BY ','
-- OPTIONALLY ENCLOSED BY '"'
-- LINES TERMINATED BY '\r\n'
-- IGNORE 1 LINES
-- (
--     @flight_id,
--     @source_airport_code,
--     @aircraft_id,
--     @departure_airport_code,
--     @arrival_airport_code,
--     @departure_datetime,
--     @arrival_datetime,
--     @duration_hours
-- )
-- SET
--     flight_id = @flight_id,
--     airport_code = @source_airport_code,
--     aircraft_id = @aircraft_id,
--     departure_airport_code = @departure_airport_code,
--     arrival_airport_code = @arrival_airport_code,
--     departure_datetime = STR_TO_DATE(@departure_datetime, '%Y-%m-%d %H:%i:%s'),
--     arrival_datetime = STR_TO_DATE(@arrival_datetime, '%Y-%m-%d %H:%i:%s'),
--     duration_hours = @duration_hours;

-- Query 1: the count by filter and departure airport, including zero-count bars.
SELECT
    df.filter_code,
    df.filter_name,
    a.airport_code,
    COUNT(f.flight_id) AS flight_count
FROM date_filters AS df
CROSS JOIN airports AS a
LEFT JOIN flights AS f
    ON f.airport_code = a.airport_code
    AND (
        (df.filter_code = 'JANUARY_1'
            AND MONTH(f.departure_datetime) = 1
            AND DAYOFMONTH(f.departure_datetime) = 1)
        OR
        (df.filter_code = 'NOVEMBER_DECEMBER'
            AND MONTH(f.departure_datetime) IN (11, 12))
        OR
        (df.filter_code = 'SPECIAL_DAYS'
            AND EXISTS (
                SELECT 1
                FROM special_calendar_days AS sd
                WHERE sd.month_number = MONTH(f.departure_datetime)
                  AND sd.day_number = DAYOFMONTH(f.departure_datetime)
            ))
        OR
        (df.filter_code = 'SUMMER'
            AND MONTH(f.departure_datetime) IN (7, 8, 9))
        OR
        (df.filter_code = 'EARLY_DEPARTURE'
            AND TIME(f.departure_datetime) BETWEEN '00:00:00' AND '06:00:00')
    )
WHERE a.airport_code IN ('CDG', 'DXB', 'JFK', 'LHR', 'SIN')
GROUP BY df.filter_code, df.filter_name, a.airport_code
ORDER BY df.filter_code, a.airport_code;

-- Query 2: overall total for each filter, used in each graph's title.
SELECT
    df.filter_code,
    df.filter_name,
    COUNT(f.flight_id) AS flight_count
FROM date_filters AS df
LEFT JOIN flights AS f
    ON (
        (df.filter_code = 'JANUARY_1'
            AND MONTH(f.departure_datetime) = 1
            AND DAYOFMONTH(f.departure_datetime) = 1)
        OR
        (df.filter_code = 'NOVEMBER_DECEMBER'
            AND MONTH(f.departure_datetime) IN (11, 12))
        OR
        (df.filter_code = 'SPECIAL_DAYS'
            AND EXISTS (
                SELECT 1
                FROM special_calendar_days AS sd
                WHERE sd.month_number = MONTH(f.departure_datetime)
                  AND sd.day_number = DAYOFMONTH(f.departure_datetime)
            ))
        OR
        (df.filter_code = 'SUMMER'
            AND MONTH(f.departure_datetime) IN (7, 8, 9))
        OR
        (df.filter_code = 'EARLY_DEPARTURE'
            AND TIME(f.departure_datetime) BETWEEN '00:00:00' AND '06:00:00')
    )
GROUP BY df.filter_code, df.filter_name
ORDER BY df.filter_code;

-- Query 3: number of departures per calendar date (dates with at least one flight).
SELECT
    DATE(departure_datetime) AS departure_date,
    COUNT(*) AS flight_count
FROM flights
GROUP BY DATE(departure_datetime)
ORDER BY departure_date;

-- Query 4: departure-date counts split by airport, if a per-airport daily graph is wanted.
SELECT
    DATE(departure_datetime) AS departure_date,
    airport_code,
    COUNT(*) AS flight_count
FROM flights
WHERE airport_code IN ('CDG', 'DXB', 'JFK', 'LHR', 'SIN')
GROUP BY DATE(departure_datetime), airport_code
ORDER BY departure_date, airport_code;
