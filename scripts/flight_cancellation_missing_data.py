import csv
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


MISSING_VALUES = {'', 'na', 'n/a', 'null', 'none', 'nan'}


def is_missing(value):
    return value is None or value.strip().lower() in MISSING_VALUES


def resolve_column(fieldnames, *candidates):
    available = set(fieldnames or [])
    return next((name for name in candidates if name in available), None)


def load_flights(data_dir):
    csv_paths = sorted(data_dir.glob('*_flights.csv'))
    if not csv_paths:
        raise FileNotFoundError(f'No *_flights.csv files found in {data_dir}')

    flights = []
    fieldnames = []
    for csv_path in csv_paths:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                raise ValueError(f'{csv_path} has no CSV header')
            for name in reader.fieldnames:
                if name not in fieldnames:
                    fieldnames.append(name)
            source_airport = csv_path.stem.removesuffix('_flights').upper()
            for row in reader:
                flights.append({
                    **row,
                    '_source_file': csv_path.name,
                    '_source_airport': source_airport,
                })
    if not flights:
        raise ValueError(f'No flights found in {data_dir}')
    return flights, fieldnames


def build_missingness(flights, fieldnames):
    rows = []
    for column in fieldnames:
        missing_count = sum(is_missing(flight.get(column)) for flight in flights)
        rows.append({
            'column': column,
            'missing_count': missing_count,
            'total_count': len(flights),
            'missing_percent': round(100 * missing_count / len(flights), 2),
        })
    return rows


def sort_missing_first(flights, column, descending):
    present = [flight for flight in flights if not is_missing(flight.get(column))]
    missing = [flight for flight in flights if is_missing(flight.get(column))]
    present.sort(
        key=lambda flight: float(flight[column]),
        reverse=descending,
    )
    return missing + present


def sort_delay_then_departure(flights, delay_column, departure_column):
    keyed_rows = []
    missing_delay = []
    for flight in flights:
        if is_missing(flight.get(delay_column)):
            missing_delay.append(flight)
        else:
            keyed_rows.append(flight)

    nonmissing_delay = []
    by_delay = {}
    for flight in keyed_rows:
        by_delay.setdefault(float(flight[delay_column]), []).append(flight)
    for delay in sorted(by_delay, reverse=True):
        tied = by_delay[delay]
        present_time = [
            flight for flight in tied
            if not is_missing(flight.get(departure_column))
        ]
        missing_time = [
            flight for flight in tied
            if is_missing(flight.get(departure_column))
        ]
        present_time.sort(key=lambda flight: flight[departure_column].strip())
        nonmissing_delay.extend(missing_time + present_time)
    return missing_delay + nonmissing_delay


def month_label(value):
    if is_missing(value):
        return 'Unknown'
    normalized = value.strip().replace('/', '-')
    return normalized[:7] if len(normalized) >= 7 else normalized


