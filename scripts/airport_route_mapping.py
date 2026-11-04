import csv
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


US_MAP_BOUNDS = (-126, -66, 23, 51)

# Approximate contiguous-U.S. outline for a lightweight schematic basemap.
US_OUTLINE = [
    (-124.7, 48.4), (-123.0, 48.2), (-122.5, 46.0),
    (-123.2, 44.5), (-124.1, 42.0), (-123.0, 41.0), (-123.8, 39.0),
    (-122.4, 38.0), (-122.5, 37.0), (-121.0, 36.0), (-120.0, 35.0),
    (-117.1, 33.0), (-114.7, 32.7), (-111.0, 31.3), (-109.0, 31.3),
    (-106.5, 31.8), (-103.0, 29.8), (-101.0, 29.0), (-99.0, 26.4),
    (-97.2, 25.9), (-96.0, 28.0), (-94.5, 29.5), (-91.0, 29.2),
    (-89.5, 30.2), (-88.0, 30.3), (-85.0, 30.2), (-82.0, 25.2),
    (-80.0, 25.4), (-80.1, 27.0), (-80.5, 29.0), (-81.0, 30.7),
    (-80.0, 32.0), (-78.5, 33.0), (-77.0, 35.0), (-76.0, 36.5),
    (-75.5, 38.0), (-74.0, 40.0), (-72.0, 41.3), (-70.0, 42.0),
    (-69.0, 43.0), (-69.0, 45.0), (-69.5, 47.0),
    (-71.5, 45.0), (-73.3, 45.0), (-75.0, 44.9), (-76.8, 43.6),
    (-79.0, 43.3), (-80.5, 42.5), (-82.5, 41.7), (-84.8, 41.7),
    (-86.8, 41.8), (-87.5, 41.9), (-89.5, 37.0), (-90.3, 35.0),
    (-91.5, 33.0), (-94.0, 33.0), (-94.5, 36.0), (-94.6, 36.9),
    (-100.0, 37.0), (-102.0, 37.0), (-102.0, 41.0), (-104.0, 41.0),
    (-104.0, 45.9), (-106.0, 46.0), (-111.0, 45.0), (-113.0, 46.0),
    (-116.0, 47.5), (-120.0, 49.0), (-123.0, 49.0),
    (-124.7, 48.4),
]


def load_airports(path):
    airports = {}
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        required = {'airport_code', 'latitude', 'longitude'}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'{path} is missing columns: {", ".join(sorted(missing))}')
        for row in reader:
            code = row['airport_code'].strip().upper()
            latitude = float(row['latitude'])
            longitude = float(row['longitude'])
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError(f'Invalid coordinates for airport {code}')
            airports[code] = {
                **row,
                'airport_code': code,
                'latitude': latitude,
                'longitude': longitude,
            }
    if not airports:
        raise ValueError(f'No airport coordinates found in {path}')
    return airports


def load_routes(data_dir):
    csv_paths = sorted(data_dir.glob('*_flights.csv'))
    if not csv_paths:
        raise FileNotFoundError(f'No *_flights.csv files found in {data_dir}')
    routes = Counter()
    missing_columns = []
    for csv_path in csv_paths:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if not {'dep_airport', 'arr_airport'} <= set(reader.fieldnames or []):
                missing_columns.append(csv_path.name)
                continue
            for row in reader:
                origin = (row.get('dep_airport') or '').strip().upper()
                destination = (row.get('arr_airport') or '').strip().upper()
                if origin and destination:
                    routes[(origin, destination)] += 1
    if missing_columns:
        raise ValueError(
            'Flight CSVs are missing dep_airport/arr_airport: '
            + ', '.join(missing_columns)
        )
    if not routes:
        raise ValueError('No valid origin-destination routes found')
    return routes


def route_rows(routes, airports):
    rows = []
    unknown_airports = set()
    for (origin, destination), count in routes.most_common():
        if origin not in airports:
            unknown_airports.add(origin)
        if destination not in airports:
            unknown_airports.add(destination)
        origin_coords = airports.get(origin)
        destination_coords = airports.get(destination)
        rows.append({
            'origin': origin,
            'destination': destination,
            'flight_count': count,
            'origin_lon': origin_coords['longitude'] if origin_coords else '',
            'origin_lat': origin_coords['latitude'] if origin_coords else '',
            'dest_lon': destination_coords['longitude'] if destination_coords else '',
            'dest_lat': destination_coords['latitude'] if destination_coords else '',
        })
    if unknown_airports:
        raise ValueError(
            'Missing airport coordinates for: '
            + ', '.join(sorted(unknown_airports))
            + '. Add them to data/airports/airport_coordinates.csv.'
        )
    return rows


