"""Générateur de données de vols synthétiques.

Le script produit des fichiers CSV de vols pour plusieurs aéroports, avec des
horaires, durées, identifiants d'avion et routes simulées. Les fichiers ainsi
créés servent ensuite aux analyses de trafic et de performance.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / 'data'
AIRPORTS_DIR = DATA_DIR / 'airports'
AIRPORTS_DIR.mkdir(parents=True, exist_ok=True)

AIRPORTS = {
    'CDG': {
        'city': 'Paris',
        'aircraft': ['CDG-A01', 'CDG-A02', 'CDG-A03', 'CDG-A04'],
        'partners': ['JFK', 'DXB', 'LHR', 'SIN', 'MAD']
    },
    'JFK': {
        'city': 'New York',
        'aircraft': ['JFK-B01', 'JFK-B02', 'JFK-B03', 'JFK-B04'],
        'partners': ['CDG', 'DXB', 'LHR', 'SIN', 'MIA']
    },
    'DXB': {
        'city': 'Dubai',
        'aircraft': ['DXB-C01', 'DXB-C02', 'DXB-C03', 'DXB-C04'],
        'partners': ['CDG', 'JFK', 'SIN', 'LHR', 'BKK']
    },
    'LHR': {
        'city': 'London',
        'aircraft': ['LHR-D01', 'LHR-D02', 'LHR-D03', 'LHR-D04'],
        'partners': ['CDG', 'JFK', 'DXB', 'SIN', 'AMS']
    },
    'SIN': {
        'city': 'Singapore',
        'aircraft': ['SIN-E01', 'SIN-E02', 'SIN-E03', 'SIN-E04'],
        'partners': ['CDG', 'JFK', 'DXB', 'LHR', 'BKK']
    }
}

START_DATE = datetime(2024, 1, 1, 0, 0, 0)
END_DATE = datetime(2026, 12, 31, 23, 59, 59)


def random_datetime(start_date, end_date):
    delta_seconds = int((end_date - start_date).total_seconds())
    seconds = random.randint(0, max(delta_seconds, 0))
    return start_date + timedelta(seconds=seconds)


def generate_airport_file(airport_code, rows_per_airport=50):
    airport = AIRPORTS[airport_code]
    aircrafts = airport['aircraft']
    flights = []

    for index in range(1, rows_per_airport + 1):
        aircraft_id = random.choice(aircrafts)
        dep_airport = airport_code
        arr_airport = random.choice(airport['partners'])
        dep_dt = random_datetime(START_DATE, END_DATE)
        duration_hours = round(random.uniform(1.5, 15.0), 2)
        arr_dt = dep_dt + timedelta(hours=duration_hours)

        flights.append({
            'flight_id': f'{airport_code}-{aircraft_id}-{index:03d}',
            'airport_code': airport_code,
            'aircraft_id': aircraft_id,
            'dep_airport': dep_airport,
            'arr_airport': arr_airport,
            'dep_date': dep_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'arr_date': arr_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_hours': duration_hours,
        })

    file_name = AIRPORTS_DIR / f'{airport_code}_flights.csv'
    with open(file_name, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            'flight_id',
            'airport_code',
            'aircraft_id',
            'dep_airport',
            'arr_airport',
            'dep_date',
            'arr_date',
            'duration_hours'
        ])
        writer.writeheader()
        writer.writerows(flights)

    print(f'Generated {len(flights)} rows in {file_name.name}')


if __name__ == '__main__':
    traffic_summary = {}
    for airport_code in AIRPORTS:
        rows_per_airport = random.randint(20, 80)
        traffic_summary[airport_code] = rows_per_airport
        generate_airport_file(airport_code, rows_per_airport=rows_per_airport)

    summary_path = AIRPORTS_DIR / 'airport_summary.csv'
    with open(summary_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['airport_code', 'city', 'aircraft_count', 'flight_rows'])
        for airport_code, info in AIRPORTS.items():
            writer.writerow([airport_code, info['city'], len(info['aircraft']), traffic_summary[airport_code]])

    print(f'Summary created in {summary_path.name}')
    print('Traffic summary:', traffic_summary)
