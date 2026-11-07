"""Analyse chronologique globale des vols.

Ce script lit les fichiers de chaque aéroport, ordonne les vols par date de
voyage, puis produit un diagramme de suivi temporel et un histogramme de densité
mensuelle pour l'ensemble du réseau.
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_airport_flights(data_dir):
    flights = []
    for csv_path in sorted(data_dir.glob('*_flights.csv')):
        with open(csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                dep_dt = datetime.strptime(row['dep_date'], '%Y-%m-%d %H:%M:%S')
                arr_dt = datetime.strptime(row['arr_date'], '%Y-%m-%d %H:%M:%S')
                duration_hours = float(row['duration_hours'])
                flights.append({
                    'airport': csv_path.stem.replace('_flights', '').upper(),
                    'flight_id': row['flight_id'],
                    'aircraft_id': row['aircraft_id'],
                    'dep_airport': row['dep_airport'],
                    'arr_airport': row['arr_airport'],
                    'dep_date': dep_dt,
                    'arr_date': arr_dt,
                    'duration_hours': duration_hours,
                })
    return sorted(flights, key=lambda f: f['dep_date'])


def aggregate_by_month(flights):
    month_counts = defaultdict(int)
    for flight in flights:
        month_key = flight['dep_date'].strftime('%Y-%m')
        month_counts[month_key] += 1
    return sorted(month_counts.items())


def plot_timeline(flights, output_path):
    dates = [flight['dep_date'] for flight in flights]
    durations = [flight['duration_hours'] for flight in flights]

    plt.figure(figsize=(12, 6))
    plt.plot(dates, durations, color='royalblue', marker='o', markersize=3, linewidth=1.5)
    plt.title('Chronological flight durations by departure date')
    plt.xlabel('Departure date')
    plt.ylabel('Duration (hours)')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


if __name__ == '__main__':
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / 'data' / 'airports'
    flights = load_airport_flights(data_dir)

    timeline_path = base_dir / 'data' / 'airport_flight_timeline.png'
    plot_timeline(flights, timeline_path)

    month_counts = aggregate_by_month(flights)
    month_density_path = base_dir / 'data' / 'airport_flight_density_by_month.png'

    plt.figure(figsize=(12, 6))
    months = [entry[0] for entry in month_counts]
    month_values = [entry[1] for entry in month_counts]
    plt.bar(months, month_values, color='forestgreen', edgecolor='black')
    plt.title('Flight density by month')
    plt.xlabel('Month')
    plt.ylabel('Number of departures')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(month_density_path)
    plt.close()

    print(f'Flights loaded: {len(flights)}')
    print(f'Timeline saved: {timeline_path}')
    print(f'Month density saved: {month_density_path}')
