CREATE DATABASE IF NOT EXISTS airport_route_mapping
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE airport_route_mapping;

CREATE TABLE IF NOT EXISTS airports (
    airport_code CHAR(3) NOT NULL,
    airport_name VARCHAR(120) NOT NULL,
    city VARCHAR(80) NOT NULL,
    country VARCHAR(80) NOT NULL,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(9, 6) NOT NULL,
    PRIMARY KEY (airport_code),
    CONSTRAINT chk_airport_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_airport_longitude CHECK (longitude BETWEEN -180 AND 180)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS flights (
    flight_id VARCHAR(40) NOT NULL,
    origin CHAR(3) NOT NULL,
    destination CHAR(3) NOT NULL,
    departure_datetime DATETIME NULL,
    PRIMARY KEY (flight_id),
    CONSTRAINT fk_route_origin
        FOREIGN KEY (origin) REFERENCES airports (airport_code),
    CONSTRAINT fk_route_destination
        FOREIGN KEY (destination) REFERENCES airports (airport_code),
    INDEX idx_flight_origin_destination (origin, destination),
    INDEX idx_flight_destination (destination)
) ENGINE = InnoDB;

-- Import airport_coordinates.csv into airports using LOAD DATA LOCAL INFILE
-- before loading flights. For example:
-- LOAD DATA LOCAL INFILE
--   'C:\\Users\\DELL\\Documents\\flights\\data\\airports\\airport_coordinates.csv'
-- INTO TABLE airports
-- CHARACTER SET utf8mb4
-- FIELDS TERMINATED BY ','
-- OPTIONALLY ENCLOSED BY '"'
-- LINES TERMINATED BY '\r\n'
-- IGNORE 1 LINES
-- (airport_code, airport_name, city, country, latitude, longitude);
--
-- Import each *_flights.csv; map dep_airport -> origin and arr_airport -> destination.
-- LOAD DATA LOCAL INFILE 'C:\\path\\to\\CDG_flights.csv'
-- INTO TABLE flights
-- CHARACTER SET utf8mb4
-- FIELDS TERMINATED BY ','
-- OPTIONALLY ENCLOSED BY '"'
-- LINES TERMINATED BY '\r\n'
-- IGNORE 1 LINES
-- (@flight_id, @airport_code, @aircraft_id, @origin, @destination,
--  @departure_datetime, @arrival_datetime, @duration_hours)
-- SET flight_id = @flight_id,
--     origin = @origin,
--     destination = @destination,
--     departure_datetime = STR_TO_DATE(@departure_datetime, '%Y-%m-%d %H:%i:%s');

-- Join flights to origin and destination airport rows and create the four
-- coordinates required for route mapping.
CREATE OR REPLACE VIEW flight_route_coordinates AS
SELECT
    f.flight_id,
    f.origin,
    f.destination,
    f.departure_datetime,
    origin_airport.longitude AS origin_lon,
    origin_airport.latitude AS origin_lat,
    destination_airport.longitude AS dest_lon,
    destination_airport.latitude AS dest_lat
FROM flights AS f
JOIN airports AS origin_airport
    ON origin_airport.airport_code = f.origin
JOIN airports AS destination_airport
    ON destination_airport.airport_code = f.destination;

SELECT * FROM flight_route_coordinates;

-- Top 100 most frequently used directed routes, including all four coordinates.
SELECT
    origin,
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

-- The five most visited destinations, regardless of origin.
SELECT
    destination,
    COUNT(*) AS flight_count
FROM flights
GROUP BY destination
ORDER BY flight_count DESC, destination
LIMIT 5;

-- Top 100 routes whose two endpoints lie within the contiguous-U.S. bounds.
-- This does not include international routes to/from U.S. airports.
SELECT
    origin,
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
