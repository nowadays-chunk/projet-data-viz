"""Comparaison de la fréquentation par aéroport.

Le script charge les données de vols de tous les aéroports, construit des
chronologies de trafic avec leurs densités par date et par mois, puis génère
un résumé de comptage dans data/ ainsi que les graphiques dans charts/airports/.
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_flights(data_dir):
    airport_data = defaultdict(list)

    for csv_path in sorted(data_dir.glob('*_flights.csv')):
        airport_code = csv_path.stem.replace('_flights', '').upper()
        with open(csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                dep_dt = datetime.strptime(row['dep_date'], '%Y-%m-%d %H:%M:%S')
                arr_dt = datetime.strptime(row['arr_date'], '%Y-%m-%d %H:%M:%S')
                duration_hours = float(row['duration_hours'])
                airport_data[airport_code].append({
                    'flight_id': row['flight_id'],
                    'dep_date': dep_dt,
                    'arr_date': arr_dt,
                    'duration_hours': duration_hours,
                    'dep_airport': row['dep_airport'],
                    'arr_airport': row['arr_airport'],
                })

    return airport_data


def build_airport_plots(airport_code, flights, output_root):
    airport_dir = output_root / airport_code
    airport_dir.mkdir(parents=True, exist_ok=True)

    sorted_flights = sorted(flights, key=lambda x: x['dep_date'])
    dates = [f['dep_date'] for f in sorted_flights]
    durations = [f['duration_hours'] for f in sorted_flights]

    plt.figure(figsize=(12, 6))
    plt.plot(dates, durations, color='royalblue', marker='o', markersize=3, linewidth=1.5)
    plt.title(f'{airport_code} - Flight durations by departure date')
    plt.xlabel('Departure date')
    plt.ylabel('Duration (hours)')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(airport_dir / f'{airport_code}_timeline.png')
    plt.close()

    date_counts = defaultdict(int)
    month_counts = defaultdict(int)
    for flight in sorted_flights:
        date_counts[flight['dep_date'].strftime('%Y-%m-%d')] += 1
        month_counts[flight['dep_date'].strftime('%Y-%m')] += 1

    date_labels = sorted(date_counts.keys())
    date_values = [date_counts[d] for d in date_labels]
    plt.figure(figsize=(12, 6))
    plt.bar(date_labels, date_values, color='darkorange', edgecolor='black')
    plt.title(f'{airport_code} - Flight density by date')
    plt.xlabel('Date')
    plt.ylabel('Flights')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(airport_dir / f'{airport_code}_density_by_date.png')
    plt.close()

    month_labels = sorted(month_counts.keys())
    month_values = [month_counts[m] for m in month_labels]
    plt.figure(figsize=(12, 6))
    plt.bar(month_labels, month_values, color='forestgreen', edgecolor='black')
    plt.title(f'{airport_code} - Flight density by month')
    plt.xlabel('Month')
    plt.ylabel('Flights')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(airport_dir / f'{airport_code}_density_by_month.png')
    plt.close()

    return len(sorted_flights)


if __name__ == '__main__':
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / 'data' / 'airports'
    output_dir = base_dir / 'charts' / 'airports'
    output_dir.mkdir(parents=True, exist_ok=True)

    airport_data = load_flights(data_dir)
    traffic_summary = {}

    for airport_code, flights in airport_data.items():
        traffic_summary[airport_code] = build_airport_plots(airport_code, flights, output_dir)

    print('Traffic by airport:')
    for airport_code, count in sorted(traffic_summary.items(), key=lambda item: item[1], reverse=True):
        print(f'{airport_code}: {count} flights')

    max_airport = max(traffic_summary, key=traffic_summary.get)
    min_airport = min(traffic_summary, key=traffic_summary.get)

    print(f'\nMost active airport: {max_airport} ({traffic_summary[max_airport]} flights)')
    print(f'Least active airport: {min_airport} ({traffic_summary[min_airport]} flights)')

    summary_path = base_dir / 'data' / 'airport_traffic_summary.csv'
    with open(summary_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['airport_code', 'flight_count'])
        for airport_code, count in sorted(traffic_summary.items()):
            writer.writerow([airport_code, count])

    print(f'\nSummary saved to: {summary_path}')
    print(f'Charts saved in: {output_dir}')
