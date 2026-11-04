import csv
from pathlib import Path


MISSING_VALUES = {'', 'na', 'n/a', 'null', 'none', 'nan'}
MINUTES_PER_DAY = 24 * 60


def is_missing(value):
    return value is None or value.strip().lower() in MISSING_VALUES


def find_column(fieldnames, *candidates):
    available = set(fieldnames or [])
    return next((name for name in candidates if name in available), None)


def parse_hhmm(value, column_name):
    if is_missing(value):
        return None
    try:
        numeric_value = float(value)
    except ValueError as error:
        raise ValueError(f'Invalid HHMM value for {column_name}: {value!r}') from error
    if not numeric_value.is_integer():
        raise ValueError(f'HHMM value must be an integer: {column_name}={value!r}')
    hhmm = int(numeric_value)
    if hhmm == 2400:
        return 0
    hour, minute = divmod(hhmm, 100)
    if hour > 23 or minute > 59:
        raise ValueError(f'Invalid HHMM value for {column_name}: {value!r}')
    return hour * 60 + minute


def resolve_columns(fieldnames, file_path):
    columns = {
        'flight_id': find_column(fieldnames, 'flight_id', 'id'),
        'departure_time': find_column(fieldnames, 'dep_time'),
        'scheduled_departure_time': find_column(fieldnames, 'sched_dep_time'),
        'departure_delay': find_column(fieldnames, 'dep_delay'),
        'arrival_time': find_column(fieldnames, 'arr_time'),
        'air_time': find_column(fieldnames, 'air_time'),
    }
    required = ('departure_time', 'scheduled_departure_time', 'departure_delay')
    missing = [key for key in required if columns[key] is None]
    if missing:
        raise ValueError(
            f'{file_path} must contain dep_time, sched_dep_time, and dep_delay '
            f'(missing: {", ".join(missing)}). '
            f'Available columns: {", ".join(fieldnames or [])}'
        )
    return columns


