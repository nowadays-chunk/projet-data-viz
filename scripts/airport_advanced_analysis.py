import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_flights(data_dir):
    flights = []
    csv_paths = sorted(data_dir.glob('*_flights.csv'))
    if not csv_paths:
        raise FileNotFoundError(f'No *_flights.csv files found in {data_dir}')

    required_fields = {
        'aircraft_id',
        'arr_airport',
        'dep_airport',
        'dep_date',
        'duration_hours',
    }

    for csv_path in csv_paths:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            missing_fields = required_fields - set(reader.fieldnames or [])
            if missing_fields:
                missing = ', '.join(sorted(missing_fields))
                raise ValueError(f'{csv_path} is missing required columns: {missing}')

            airport_code = csv_path.stem.replace('_flights', '').upper()
            for row in reader:
                flights.append({
                    'airport': airport_code,
                    'aircraft_id': row['aircraft_id'],
                    'arr_airport': row['arr_airport'],
                    'dep_airport': row['dep_airport'],
                    'dep_date': datetime.strptime(row['dep_date'], '%Y-%m-%d %H:%M:%S'),
                    'duration_hours': float(row['duration_hours']),
                })

    if not flights:
        raise ValueError(f'No flights found in {data_dir}')
    return flights


def month_range(start, end):
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append(f'{year:04d}-{month:02d}')
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return months


def plot_monthly_activity(flights, output_path):
    monthly_counts = defaultdict(Counter)
    for flight in flights:
        month = flight['dep_date'].strftime('%Y-%m')
        monthly_counts[flight['airport']][month] += 1

    months = month_range(
        min(flight['dep_date'] for flight in flights),
        max(flight['dep_date'] for flight in flights),
    )
    fig, ax = plt.subplots(figsize=(13, 6))
    for airport in sorted(monthly_counts):
        ax.plot(
            months,
            [monthly_counts[airport][month] for month in months],
            marker='o',
            markersize=3,
            label=airport,
        )
    ax.set(title='Monthly departures by airport', xlabel='Month', ylabel='Flights')
    ax.tick_params(axis='x', labelrotation=45)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(title='Airport')
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_duration_distribution(flights, output_path):
    durations = defaultdict(list)
    for flight in flights:
        durations[flight['airport']].append(flight['duration_hours'])

    airports = sorted(durations)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot(
        [durations[airport] for airport in airports],
        showmeans=True,
    )
    ax.set_xticks(range(1, len(airports) + 1), airports)
    ax.set(title='Flight duration distribution by airport', xlabel='Airport', ylabel='Duration (hours)')
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_top_routes(flights, output_path):
    route_counts = Counter(
        (flight['dep_airport'], flight['arr_airport']) for flight in flights
    )
    top_routes = route_counts.most_common(10)
    labels = [f'{origin} -> {destination}' for (origin, destination), _ in top_routes]
    counts = [count for _, count in top_routes]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels[::-1], counts[::-1], color='darkorange', edgecolor='black')
    ax.set(title='Top 10 routes', xlabel='Flights', ylabel='Route')
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_departure_heatmap(flights, output_path):
    counts = [[0] * 24 for _ in range(7)]
    for flight in flights:
        departure = flight['dep_date']
        counts[departure.weekday()][departure.hour] += 1

    fig, ax = plt.subplots(figsize=(13, 5))
    image = ax.imshow(counts, aspect='auto', cmap='YlOrRd', interpolation='nearest')
    ax.set(
        title='Departures by day of week and hour',
        xlabel='Hour of day',
        ylabel='Day of week',
        xticks=range(24),
        yticks=range(7),
        yticklabels=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    )
    fig.colorbar(image, ax=ax, label='Flights')
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_aircraft_utilization(flights, output_path):
    aircraft_counts = Counter(flight['aircraft_id'] for flight in flights)
    top_aircraft = aircraft_counts.most_common(15)
    labels = [aircraft for aircraft, _ in top_aircraft]
    counts = [count for _, count in top_aircraft]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(labels[::-1], counts[::-1], color='steelblue', edgecolor='black')
    ax.set(title='Flights per aircraft (top 15)', xlabel='Flights', ylabel='Aircraft')
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def write_summaries(flights, output_dir):
    durations_by_airport = defaultdict(list)
    route_counts = Counter()
    aircraft_counts = Counter()
    for flight in flights:
        durations_by_airport[flight['airport']].append(flight['duration_hours'])
        route_counts[(flight['dep_airport'], flight['arr_airport'])] += 1
        aircraft_counts[(flight['airport'], flight['aircraft_id'])] += 1

    duration_path = output_dir / 'airport_duration_summary.csv'
    with open(duration_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'airport_code',
            'flight_count',
            'mean_duration_hours',
            'median_duration_hours',
            'min_duration_hours',
            'max_duration_hours',
        ])
        for airport, durations in sorted(durations_by_airport.items()):
            writer.writerow([
                airport,
                len(durations),
                f'{mean(durations):.2f}',
                f'{median(durations):.2f}',
                f'{min(durations):.2f}',
                f'{max(durations):.2f}',
            ])

    route_path = output_dir / 'airport_route_summary.csv'
    with open(route_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['dep_airport', 'arr_airport', 'flight_count'])
        for (origin, destination), count in sorted(
            route_counts.items(), key=lambda item: (-item[1], item[0])
        ):
            writer.writerow([origin, destination, count])

    aircraft_path = output_dir / 'aircraft_utilization_summary.csv'
    with open(aircraft_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['airport_code', 'aircraft_id', 'flight_count'])
        for (airport, aircraft), count in sorted(
            aircraft_counts.items(), key=lambda item: (item[0][0], -item[1], item[0][1])
        ):
            writer.writerow([airport, aircraft, count])

    return duration_path, route_path, aircraft_path


def main():
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / 'data' / 'airports'
    chart_dir = base_dir / 'charts' / 'advanced_analysis'
    chart_dir.mkdir(parents=True, exist_ok=True)

    flights = load_flights(data_dir)
    chart_paths = {
        'Monthly activity': chart_dir / 'monthly_activity_by_airport.png',
        'Duration distribution': chart_dir / 'duration_distribution_by_airport.png',
        'Most popular routes': chart_dir / 'top_routes.png',
        'Departure schedule heatmap': chart_dir / 'departure_day_hour_heatmap.png',
        'Aircraft utilization': chart_dir / 'aircraft_utilization.png',
    }
    plot_monthly_activity(flights, chart_paths['Monthly activity'])
    plot_duration_distribution(flights, chart_paths['Duration distribution'])
    plot_top_routes(flights, chart_paths['Most popular routes'])
    plot_departure_heatmap(flights, chart_paths['Departure schedule heatmap'])
    plot_aircraft_utilization(flights, chart_paths['Aircraft utilization'])

    summary_paths = write_summaries(flights, base_dir / 'data')
    print(f'Flights analyzed: {len(flights)}')
    for label, path in chart_paths.items():
        print(f'{label}: {path}')
    for path in summary_paths:
        print(f'Summary: {path}')


if __name__ == '__main__':
    main()
