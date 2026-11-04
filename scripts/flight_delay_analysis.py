import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
ARRIVAL_DELAY_THRESHOLD_MINUTES = 15
MINUTES_PER_HOUR = 60


def _column(fieldnames, *candidates):
    fieldnames = set(fieldnames or [])
    return next((name for name in candidates if name in fieldnames), None)


def _resolve_columns(fieldnames, file_path):
    columns = {
        'flight_id': _column(fieldnames, 'flight_id'),
        'airline': _column(fieldnames, 'airline_code', 'airline', 'carrier', 'company'),
        'departure_airport': _column(fieldnames, 'dep_airport', 'departure_airport_code'),
        'arrival_airport': _column(fieldnames, 'arr_airport', 'arrival_airport_code'),
        'air_time': _column(fieldnames, 'air_time_minutes', 'air_time'),
        'distance': _column(fieldnames, 'distance_miles', 'distance'),
        'departure_actual': _column(
            fieldnames, 'dep_actual', 'dep_date', 'actual_dep_date',
            'departure_actual',
        ),
        'departure_delay': _column(fieldnames, 'dep_delay_minutes', 'dep_delay'),
        'arrival_delay': _column(fieldnames, 'arr_delay_minutes', 'arr_delay'),
    }

    if columns['departure_delay'] is None:
        columns['departure_scheduled'] = _column(
            fieldnames, 'dep_scheduled', 'scheduled_dep_date'
        )
    if columns['arrival_delay'] is None:
        columns['arrival_scheduled'] = _column(
            fieldnames, 'arr_scheduled', 'scheduled_arr_date'
        )
        columns['arrival_actual'] = _column(
            fieldnames, 'arr_actual', 'arr_date', 'actual_arr_date'
        )

    missing = [
        label for key, label in (
            ('flight_id', 'flight_id'),
            ('airline', 'airline_code (or airline/carrier/company)'),
            ('departure_airport', 'dep_airport'),
            ('arrival_airport', 'arr_airport'),
            ('air_time', 'air_time_minutes'),
            ('distance', 'distance_miles'),
            (
                'departure_actual',
                'dep_date (or dep_actual/departure_actual) for daily averages',
            ),
        )
        if columns[key] is None
    ]
    for delay_key, scheduled_key, actual_key, label in (
        (
            'departure_delay',
            'departure_scheduled',
            'departure_actual',
            'dep_delay_minutes OR dep_scheduled + dep_actual',
        ),
        (
            'arrival_delay',
            'arrival_scheduled',
            'arrival_actual',
            'arr_delay_minutes OR arr_scheduled + arr_actual',
        ),
    ):
        if columns[delay_key] is None and (
            columns.get(scheduled_key) is None or columns.get(actual_key) is None
        ):
            missing.append(label)

    if missing:
        raise ValueError(
            f'{file_path} is missing required data: {", ".join(missing)}. '
            'See sql/flight_delay_analysis_mysql8.sql for the expected schema. '
            'Current generated flight data does not contain airline, scheduled '
            'times, air time, or route distance.'
        )
    return columns


def _delay_minutes(row, columns, delay_key, scheduled_key, actual_key):
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
                    'dep_airport': row[columns['departure_airport']].strip().upper(),
                    'arr_airport': row[columns['arrival_airport']].strip().upper(),
                    'dep_date': row[columns['departure_actual']],
                    'dep_delay_minutes': _delay_minutes(
                        row,
                        columns,
                        'departure_delay',
                        'departure_scheduled',
                        'departure_actual',
                    ),
                    'arr_delay_minutes': _delay_minutes(
                        row,
                        columns,
                        'arrival_delay',
                        'arrival_scheduled',
                        'arrival_actual',
                    ),
                    'air_time_minutes': float(row[columns['air_time']]),
                    'distance_miles': float(row[columns['distance']]),
                }
                if flight['air_time_minutes'] <= 0:
                    raise ValueError(
                        f'{csv_path}: flight {flight["flight_id"]} has '
                        'air_time_minutes <= 0'
                    )
                if flight['distance_miles'] < 0:
                    raise ValueError(
                        f'{csv_path}: flight {flight["flight_id"]} has '
                        'distance_miles < 0'
                    )
                flights.append(flight)

    if not flights:
        raise ValueError(f'No flights found in {data_dir}')
    return flights


def add_derived_metrics(flight):
    gain_minutes = flight['arr_delay_minutes'] - flight['dep_delay_minutes']
    recovered_minutes = -gain_minutes
    air_time_hours = flight['air_time_minutes'] / MINUTES_PER_HOUR
    return {
        **flight,
        'gain_minutes': gain_minutes,
        'recovered_minutes': recovered_minutes,
        'gain_per_hour': gain_minutes / air_time_hours,
        'speed_mph': flight['distance_miles'] / air_time_hours,
    }


