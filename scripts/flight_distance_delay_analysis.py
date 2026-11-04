import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
OUTLIER_DESTINATION = 'HNL'
SHORT_FLIGHT_MAX_MILES = 1000
MEDIUM_FLIGHT_MAX_MILES = 3000
MINUTES_PER_HOUR = 60


def _column(fieldnames, *candidates):
    names = set(fieldnames or [])
    return next((candidate for candidate in candidates if candidate in names), None)


def _resolve_columns(fieldnames, file_path):
    columns = {
        'flight_id': _column(fieldnames, 'flight_id'),
        'airline': _column(fieldnames, 'airline_code', 'airline', 'carrier', 'company'),
        'departure_airport': _column(fieldnames, 'dep_airport', 'departure_airport_code'),
        'destination': _column(fieldnames, 'arr_airport', 'arrival_airport_code'),
        'departure_time': _column(
            fieldnames, 'dep_actual', 'dep_date', 'actual_dep_date',
            'departure_actual',
        ),
        'departure_delay': _column(fieldnames, 'dep_delay_minutes', 'dep_delay'),
        'arrival_delay': _column(fieldnames, 'arr_delay_minutes', 'arr_delay'),
        'distance': _column(fieldnames, 'distance_miles', 'distance'),
    }

    if columns['departure_delay'] is None:
        columns['departure_scheduled'] = _column(
            fieldnames, 'dep_scheduled', 'scheduled_dep_date',
            'departure_scheduled',
        )
    if columns['arrival_delay'] is None:
        columns['arrival_scheduled'] = _column(
            fieldnames, 'arr_scheduled', 'scheduled_arr_date',
            'arrival_scheduled',
        )
        columns['arrival_actual'] = _column(
            fieldnames, 'arr_actual', 'arr_date', 'actual_arr_date',
            'arrival_actual',
        )

    missing = [
        label for key, label in (
            ('flight_id', 'flight_id'),
            ('airline', 'airline_code (or airline/carrier/company)'),
            ('departure_airport', 'dep_airport'),
            ('destination', 'arr_airport (destination)'),
            ('departure_time', 'dep_date (actual departure datetime)'),
            ('distance', 'distance_miles'),
        )
        if columns[key] is None
    ]
    for delay_key, scheduled_key, actual_key, label in (
        (
            'departure_delay',
            'departure_scheduled',
            'departure_time',
            'dep_delay_minutes OR dep_scheduled + dep_date',
        ),
        (
            'arrival_delay',
            'arrival_scheduled',
            'arrival_actual',
            'arr_delay_minutes OR arr_scheduled + arr_date',
        ),
    ):
        if columns[delay_key] is None and (
            columns.get(scheduled_key) is None or columns.get(actual_key) is None
        ):
            missing.append(label)

    if missing:
        raise ValueError(
            f'{file_path} is missing required data: {", ".join(missing)}. '
            'The existing project CSVs contain no airline, delay, or distance '
            'columns. Add the enriched fields described in '
            'sql/flight_distance_delay_analysis_mysql8.sql.'
        )
    return columns


def _get_delay(row, columns, delay_key, scheduled_key, actual_key):
    delay_column = columns[delay_key]
    if delay_column is not None:
        return float(row[delay_column])
    scheduled = datetime.strptime(row[columns[scheduled_key]], DATE_FORMAT)
    actual = datetime.strptime(row[columns[actual_key]], DATE_FORMAT)
    return (actual - scheduled).total_seconds() / MINUTES_PER_HOUR