def write_rows(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def count_by(rows, key):
    counts = Counter()
    for row in rows:
        value = row.get(key)
        label = value.strip() if not is_missing(value) else 'Unknown'
        counts[label] += 1
    return counts


def save_bar_chart(counts, path, title, xlabel, top_n=20):
    selected = counts.most_common(top_n)
    fig, ax = plt.subplots(figsize=(11, max(4, len(selected) * 0.38)))
    if selected:
        labels = [label for label, _ in reversed(selected)]
        values = [value for _, value in reversed(selected)]
        bars = ax.barh(labels, values, color='indianred', edgecolor='black')
        ax.bar_label(bars, padding=3)
        ax.set_xlim(0, max(values) * 1.15 + 1)
    else:
        ax.text(0.5, 0.5, 'No cancelled flights found',
                ha='center', va='center', transform=ax.transAxes)
    ax.set(title=title, xlabel=xlabel, ylabel='')
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def analyze(flights, fieldnames, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = {
        'departure_time': resolve_column(
            fieldnames, 'dep_time', 'departure_time', 'dep_date',
            'departure_actual',
        ),
        'arrival_time': resolve_column(
            fieldnames, 'arr_time', 'arrival_time', 'arr_date',
            'arrival_actual',
        ),
        'departure_delay': resolve_column(
            fieldnames, 'dep_delay', 'dep_delay_minutes',
        ),
        'arrival_delay': resolve_column(
            fieldnames, 'arr_delay', 'arr_delay_minutes',
        ),
        'destination': resolve_column(
            fieldnames, 'dest', 'destination', 'arr_airport',
            'arrival_airport_code',
        ),
        'airline': resolve_column(
            fieldnames, 'carrier', 'airline', 'airline_code', 'company',
        ),
        'date': resolve_column(
            fieldnames, 'flight_date', 'date', 'year_month',
            'departure_scheduled', 'dep_scheduled', 'dep_date',
        ),
    }

    missingness = build_missingness(flights, fieldnames)
    write_rows(
        output_dir / 'missing_data_by_column.csv',
        ['column', 'missing_count', 'total_count', 'missing_percent'],
        missingness,
    )

    missing_required = [
        key for key in ('departure_time', 'arrival_time', 'departure_delay',
                        'arrival_delay', 'destination', 'airline', 'date')
        if columns[key] is None
    ]
    _write_missingness_chart(
        missingness, output_dir / 'missing_data_by_column.png'
    )

    cancelled = []
    cancellation_counts = []
    if columns['departure_time'] and columns['arrival_time']:
        cancelled = [
            flight for flight in flights
            if is_missing(flight.get(columns['departure_time']))
            and is_missing(flight.get(columns['arrival_time']))
        ]
        for label, key in (
            ('destination', columns['destination']),
            ('airline', columns['airline']),
            ('month', columns['date']),
        ):
            if key:
                counts = (
                    Counter(month_label(flight.get(key)) for flight in cancelled)
                    if label == 'month'
                    else count_by(cancelled, key)
                )
                cancellation_counts.append((label, counts))
                rows = [
                    {'group': group, 'cancelled_flight_count': count}
                    for group, count in sorted(counts.items())
                ]
                write_rows(
                    output_dir / f'cancellations_by_{label}.csv',
                    ['group', 'cancelled_flight_count'],
                    rows,
                )
                save_bar_chart(
                    counts,
                    output_dir / f'cancellations_by_{label}.png',
                    f'Cancelled flights by {label}',
                    'Cancelled flights',
                    top_n=24 if label == 'month' else 20,
                )

        group_keys = [
            key for key in (columns['destination'], columns['airline'])
            if key
        ]
        if len(group_keys) == 2:
            cross_counts = Counter(
                (
                    flight[group_keys[0]].strip()
                    if not is_missing(flight.get(group_keys[0])) else 'Unknown',
                    flight[group_keys[1]].strip()
                    if not is_missing(flight.get(group_keys[1])) else 'Unknown',
                )
                for flight in cancelled
            )
            cross_rows = [
                {
                    'destination': destination,
                    'airline': airline,
                    'cancelled_flight_count': count,
                }
                for (destination, airline), count in sorted(
                    cross_counts.items(), key=lambda item: (-item[1], item[0])
                )
            ]
            write_rows(
                output_dir / 'cancellations_by_destination_and_airline.csv',
                ['destination', 'airline', 'cancelled_flight_count'],
                cross_rows,
            )

    sorted_files = []
    if columns['departure_delay']:
        delay_column = columns['departure_delay']
        sort_one = sort_missing_first(flights, delay_column, descending=True)
        path_one = output_dir / 'flights_by_departure_delay_desc_na_first.csv'
        write_rows(path_one, fieldnames, sort_one)
        sorted_files.append(path_one)

        if columns['departure_time']:
            sort_two = sort_delay_then_departure(
                flights, delay_column, columns['departure_time']
            )
            path_two = output_dir / 'flights_by_delay_desc_time_asc_na_first.csv'
            write_rows(path_two, fieldnames, sort_two)
            sorted_files.append(path_two)

    chart_paths = [output_dir / 'missing_data_by_column.png']
    for label, _ in cancellation_counts:
        chart_paths.append(output_dir / f'cancellations_by_{label}.png')

    return {
        'columns': columns,
        'missing_required': missing_required,
        'missingness': missingness,
        'cancelled_count': len(cancelled),
        'flight_count': len(flights),
        'chart_paths': chart_paths,
        'sorted_files': sorted_files,
    }


def _write_missingness_chart(rows, path):
    selected = [row for row in rows if row['missing_count'] > 0]
    fig, ax = plt.subplots(figsize=(10, max(4, len(selected) * 0.4)))
    if selected:
        selected.sort(key=lambda row: row['missing_percent'])
        labels = [row['column'] for row in selected]
        values = [row['missing_percent'] for row in selected]
        bars = ax.barh(labels, values, color='darkorange', edgecolor='black')
        ax.bar_label(bars, fmt='%.1f%%', padding=3)
        ax.set_xlim(0, max(values) * 1.15 + 1)
    else:
        ax.text(0.5, 0.5, 'No missing values found',
                ha='center', va='center', transform=ax.transAxes)
    ax.set(title='Missing values by column', xlabel='Missing values (%)', ylabel='')
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    base_dir = Path(__file__).resolve().parents[1]
    flights, fieldnames = load_flights(base_dir / 'data' / 'airports')
    output_dir = base_dir / 'data' / 'flight_cancellation_analysis'
    report = analyze(flights, fieldnames, output_dir)

    print(f'Flights analyzed: {report["flight_count"]}')
    print('Missing values by column:')
    for row in report['missingness']:
        print(
            f'  {row["column"]}: {row["missing_count"]}/'
            f'{row["total_count"]} ({row["missing_percent"]:.2f}%)'
        )
    if report['columns']['departure_time'] and report['columns']['arrival_time']:
        print(
            'Cancelled flights (departure and arrival times both missing): '
            f'{report["cancelled_count"]}'
        )
    else:
        print('Cannot calculate cancellations: dep_time/arr_time columns absent.')
    if report['missing_required']:
        print(
            'Unavailable requested fields in this dataset: '
            + ', '.join(report['missing_required'])
        )
    for path in report['chart_paths']:
        print(f'Chart saved: {path}')
    for path in report['sorted_files']:
        print(f'Sorted flights saved: {path}')
    print(f'CSV results saved in: {output_dir}')


if __name__ == '__main__':
    main()