def load_flights(data_dir):
    csv_paths = sorted(data_dir.glob('*_flights.csv'))
    if not csv_paths:
        raise FileNotFoundError(f'No *_flights.csv files found in {data_dir}')

    flights = []
    for csv_path in csv_paths:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            columns = resolve_columns(reader.fieldnames, csv_path)
            for row in reader:
                flight_id = (
                    row[columns['flight_id']]
                    if columns['flight_id'] and not is_missing(row.get(columns['flight_id']))
                    else f'{csv_path.stem}-row-{reader.line_num - 1}'
                )
                departure_minute = parse_hhmm(
                    row.get(columns['departure_time']), columns['departure_time']
                )
                scheduled_minute = parse_hhmm(
                    row.get(columns['scheduled_departure_time']),
                    columns['scheduled_departure_time'],
                )
                departure_delay = row.get(columns['departure_delay'])
                if is_missing(departure_delay):
                    delay_minutes = None
                else:
                    try:
                        delay_minutes = float(departure_delay)
                    except ValueError as error:
                        raise ValueError(
                            f'{csv_path}: invalid dep_delay for flight {flight_id}: '
                            f'{departure_delay!r}'
                        ) from error

                arrival_minute = (
                    parse_hhmm(row.get(columns['arrival_time']), columns['arrival_time'])
                    if columns['arrival_time']
                    else None
                )
                air_time = row.get(columns['air_time']) if columns['air_time'] else None
                if is_missing(air_time):
                    air_time_minutes = None
                else:
                    try:
                        air_time_minutes = float(air_time)
                    except ValueError as error:
                        raise ValueError(
                            f'{csv_path}: invalid air_time for flight {flight_id}: '
                            f'{air_time!r}'
                        ) from error

                calculated_delay = None
                if departure_minute is not None and scheduled_minute is not None:
                    calculated_delay = (
                        (departure_minute - scheduled_minute + MINUTES_PER_DAY // 2)
                        % MINUTES_PER_DAY
                    ) - MINUTES_PER_DAY // 2

                elapsed_clock_minutes = None
                elapsed_minus_air_time = None
                if departure_minute is not None and arrival_minute is not None:
                    elapsed_clock_minutes = (
                        arrival_minute - departure_minute
                    ) % MINUTES_PER_DAY
                    if air_time_minutes is not None:
                        elapsed_minus_air_time = (
                            elapsed_clock_minutes - air_time_minutes
                        )

                flights.append({
                    'flight_id': flight_id,
                    'source_file': csv_path.name,
                    'dep_time': row.get(columns['departure_time'], ''),
                    'sched_dep_time': row.get(columns['scheduled_departure_time'], ''),
                    'dep_delay': delay_minutes,
                    'dep_time_minutes': departure_minute,
                    'sched_dep_time_minutes': scheduled_minute,
                    'calculated_dep_delay_minutes': calculated_delay,
                    'reported_minus_calculated_delay_minutes': (
                        delay_minutes - calculated_delay
                        if delay_minutes is not None and calculated_delay is not None
                        else None
                    ),
                    'arr_time': row.get(columns['arrival_time'], '')
                    if columns['arrival_time'] else '',
                    'arr_time_minutes': arrival_minute,
                    'air_time_minutes': air_time_minutes,
                    'elapsed_clock_minutes': elapsed_clock_minutes,
                    'elapsed_clock_minus_air_time_minutes': elapsed_minus_air_time,
                })

    if not flights:
        raise ValueError(f'No flights found in {data_dir}')
    return flights


def min_ranks(flights):
    ranked = [flight for flight in flights if flight['dep_delay'] is not None]
    ranked.sort(key=lambda flight: flight['dep_delay'], reverse=True)

    result = []
    previous_delay = None
    current_rank = 0
    for row_number, flight in enumerate(ranked, start=1):
        delay = flight['dep_delay']
        if row_number == 1 or delay != previous_delay:
            current_rank = row_number
        result.append({**flight, 'rank': current_rank})
        previous_delay = delay
    return result


def write_csv(path, rows):
    fields = [
        'rank',
        'flight_id',
        'source_file',
        'dep_time',
        'sched_dep_time',
        'dep_delay',
        'dep_time_minutes',
        'sched_dep_time_minutes',
        'calculated_dep_delay_minutes',
        'reported_minus_calculated_delay_minutes',
        'arr_time',
        'arr_time_minutes',
        'air_time_minutes',
        'elapsed_clock_minutes',
        'elapsed_clock_minus_air_time_minutes',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: '' if row.get(key) is None else row.get(key, '')
                for key in fields
            })


def main():
    base_dir = Path(__file__).resolve().parents[1]
    flights = load_flights(base_dir / 'data' / 'airports')
    ranked = min_ranks(flights)
    top_ten = [flight for flight in ranked if flight['rank'] <= 10]
    output_dir = base_dir / 'data' / 'flight_custom_sort_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized_path = output_dir / 'flight_time_comparisons.csv'
    write_csv(normalized_path, flights)
    ranking_path = output_dir / 'top_10_departure_delays_min_rank.csv'
    write_csv(ranking_path, top_ten)

    comparable = [
        flight for flight in flights
        if flight['reported_minus_calculated_delay_minutes'] is not None
    ]
    print(f'Flights analyzed: {len(flights)}')
    print(f'Flights with comparable departure delay: {len(comparable)}')
    if comparable:
        average_difference = sum(
            abs(flight['reported_minus_calculated_delay_minutes'])
            for flight in comparable
        ) / len(comparable)
        print(
            'Mean absolute difference between reported and HHMM-derived '
            f'departure delay: {average_difference:.2f} minutes'
        )
    print(f'Flights in min_rank() top 10: {len(top_ten)}')
    print('Ties share a rank; all flights tied at rank 10 are included.')
    print('HHMM-derived delays wrap across midnight and assume a delay shorter '
          'than 12 hours.')
    print('arr_time - dep_time from clock values is only modulo 24 hours; '
          'timezone offsets and taxi time are not represented.')
    print(f'Normalized comparisons saved: {normalized_path}')
    print(f'Top-10 ranking saved: {ranking_path}')


if __name__ == '__main__':
    main()