def load_flights(data_dir):
    csv_paths = sorted(data_dir.glob('*_flights.csv'))
    if not csv_paths:
        raise FileNotFoundError(f'No *_flights.csv files found in {data_dir}')

    flights = []
    for csv_path in csv_paths:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            columns = _resolve_columns(reader.fieldnames, csv_path)
            for row in reader:
                flight = {
                    'flight_id': row[columns['flight_id']],
                    'airline_code': row[columns['airline']].strip().upper(),
                    'departure_airport': row[columns['departure_airport']].strip().upper(),
                    'destination': row[columns['destination']].strip().upper(),
                    'departure_datetime': datetime.strptime(
                        row[columns['departure_time']], DATE_FORMAT
                    ),
                    'dep_delay_minutes': _get_delay(
                        row,
                        columns,
                        'departure_delay',
                        'departure_scheduled',
                        'departure_time',
                    ),
                    'arr_delay_minutes': _get_delay(
                        row,
                        columns,
                        'arrival_delay',
                        'arrival_scheduled',
                        'arrival_actual',
                    ),
                    'distance_miles': float(row[columns['distance']]),
                }
                if flight['distance_miles'] < 0:
                    raise ValueError(
                        f'{csv_path}: flight {flight["flight_id"]} has '
                        'distance_miles < 0'
                    )
                flights.append(flight)

    if not flights:
        raise ValueError(f'No flights found in {data_dir}')
    return flights


def destination_statistics(flights):
    groups = defaultdict(list)
    for flight in flights:
        groups[flight['destination']].append(flight)

    rows = []
    for destination, group in sorted(groups.items()):
        distances = [flight['distance_miles'] for flight in group]
        mean_distance = mean(distances)
        if mean_distance < SHORT_FLIGHT_MAX_MILES:
            distance_band = 'Short (<1000 miles)'
        elif mean_distance < MEDIUM_FLIGHT_MAX_MILES:
            distance_band = 'Medium (1000-2999 miles)'
        else:
            distance_band = 'Long (>=3000 miles)'
        rows.append({
            'destination': destination,
            'flight_count': len(group),
            'distinct_distance_count': len(set(distances)),
            'mean_distance_miles': mean_distance,
            'min_distance_miles': min(distances),
            'max_distance_miles': max(distances),
            'mean_arr_delay_minutes': mean(
                flight['arr_delay_minutes'] for flight in group
            ),
            'mean_dep_delay_minutes': mean(
                flight['dep_delay_minutes'] for flight in group
            ),
            'arrival_delay_over_15_count': sum(
                flight['arr_delay_minutes'] > 15 for flight in group
            ),
            'arrival_delay_over_15_percent': 100 * sum(
                flight['arr_delay_minutes'] > 15 for flight in group
            ) / len(group),
            'distance_band': distance_band,
        })
    return rows