def write_csv(path, rows):
    fields = [
        'origin',
        'destination',
        'flight_count',
        'origin_lon',
        'origin_lat',
        'dest_lon',
        'dest_lat',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_us_routes(rows, airports, path):
    us_airports = {
        code: airport for code, airport in airports.items()
        if airport.get('country', '').strip().lower() in {'united states', 'usa', 'us'}
        and US_MAP_BOUNDS[0] <= airport['longitude'] <= US_MAP_BOUNDS[1]
        and US_MAP_BOUNDS[2] <= airport['latitude'] <= US_MAP_BOUNDS[3]
    }
    domestic_routes = [
        row for row in rows
        if row['origin'] in us_airports and row['destination'] in us_airports
    ]

    fig, ax = plt.subplots(figsize=(12, 7))
    outline_x, outline_y = zip(*US_OUTLINE)
    ax.fill(outline_x, outline_y, color='#f3f0e8', edgecolor='#58656f', linewidth=1.2)
    ax.set_facecolor('#dcecf4')

    max_count = max((row['flight_count'] for row in domestic_routes), default=1)
    for row in domestic_routes:
        origin = airports[row['origin']]
        destination = airports[row['destination']]
        line_width = 1.1 + 3.0 * row['flight_count'] / max_count
        ax.annotate(
            '',
            xy=(destination['longitude'], destination['latitude']),
            xytext=(origin['longitude'], origin['latitude']),
            arrowprops={
                'arrowstyle': '-|>',
                'color': '#c43c39',
                'linewidth': line_width,
                'alpha': 0.75,
                'connectionstyle': 'arc3,rad=0.15',
                'shrinkA': 8,
                'shrinkB': 8,
            },
        )

    for code, airport in us_airports.items():
        ax.scatter(
            airport['longitude'],
            airport['latitude'],
            s=35,
            color='#173f5f',
            edgecolors='white',
            linewidths=0.6,
            zorder=4,
        )
        ax.annotate(
            code,
            (airport['longitude'], airport['latitude']),
            xytext=(4, 4),
            textcoords='offset points',
            fontsize=8,
            zorder=5,
        )

    ax.set_xlim(US_MAP_BOUNDS[0], US_MAP_BOUNDS[1])
    ax.set_ylim(US_MAP_BOUNDS[2], US_MAP_BOUNDS[3])
    ax.set_aspect('equal', adjustable='box')
    ax.set(
        title=f'Most frequent domestic U.S. routes ({len(domestic_routes)} routes)',
        xlabel='Longitude',
        ylabel='Latitude',
    )
    ax.grid(True, linestyle=':', alpha=0.4)
    ax.text(
        0.01,
        0.015,
        'Schematic contiguous-U.S. outline; arrows show flight direction.',
        transform=ax.transAxes,
        fontsize=8,
        color='#45545e',
    )
    if not domestic_routes:
        ax.text(
            0.5,
            0.5,
            'No routes with both origin and destination in the United States',
            transform=ax.transAxes,
            ha='center',
            va='center',
            bbox={'facecolor': 'white', 'alpha': 0.85, 'edgecolor': 'gray'},
        )
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return domestic_routes


def main():
    base_dir = Path(__file__).resolve().parents[1]
    airport_path = base_dir / 'data' / 'airports' / 'airport_coordinates.csv'
    airports = load_airports(airport_path)
    routes = load_routes(base_dir / 'data' / 'airports')
    rows = route_rows(routes, airports)

    output_dir = base_dir / 'data' / 'airport_route_mapping'
    output_dir.mkdir(parents=True, exist_ok=True)
    top_100_path = output_dir / 'top_100_routes.csv'
    write_csv(top_100_path, rows[:100])

    destination_counts = Counter()
    for (origin, destination), count in routes.items():
        destination_counts[destination] += count
    top_destinations = [
        {'destination': code, 'flight_count': count}
        for code, count in destination_counts.most_common(5)
    ]
    top_destinations_path = output_dir / 'top_5_destinations.csv'
    with open(top_destinations_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=['destination', 'flight_count']
        )
        writer.writeheader()
        writer.writerows(top_destinations)

    map_path = output_dir / 'us_top_routes.png'
    domestic_routes = plot_us_routes(rows[:100], airports, map_path)

    print(f'Flights/routes aggregated: {sum(routes.values())} flights, {len(routes)} unique routes')
    print('Top 5 destinations:')
    for row in top_destinations:
        print(f'  {row["destination"]}: {row["flight_count"]} flights')
    print(f'Top 100 global routes saved: {top_100_path}')
    print(f'Top 5 destinations saved: {top_destinations_path}')
    print(f'U.S. domestic routes in top 100 and plotted: {len(domestic_routes)}')
    print(f'U.S. route map saved: {map_path}')


if __name__ == '__main__':
    main()