def _write_csv(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def analyze_flights(flights, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = [add_derived_metrics(flight) for flight in flights]

    by_arrival_delay = sorted(
        metrics, key=lambda flight: flight['arr_delay_minutes'], reverse=True
    )
    by_departure_delay = sorted(
        metrics, key=lambda flight: flight['dep_delay_minutes'], reverse=True
    )
    delayed_both = sorted(
        (
            flight for flight in metrics
            if flight['dep_delay_minutes'] > 0 and flight['arr_delay_minutes'] > 0
        ),
        key=lambda flight: (
            flight['dep_delay_minutes'] + flight['arr_delay_minutes']
        ),
        reverse=True,
    )

    metric_fields = [
        'flight_id',
        'airline_code',
        'dep_airport',
        'arr_airport',
        'dep_date',
        'dep_delay_minutes',
        'arr_delay_minutes',
        'air_time_minutes',
        'distance_miles',
        'gain_minutes',
        'recovered_minutes',
        'gain_per_hour',
        'speed_mph',
    ]
    _write_csv(
        output_dir / 'flights_ranked_by_arrival_delay.csv',
        metric_fields,
        by_arrival_delay,
    )
    _write_csv(
        output_dir / 'flights_ranked_by_departure_delay.csv',
        metric_fields,
        by_departure_delay,
    )
    _write_csv(
        output_dir / 'flights_delayed_at_departure_and_arrival.csv',
        metric_fields,
        delayed_both,
    )

    daily_delays = defaultdict(list)
    reliability = defaultdict(list)
    for flight in metrics:
        if 'dep_date' in flight:
            day = datetime.strptime(flight['dep_date'], DATE_FORMAT).date()
            daily_delays[day].append(flight['dep_delay_minutes'])
        reliability[(flight['airline_code'], flight['arr_airport'])].append(flight)

    daily_rows = [
        {
            'departure_date': day.isoformat(),
            'flight_count': len(delays),
            'mean_departure_delay_minutes': round(mean(delays), 2),
        }
        for day, delays in sorted(daily_delays.items())
    ]
    _write_csv(
        output_dir / 'daily_mean_departure_delay.csv',
        ['departure_date', 'flight_count', 'mean_departure_delay_minutes'],
        daily_rows,
    )

    reliability_rows = []
    for (airline, destination), group in reliability.items():
        delayed_count = sum(
            flight['arr_delay_minutes'] > ARRIVAL_DELAY_THRESHOLD_MINUTES
            for flight in group
        )
        reliability_rows.append({
            'airline_code': airline,
            'destination': destination,
            'flight_count': len(group),
            'arrivals_delayed_over_15_minutes': delayed_count,
            'arrival_delay_rate_percent': round(100 * delayed_count / len(group), 2),
            'mean_arrival_delay_minutes': round(
                mean(flight['arr_delay_minutes'] for flight in group), 2
            ),
        })
    reliability_rows.sort(
        key=lambda row: (
            -row['arrival_delay_rate_percent'],
            -row['flight_count'],
            row['airline_code'],
            row['destination'],
        )
    )
    for rank, row in enumerate(reliability_rows, start=1):
        row['rank'] = rank
    _write_csv(
        output_dir / 'airline_destination_reliability.csv',
        [
            'rank',
            'airline_code',
            'destination',
            'flight_count',
            'arrivals_delayed_over_15_minutes',
            'arrival_delay_rate_percent',
            'mean_arrival_delay_minutes',
        ],
        reliability_rows,
    )

    recoveries = [
        flight for flight in metrics
        if flight['dep_delay_minutes'] >= 60 and flight['recovered_minutes'] > 30
    ]
    arrived_over_two_hours_late_but_departed_on_time = [
        flight for flight in metrics
        if flight['arr_delay_minutes'] > 120
        and flight['dep_delay_minutes'] <= 0
    ]
    neither_delay_over_two_hours = [
        flight for flight in metrics
        if flight['dep_delay_minutes'] <= 120
        and flight['arr_delay_minutes'] <= 120
    ]
    partial_or_full_recoveries = [
        flight for flight in metrics
        if flight['dep_delay_minutes'] > 0 and flight['recovered_minutes'] > 0
    ]
    early_departures = [
        flight for flight in metrics if flight['dep_delay_minutes'] < 0
    ]
    early_arrivals = [
        flight for flight in metrics if flight['arr_delay_minutes'] < 0
    ]
    summary = [
        ('flight_count', len(metrics)),
        ('mean_departure_delay_minutes', round(
            mean(flight['dep_delay_minutes'] for flight in metrics), 2
        )),
        ('mean_of_daily_mean_departure_delay_minutes', round(
            mean(row['mean_departure_delay_minutes'] for row in daily_rows), 2
        ) if daily_rows else ''),
        ('arrived_over_120_minutes_late_but_departed_on_time', sum(
            flight['arr_delay_minutes'] > 120
            and flight['dep_delay_minutes'] <= 0
            for flight in metrics
        )),
        ('neither_departure_nor_arrival_delay_over_120_minutes', sum(
            flight['dep_delay_minutes'] <= 120
            and flight['arr_delay_minutes'] <= 120
            for flight in metrics
        )),
        ('departed_early', len(early_departures)),
        ('arrived_early', len(early_arrivals)),
        ('departed_at_least_60_minutes_late_recovered_over_30', len(recoveries)),
        ('longest_distance_miles', max(flight['distance_miles'] for flight in metrics)),
        ('shortest_distance_miles', min(flight['distance_miles'] for flight in metrics)),
    ]
    _write_csv(
        output_dir / 'flight_delay_summary.csv',
        ['metric', 'value'],
        [{'metric': key, 'value': value} for key, value in summary],
    )

    _write_csv(
        output_dir / 'recovered_over_30_minutes.csv',
        metric_fields,
        sorted(recoveries, key=lambda flight: flight['recovered_minutes'], reverse=True),
    )
    _write_csv(
        output_dir / 'all_departure_delay_recoveries.csv',
        metric_fields,
        sorted(
            partial_or_full_recoveries,
            key=lambda flight: flight['recovered_minutes'],
            reverse=True,
        ),
    )
    _write_csv(
        output_dir / 'arrived_over_2_hours_late_departed_on_time.csv',
        metric_fields,
        sorted(
            arrived_over_two_hours_late_but_departed_on_time,
            key=lambda flight: flight['arr_delay_minutes'],
            reverse=True,
        ),
    )
    _write_csv(
        output_dir / 'neither_delay_over_2_hours.csv',
        metric_fields,
        neither_delay_over_two_hours,
    )
    _write_csv(
        output_dir / 'departed_early.csv',
        metric_fields,
        sorted(early_departures, key=lambda flight: flight['dep_delay_minutes']),
    )
    _write_csv(
        output_dir / 'arrived_early.csv',
        metric_fields,
        sorted(early_arrivals, key=lambda flight: flight['arr_delay_minutes']),
    )
    _write_csv(
        output_dir / 'flights_ranked_by_speed.csv',
        metric_fields,
        sorted(metrics, key=lambda flight: flight['speed_mph'], reverse=True),
    )
    _write_csv(
        output_dir / 'flights_ranked_by_distance.csv',
        metric_fields,
        sorted(metrics, key=lambda flight: flight['distance_miles'], reverse=True),
    )

    chart_path = output_dir / 'airline_destination_delay_rate.png'
    top_groups = reliability_rows[:15]
    if top_groups:
        labels = [
            f'{row["airline_code"]} -> {row["destination"]} (n={row["flight_count"]})'
            for row in reversed(top_groups)
        ]
        rates = [
            row['arrival_delay_rate_percent'] for row in reversed(top_groups)
        ]
        fig, ax = plt.subplots(figsize=(11, max(5, len(top_groups) * 0.4)))
        bars = ax.barh(labels, rates, color='indianred', edgecolor='black')
        ax.bar_label(bars, fmt='%.1f%%', padding=3)
        ax.set(
            title='Airline reliability by destination '
                  '(arrival delay > 15 minutes; highest rates)',
            xlabel='Delayed arrivals (%)',
            ylabel='Airline -> destination',
        )
        ax.set_xlim(0, max(rates, default=0) * 1.15 + 1)
        ax.grid(axis='x', linestyle='--', alpha=0.4)
        fig.tight_layout()
        fig.savefig(chart_path)
        plt.close(fig)

    return summary, chart_path


def main():
    base_dir = Path(__file__).resolve().parents[1]
    flights = load_flights(base_dir / 'data' / 'airports')
    output_dir = base_dir / 'data' / 'flight_delay_analysis'
    summary, chart_path = analyze_flights(flights, output_dir)

    print(f'Flights analyzed: {len(flights)}')
    print('Arrival-delay threshold for the reliability ranking: '
          f'> {ARRIVAL_DELAY_THRESHOLD_MINUTES} minutes')
    print('Generated summary:')
    for metric, value in summary:
        print(f'  {metric}: {value}')
    print(f'Chart saved: {chart_path}')
    print(f'Detailed results saved in: {output_dir}')


if __name__ == '__main__':
    main()
