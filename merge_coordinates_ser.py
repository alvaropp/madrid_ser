#!/usr/bin/env python3
"""
Merge coordinates dataset with SER zones dataset.
Creates a final dataset ready for instant map visualization.
"""

import pandas as pd
import json

# Configuration
COORDINATES_FILE = 'direcciones_con_coordenadas.csv'
SER_ZONES_FILE = 'data/CALLEJERO_VIGENTE_SER_202510.csv'
OUTPUT_FILE = 'data/parking_with_coordinates.json'

print("=" * 60)
print("Merging Coordinates with SER Zones")
print("=" * 60)

# Load coordinates file
print("\n1. Loading addresses with coordinates...")
df_coords = pd.read_csv(COORDINATES_FILE, delimiter=';', encoding='latin-1', dtype=str)
print(f"   ✓ Loaded {len(df_coords)} addresses with coordinates")
print(f"   Columns: {', '.join(df_coords.columns[:10])}")

# Load SER zones file
print("\n2. Loading SER zones data...")
df_ser = pd.read_csv(SER_ZONES_FILE, delimiter=';', encoding='latin-1', dtype=str)
df_ser.columns = df_ser.columns.str.strip()
print(f"   ✓ Loaded {len(df_ser)} SER zone records")

# Parse coordinates (convert from degrees/minutes/seconds to decimal)
print("\n3. Parsing coordinates...")

def dms_to_decimal(dms_str):
    """Convert degrees/minutes/seconds string to decimal"""
    try:
        # Format: "40°29'21.84'' N" or "3°40'23.56'' W"
        dms_str = str(dms_str).strip()
        if not dms_str or dms_str == 'nan':
            return None

        # Remove direction (N/S/E/W)
        direction = dms_str[-1]
        dms_str = dms_str[:-2].strip()

        # Split by degree, minute, second symbols
        parts = dms_str.replace('°', ' ').replace("'", ' ').replace('"', ' ').split()

        if len(parts) >= 3:
            degrees = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])

            decimal = degrees + minutes/60 + seconds/3600

            # Make negative for West/South
            if direction in ['W', 'S']:
                decimal = -decimal

            return decimal
    except:
        return None
    return None

df_coords['lat'] = df_coords['LATITUD'].apply(dms_to_decimal)
df_coords['lon'] = df_coords['LONGITUD'].apply(dms_to_decimal)

# Remove rows without valid coordinates
df_coords = df_coords[df_coords['lat'].notna() & df_coords['lon'].notna()]
print(f"   ✓ Parsed {len(df_coords)} addresses with valid coordinates")

# Prepare SER data for merging
print("\n4. Preparing SER zone data...")
df_ser['street_key'] = (df_ser['Codigo de via'].str.strip())
df_ser['zone'] = df_ser['Zona S E R  del tramo'].str.strip()
df_ser['segment_type'] = df_ser['Tipo de tramo'].str.strip()

# Group by street code to get all zones per street
ser_grouped = df_ser.groupby('street_key').agg({
    'zone': lambda x: ', '.join(sorted(set([z for z in x if z and z != '0']))),
    'segment_type': lambda x: ', '.join(sorted(set(x)))
}).reset_index()

# Filter only streets with SER zones
ser_grouped = ser_grouped[ser_grouped['zone'].str.len() > 0]
print(f"   ✓ Found {len(ser_grouped)} streets with SER zones")

# Merge datasets
print("\n5. Merging datasets...")
df_coords['street_key'] = df_coords['COD_VIA'].str.strip()

df_merged = df_coords.merge(
    ser_grouped,
    on='street_key',
    how='inner'
)

print(f"   ✓ Merged: {len(df_merged)} addresses with SER zones and coordinates")

# Create final output
print("\n6. Creating output dataset...")
results = []

for idx, row in df_merged.iterrows():
    street_name = str(row.get('VIA_PAR', '')).strip() + ' ' + str(row.get('VIA_NOMBRE', '')).strip()
    street_name = street_name.strip()

    results.append({
        'street_name': street_name,
        'street_type': str(row.get('VIA_CLASE', '')).strip(),
        'number': str(row.get('NUMERO', '')).strip(),
        'zone': row['zone'],
        'segment_type': row['segment_type'],
        'district': str(row.get('DISTRITO', '')).strip(),
        'postal_code': str(row.get('COD_POSTAL', '')).strip(),
        'lat': float(row['lat']),
        'lon': float(row['lon'])
    })

print(f"   ✓ Created {len(results)} records")

# Save to JSON
print(f"\n7. Saving to {OUTPUT_FILE}...")
with open(OUTPUT_FILE, 'w') as f:
    json.dump(results, f, indent=2)

print(f"   ✓ Saved {len(results)} records")

# Statistics
print("\n" + "=" * 60)
print("✓ SUCCESS! Data is ready")
print("=" * 60)
print(f"\nStatistics:")
print(f"  - Total addresses with SER zones: {len(results)}")
print(f"  - Unique zones: {len(set(r['zone'].split(', ')[0] for r in results if r['zone']))}")
print(f"\nThe webapp will now load INSTANTLY!")
print("=" * 60)