def descriptive_statistics(values):
    ordered = sorted(values)
    count = len(ordered)
    return {
        'count': count,
        'mean': mean(ordered),
        'median': median(ordered),
        'std_dev_sample': stdev(ordered) if count > 1 else 0.0,
        'min': ordered[0],
        'q1': ordered[(count - 1) // 4],
        'q3': ordered[(3 * (count - 1)) // 4],
        'max': ordered[-1],
    }


def pearson_correlation(x_values, y_values):
    if len(x_values) < 2:
        return None
    x_mean = mean(x_values)
    y_mean = mean(y_values)
    x_deviations = [value - x_mean for value in x_values]
    y_deviations = [value - y_mean for value in y_values]
    denominator = math.sqrt(
        sum(value ** 2 for value in x_deviations)
        * sum(value ** 2 for value in y_deviations)
    )
    if denominator == 0:
        return None
    return sum(
        x_delta * y_delta
        for x_delta, y_delta in zip(x_deviations, y_deviations)
    ) / denominator


def _write_csv(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _plot_destination_distance(rows, chart_path):
    included = [
        row for row in rows if row['destination'] != OUTLIER_DESTINATION
    ]
    fig, ax = plt.subplots(figsize=(11, 6))
    if included:
        x_values = [row['mean_distance_miles'] for row in included]
        y_values = [row['mean_arr_delay_minutes'] for row in included]
        sizes = [max(35, row['flight_count'] * 8) for row in included]
        ax.scatter(
            x_values,
            y_values,
            s=sizes,
            alpha=0.75,
            edgecolors='black',
        )
        for row in included:
            ax.annotate(
                row['destination'],
                (row['mean_distance_miles'], row['mean_arr_delay_minutes']),
                xytext=(5, 5),
                textcoords='offset points',
            )
        correlation = pearson_correlation(x_values, y_values)
        correlation_label = (
            f'Pearson r = {correlation:.3f}'
            if correlation is not None
            else 'Pearson r unavailable'
        )
        ax.text(
            0.02,
            0.98,
            f'{correlation_label}; HNL excluded',
            transform=ax.transAxes,
            va='top',
        )
    else:
        ax.text(0.5, 0.5, 'No destinations available after excluding HNL',
                ha='center', va='center', transform=ax.transAxes)
    ax.set(
        title='Mean arrival delay vs mean destination distance',
        xlabel='Mean distance to destination (miles)',
        ylabel='Mean arrival delay (minutes)',
    )
    ax.axhline(0, color='gray', linewidth=0.8, linestyle='--')
    ax.grid(True, linestyle='--', alpha=0.35)
    fig.tight_layout()
    fig.savefig(chart_path)
    plt.close(fig)


def _plot_delay_distributions(flights, chart_path):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.boxplot(
        [
            [flight['dep_delay_minutes'] for flight in flights],
            [flight['arr_delay_minutes'] for flight in flights],
        ],
        showmeans=True,
    )
    ax.set_xticks([1, 2], ['Departure delay', 'Arrival delay'])
    ax.set(title='Departure and arrival delay distributions', ylabel='Delay (minutes)')
    ax.axhline(0, color='gray', linewidth=0.8, linestyle='--')
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    fig.tight_layout()
    fig.savefig(chart_path)
    plt.close(fig)


def _plot_airline_destination_delays(flights, chart_path):
    groups = defaultdict(list)
    for flight in flights:
        groups[(flight['airline_code'], flight['destination'])].append(
            flight['arr_delay_minutes']
        )
    ranked = sorted(
        groups.items(),
        key=lambda item: mean(item[1]),
        reverse=True,
    )[:15]
    fig, ax = plt.subplots(figsize=(11, max(5, len(ranked) * 0.4)))
    if ranked:
        labels = [
            f'{airline} -> {destination} (n={len(delays)})'
            for (airline, destination), delays in reversed(ranked)
        ]
        averages = [mean(delays) for _, delays in reversed(ranked)]
        bars = ax.barh(labels, averages, color='indianred', edgecolor='black')
        ax.bar_label(bars, fmt='%.1f', padding=3)
        ax.set_xlim(min(0, min(averages)) * 1.15, max(0, max(averages)) * 1.2 + 1)
    else:
        ax.text(0.5, 0.5, 'No airline/destination groups found',
                ha='center', va='center', transform=ax.transAxes)
    ax.set(
        title='Destinations and airlines with highest mean arrival delay (top 15)',
        xlabel='Mean arrival delay (minutes)',
        ylabel='Airline -> destination',
    )
    ax.axvline(0, color='gray', linewidth=0.8)
    ax.grid(axis='x', linestyle='--', alpha=0.35)
    fig.tight_layout()
    fig.savefig(chart_path)
    plt.close(fig)


def _plot_delay_by_departure_hour(flights, chart_path):
    hourly = defaultdict(list)
    for flight in flights:
        hourly[flight['departure_datetime'].hour].append(
            flight['arr_delay_minutes']
        )
    hours = sorted(hourly)
    averages = [mean(hourly[hour]) for hour in hours]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hours, averages, marker='o', color='darkorange')
    ax.set(
        title='Mean arrival delay by scheduled/actual departure hour',
        xlabel='Departure hour',
        ylabel='Mean arrival delay (minutes)',
        xticks=range(24),
    )
    ax.axhline(0, color='gray', linewidth=0.8, linestyle='--')
    ax.grid(True, linestyle='--', alpha=0.35)
    fig.tight_layout()
    fig.savefig(chart_path)
    plt.close(fig)


def analyze(flights, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    destination_rows = destination_statistics(flights)

    destination_fields = [
        'destination',
        'flight_count',
        'distinct_distance_count',
        'mean_distance_miles',
        'min_distance_miles',
        'max_distance_miles',
        'mean_arr_delay_minutes',
        'mean_dep_delay_minutes',
        'arrival_delay_over_15_count',
        'arrival_delay_over_15_percent',
        'distance_band',
    ]
    formatted_destination_rows = [
        {
            **row,
            'mean_distance_miles': round(row['mean_distance_miles'], 2),
            'min_distance_miles': round(row['min_distance_miles'], 2),
            'max_distance_miles': round(row['max_distance_miles'], 2),
            'mean_arr_delay_minutes': round(row['mean_arr_delay_minutes'], 2),
            'mean_dep_delay_minutes': round(row['mean_dep_delay_minutes'], 2),
            'arrival_delay_over_15_percent': round(
                row['arrival_delay_over_15_percent'], 2
            ),
        }
        for row in destination_rows
    ]
    _write_csv(
        output_dir / 'destination_delay_distance_summary.csv',
        destination_fields,
        formatted_destination_rows,
    )

    carrier_groups = defaultdict(list)
    for flight in flights:
        carrier_groups[(flight['airline_code'], flight['destination'])].append(flight)
    carrier_rows = []
    for (airline, destination), group in carrier_groups.items():
        delayed = sum(flight['arr_delay_minutes'] > 15 for flight in group)
        carrier_rows.append({
            'airline_code': airline,
            'destination': destination,
            'flight_count': len(group),
            'mean_arr_delay_minutes': round(
                mean(flight['arr_delay_minutes'] for flight in group), 2
            ),
            'arrivals_over_15_minutes_late': delayed,
            'arrival_delay_over_15_percent': round(
                100 * delayed / len(group), 2
            ),
        })
    carrier_rows.sort(
        key=lambda row: (
            -row['mean_arr_delay_minutes'],
            -row['arrival_delay_over_15_percent'],
            -row['flight_count'],
        )
    )
    _write_csv(
        output_dir / 'airline_destination_delay_summary.csv',
        [
            'airline_code',
            'destination',
            'flight_count',
            'mean_arr_delay_minutes',
            'arrivals_over_15_minutes_late',
            'arrival_delay_over_15_percent',
        ],
        carrier_rows,
    )

    descriptive_rows = []
    for variable, key in (
        ('arr_delay_minutes', 'arr_delay_minutes'),
        ('dep_delay_minutes', 'dep_delay_minutes'),
    ):
        stats = descriptive_statistics([flight[key] for flight in flights])
        descriptive_rows.append({
            'variable': variable,
            **{name: round(value, 2) for name, value in stats.items()},
        })
    _write_csv(
        output_dir / 'delay_descriptive_statistics.csv',
        ['variable', 'count', 'mean', 'median', 'std_dev_sample',
         'min', 'q1', 'q3', 'max'],
        descriptive_rows,
    )

    airport_groups = defaultdict(list)
    for flight in flights:
        airport_groups[flight['departure_airport']].append(
            flight['arr_delay_minutes']
        )
    airport_rows = [
        {
            'departure_airport': airport,
            'flight_count': len(delays),
            'mean_arr_delay_minutes': round(mean(delays), 2),
        }
        for airport, delays in airport_groups.items()
    ]
    airport_rows.sort(
        key=lambda row: (row['mean_arr_delay_minutes'], row['departure_airport'])
    )
    _write_csv(
        output_dir / 'arrival_delay_by_departure_airport.csv',
        ['departure_airport', 'flight_count', 'mean_arr_delay_minutes'],
        airport_rows,
    )

    hourly_groups = defaultdict(list)
    for flight in flights:
        hourly_groups[flight['departure_datetime'].hour].append(
            flight['arr_delay_minutes']
        )
    hourly_rows = [
        {
            'departure_hour': hour,
            'flight_count': len(delays),
            'mean_arr_delay_minutes': round(mean(delays), 2),
        }
        for hour, delays in sorted(hourly_groups.items())
    ]
    _write_csv(
        output_dir / 'arrival_delay_by_departure_hour.csv',
        ['departure_hour', 'flight_count', 'mean_arr_delay_minutes'],
        hourly_rows,
    )
    hourly_correlation = pearson_correlation(
        [flight['departure_datetime'].hour for flight in flights],
        [flight['arr_delay_minutes'] for flight in flights],
    )

    chart_paths = [
        output_dir / 'distance_vs_mean_arrival_delay_without_hnl.png',
        output_dir / 'departure_arrival_delay_distributions.png',
        output_dir / 'airline_destination_mean_arrival_delay.png',
        output_dir / 'arrival_delay_by_departure_hour.png',
    ]
    _plot_destination_distance(destination_rows, chart_paths[0])
    _plot_delay_distributions(flights, chart_paths[1])
    _plot_airline_destination_delays(flights, chart_paths[2])
    _plot_delay_by_departure_hour(flights, chart_paths[3])

    hnl_present = any(row['destination'] == OUTLIER_DESTINATION
                      for row in destination_rows)
    hnl_row = next(
        (row for row in destination_rows
         if row['destination'] == OUTLIER_DESTINATION),
        None,
    )
    second_farthest = max(
        (
            row['mean_distance_miles'] for row in destination_rows
            if row['destination'] != OUTLIER_DESTINATION
        ),
        default=None,
    )
    included = [
        row for row in destination_rows
        if row['destination'] != OUTLIER_DESTINATION
    ]
    correlation = pearson_correlation(
        [row['mean_distance_miles'] for row in included],
        [row['mean_arr_delay_minutes'] for row in included],
    )
    report = {
        'destination_count': len(destination_rows),
        'hnl_present': hnl_present,
        'hnl_to_second_farthest_distance_ratio': (
            round(hnl_row['mean_distance_miles'] / second_farthest, 3)
            if hnl_row and second_farthest else None
        ),
        'distance_delay_pearson_r_without_hnl': (
            round(correlation, 4) if correlation is not None else None
        ),
        'departure_hour_arrival_delay_pearson_r': (
            round(hourly_correlation, 4) if hourly_correlation is not None else None
        ),
        'lowest_mean_arrival_delay_departure_airport': (
            airport_rows[0] if airport_rows else None
        ),
        'highest_mean_arrival_delay_destination': (
            max(destination_rows, key=lambda row: row['mean_arr_delay_minutes'])
            if destination_rows else None
        ),
    }
    return report, chart_paths


def main():
    base_dir = Path(__file__).resolve().parents[1]
    flights = load_flights(base_dir / 'data' / 'airports')
    report, chart_paths = analyze(
        flights, base_dir / 'data' / 'flight_distance_delay_analysis'
    )

    print(f'Flights analyzed: {len(flights)}')
    print(f'Destinations analyzed: {report["destination_count"]}')
    print(f'HNL present: {report["hnl_present"]}')
    if not report['hnl_present']:
        print('HNL outlier exclusion was requested, but HNL is absent from the data.')
    elif report['hnl_to_second_farthest_distance_ratio'] is not None:
        print(
            'HNL / second-farthest destination mean-distance ratio: '
            f'{report["hnl_to_second_farthest_distance_ratio"]}'
        )
    print('Pearson correlation (mean distance vs mean arrival delay, excluding HNL): '
          f'{report["distance_delay_pearson_r_without_hnl"]}')
    print('Pearson correlation (departure hour vs arrival delay): '
          f'{report["departure_hour_arrival_delay_pearson_r"]}')
    airport = report['lowest_mean_arrival_delay_departure_airport']
    if airport:
        print(
            'Lowest mean arrival delay by departure airport: '
            f'{airport["departure_airport"]} '
            f'({airport["mean_arr_delay_minutes"]} minutes; '
            f'{airport["flight_count"]} flights)'
        )
    for path in chart_paths:
        print(f'Chart saved: {path}')
    print(f'CSV results saved in: {base_dir / "data" / "flight_distance_delay_analysis"}')


if __name__ == '__main__':
    main()
