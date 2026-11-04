import csv
from collections import Counter
from datetime import datetime, time
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
SPECIAL_DAYS = {
    (1, 1): "New Year's Day",
    (7, 4): 'Independence Day',
    (11, 29): 'Thanksgiving Day (date specified: 29/11)',
    (12, 25): 'Christmas Day',
}
FILTERS = (
    'January 1',
    'November or December',
    'Special days',
    'Summer (July to September)',
    'Departure between 00:00 and 06:00 inclusive',
)


def load_flights(data_dir):
    flights = []
    csv_paths = sorted(data_dir.glob('*_flights.csv'))
    if not csv_paths:
        raise FileNotFoundError(f'No *_flights.csv files found in {data_dir}')

    required_fields = {'flight_id', 'dep_airport', 'arr_airport', 'dep_date'}
    for csv_path in csv_paths:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            missing_fields = required_fields - set(reader.fieldnames or [])
            if missing_fields:
                missing = ', '.join(sorted(missing_fields))
                raise ValueError(f'{csv_path} is missing required columns: {missing}')

            airport_code = csv_path.stem.removesuffix('_flights').upper()
            for row in reader:
                flights.append({
                    'flight_id': row['flight_id'],
                    'airport_code': airport_code,
                    'dep_airport': row['dep_airport'],
                    'arr_airport': row['arr_airport'],
                    'dep_date': datetime.strptime(row['dep_date'], DATE_FORMAT),
                })

    if not flights:
        raise ValueError(f'No flights found in {data_dir}')
    return flights


def matching_filters(flight):
    departure = flight['dep_date']
    matched = []
    if departure.month == 1 and departure.day == 1:
        matched.append('January 1')
    if departure.month in (11, 12):
        matched.append('November or December')
    if (departure.month, departure.day) in SPECIAL_DAYS:
        matched.append('Special days')
    if departure.month in (7, 8, 9):
        matched.append('Summer (July to September)')
    if time(0, 0) <= departure.time() <= time(6, 0):
        matched.append('Departure between 00:00 and 06:00 inclusive')
    return matched


def plot_filter_counts(filter_counts, airports, chart_dir):
    chart_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = []

    for filter_name in FILTERS:
        counts = [filter_counts[(filter_name, airport)] for airport in airports]
        total = filter_counts[(filter_name, 'ALL')]

        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.bar(airports, counts, color='steelblue', edgecolor='black')
        ax.bar_label(bars, padding=3)
        ax.set(
            title=f'{filter_name} — {total} flights',
            xlabel='Departure airport',
            ylabel='Number of flights',
        )
        ax.set_ylim(0, max(counts, default=0) * 1.15 + 1)
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        fig.tight_layout()

        filename = ''.join(
            character.lower() if character.isalnum() else '_'
            for character in filter_name
        ).strip('_')
        chart_path = chart_dir / f'{filename}.png'
        fig.savefig(chart_path)
        plt.close(fig)
        chart_paths.append(chart_path)

    return chart_paths


def plot_daily_departures(daily_counts, chart_dir):
    chart_dir.mkdir(parents=True, exist_ok=True)
    dates = sorted(daily_counts)
    counts = [daily_counts[departure_date] for departure_date in dates]

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(dates, counts, color='darkorange', linewidth=1, marker='o', markersize=3)
    ax.set(
        title='Flights per departure date',
        xlabel='Departure date',
        ylabel='Number of flights',
    )
    ax.grid(True, linestyle='--', alpha=0.4)
    fig.autofmt_xdate()
    fig.tight_layout()
    chart_path = chart_dir / 'daily_departures.png'
    fig.savefig(chart_path)
    plt.close(fig)
    return chart_path


def write_results(flights, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)

    filter_counts = Counter()
    airport_counts = Counter()
    daily_counts = Counter()
    filtered_flights = []

    for flight in flights:
        departure = flight['dep_date']
        daily_counts[departure.date()] += 1
        matched = matching_filters(flight)
        if matched:
            filtered_flights.append((flight, matched))
            for filter_name in matched:
                filter_counts[(filter_name, 'ALL')] += 1
                filter_counts[(filter_name, flight['airport_code'])] += 1

    summary_path = output_dir / 'flight_filter_summary.csv'
    with open(summary_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['filter', 'airport_code', 'flight_count'])
        for (filter_name, airport), count in sorted(filter_counts.items()):
            writer.writerow([filter_name, airport, count])
        for filter_name in FILTERS:
            if (filter_name, 'ALL') not in filter_counts:
                writer.writerow([filter_name, 'ALL', 0])

    daily_path = output_dir / 'daily_departure_counts.csv'
    with open(daily_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['departure_date', 'flight_count'])
        for departure_date, count in sorted(daily_counts.items()):
            writer.writerow([departure_date.isoformat(), count])

    filtered_path = output_dir / 'filtered_flights.csv'
    with open(filtered_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'flight_id',
            'airport_code',
            'dep_airport',
            'arr_airport',
            'dep_date',
            'matching_filters',
        ])
        for flight, matched in sorted(
            filtered_flights, key=lambda item: item[0]['dep_date']
        ):
            writer.writerow([
                flight['flight_id'],
                flight['airport_code'],
                flight['dep_airport'],
                flight['arr_airport'],
                flight['dep_date'].strftime(DATE_FORMAT),
                '; '.join(matched),
            ])

    return filter_counts, daily_counts, (summary_path, daily_path, filtered_path)


def main():
    base_dir = Path(__file__).resolve().parents[1]
    flights = load_flights(base_dir / 'data' / 'airports')
    filter_counts, daily_counts, output_paths = write_results(
        flights, base_dir / 'data' / 'date_filter_analysis'
    )
    chart_dir = base_dir / 'data' / 'date_filter_analysis' / 'charts'
    chart_paths = plot_filter_counts(
        filter_counts,
        sorted({flight['airport_code'] for flight in flights}),
        chart_dir,
    )
    chart_paths.append(plot_daily_departures(daily_counts, chart_dir))

    print(f'Flights analyzed: {len(flights)}')
    print(f'Departure dates with flights: {len(daily_counts)}')
    for filter_name in FILTERS:
        print(f'{filter_name}: {filter_counts[(filter_name, "ALL")]} flights')
    print('Special dates use the month/day values given in the request,')
    print('including November 29 for Thanksgiving Day.')
    print('The early-departure filter includes times through exactly 06:00.')
    for path in output_paths:
        print(f'Results saved: {path}')
    for path in chart_paths:
        print(f'Chart saved: {path}')


if __name__ == '__main__':
    main()
