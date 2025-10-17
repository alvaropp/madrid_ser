#!/usr/bin/env python3
"""
Process the complete Madrid street directory with SER zones and coordinates.
This file (CALLEJERO_VIGENTE_NUMERACIONES_202510.csv) already has everything!
"""

import pandas as pd
import json

# Configuration
INPUT_FILE = 'data/CALLEJERO_VIGENTE_NUMERACIONES_202510.csv'
OUTPUT_FILE = 'data/parking_with_coordinates.json'

print("=" * 70)
print("Processing Madrid Street Directory with SER Zones & Coordinates")
print("=" * 70)

# Load the complete file
print("\n1. Loading complete street directory...")
df = pd.read_csv(INPUT_FILE, delimiter=';', encoding='latin-1', dtype=str, low_memory=False)
print(f"   ✓ Loaded {len(df)} address records")
print(f"   Columns: {len(df.columns)}")

# Clean column names
df.columns = df.columns.str.strip()

# Filter only addresses with SER zones (non-zero and non-empty)
print("\n2. Filtering addresses with SER zones...")
df['ser_zone'] = df['Zona Servicio Estacionamiento Regulado'].str.strip()
df_ser = df[(df['ser_zone'].notna()) & (df['ser_zone'] != '') & (df['ser_zone'] != '000')].copy()
print(f"   ✓ Found {len(df_ser)} addresses with SER zones")

# Parse coordinates
print("\n3. Parsing coordinates...")

def parse_coordinate(coord_str, coord_type='lat'):
    """Parse coordinate from degrees/minutes/seconds format"""
    try:
        coord_str = str(coord_str).strip()
        if not coord_str or coord_str == 'nan':
            return None

        # Remove direction indicator and normalize degree symbols
        # Handle both º (ordinal) and ° (degree symbol)
        parts = coord_str.replace('°', ' ').replace('º', ' ').replace("'", ' ').replace('"', ' ').replace('W', '').replace('E', '').replace('N', '').replace('S', '').split()

        if len(parts) >= 3:
            degrees = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])

            decimal = degrees + minutes/60 + seconds/3600

            # Longitude is negative for West (Madrid is West)
            if coord_type == 'lon':
                decimal = -decimal

            return decimal
    except Exception as e:
        return None
    return None

df_ser['lat'] = df_ser['Latitud en S R  ETRS89 WGS84'].apply(lambda x: parse_coordinate(x, 'lat'))
df_ser['lon'] = df_ser['Longitud en S R  ETRS89 WGS84'].apply(lambda x: parse_coordinate(x, 'lon'))

# Remove records without valid coordinates
df_ser = df_ser[df_ser['lat'].notna() & df_ser['lon'].notna()]
print(f"   ✓ {len(df_ser)} addresses with valid coordinates")

# Group by street to avoid overcrowding the map
print("\n4. Grouping by street (to reduce markers)...")
df_ser['street_key'] = df_ser['Codigo de via'].str.strip()

# Aggregate by street - take first coordinate and combine zones
grouped = df_ser.groupby('street_key').agg({
    'Nombre de la vía': 'first',
    'Partícula de la vía': 'first',
    'Clase de la via': 'first',
    'Literal de numeracion': 'first',
    'ser_zone': lambda x: ', '.join(sorted(set(x))),
    'Nombre del distrito': 'first',
    'Codigo postal': 'first',
    'lat': 'first',
    'lon': 'first'
}).reset_index()

print(f"   ✓ Grouped into {len(grouped)} unique locations")

# Create final output
print("\n5. Creating output dataset...")
results = []

for idx, row in grouped.iterrows():
    street_name = str(row.get('Partícula de la vía', '')).strip() + ' ' + str(row.get('Nombre de la vía', '')).strip()
    street_name = street_name.strip()

    # Skip if no valid name or coordinates
    if not street_name or row['lat'] is None or row['lon'] is None:
        continue

    results.append({
        'street_name': street_name,
        'street_type': str(row.get('Clase de la via', '')).strip(),
        'number': str(row.get('Literal de numeracion', '')).strip(),
        'zone': row['ser_zone'],
        'segment_type': 'various',
        'district': str(row.get('Nombre del distrito', '')).strip(),
        'postal_code': str(row.get('Codigo postal', '')).strip(),
        'lat': float(row['lat']),
        'lon': float(row['lon'])
    })

print(f"   ✓ Created {len(results)} records")

# Save to JSON
print(f"\n6. Saving to {OUTPUT_FILE}...")
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"   ✓ Saved {len(results)} records")

# Statistics
unique_zones = set()
for r in results:
    if r['zone']:
        unique_zones.update(r['zone'].split(', '))

print("\n" + "=" * 70)
print("✓ SUCCESS! Data is ready for instant visualization")
print("=" * 70)
print(f"\nStatistics:")
print(f"  - Total locations with SER zones: {len(results)}")
print(f"  - Unique SER zones: {len(unique_zones)}")
print(f"  - Output file: {OUTPUT_FILE}")
print(f"\nThe webapp will now load INSTANTLY - no geocoding needed!")
print("=" * 70)
