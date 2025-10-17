#!/usr/bin/env python3
"""
Batch preprocessing script to geocode all street addresses upfront.
This creates a processed dataset with coordinates, making the webapp instant.
"""

import json
import time

import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

# Configuration
INPUT_FILE = "data/CALLEJERO_VIGENTE_SER_202510.csv"
OUTPUT_FILE = "data/processed_parking_data.json"
GEOCODE_CACHE_FILE = "geocode_cache.json"


def load_geocode_cache():
    """Load existing geocode cache"""
    try:
        with open(GEOCODE_CACHE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_geocode_cache(cache):
    """Save geocode cache"""
    with open(GEOCODE_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def geocode_address(address, geolocator, cache):
    """Geocode an address with caching"""
    if address in cache:
        return cache[address]

    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            result = {"lat": location.latitude, "lon": location.longitude}
            cache[address] = result
            return result
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
        return None

    return None


def main():
    print("=" * 60)
    print("Madrid SER Data Preprocessing")
    print("=" * 60)

    # Load data
    print("\n1. Loading CSV data...")
    df = pd.read_csv(INPUT_FILE, delimiter=";", encoding="latin-1", dtype=str)
    df.columns = df.columns.str.strip()
    print(f"   ✓ Loaded {len(df)} parking segments")

    # Process data
    print("\n2. Processing street data...")
    df["street_name"] = (
        df["Particula de la via"].str.strip() + " " + df["Nombre de la via"].str.strip()
    ).str.strip()
    df["zone"] = df["Zona S E R  del tramo"].str.strip()
    df["street_type"] = df["Clase de la via"].str.strip()
    df["segment_type"] = df["Tipo de tramo"].str.strip()
    df["full_address"] = df["street_type"] + " " + df["street_name"] + ", Madrid, Spain"

    # Group by unique addresses
    print("\n3. Grouping by unique streets...")
    street_groups = (
        df.groupby("full_address")
        .agg(
            {
                "street_name": "first",
                "street_type": "first",
                "zone": lambda x: ", ".join(sorted(set(x))),
                "segment_type": lambda x: ", ".join(x),
            }
        )
        .reset_index()
    )
    print(f"   ✓ Found {len(street_groups)} unique streets")

    # Load cache and geocode
    print("\n4. Geocoding addresses...")
    cache = load_geocode_cache()
    geolocator = Nominatim(user_agent="madrid_ser_preprocessing")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

    cached_count = 0
    geocoded_count = 0
    failed_count = 0

    results = []

    for idx, row in street_groups.iterrows():
        address = row["full_address"]

        # Get coordinates
        coords = geocode_address(address, geolocator, cache)

        if coords:
            if address in cache and idx > 0:
                cached_count += 1
            else:
                geocoded_count += 1
                if geocoded_count % 10 == 0:
                    print(
                        f"   Progress: {geocoded_count} geocoded, {cached_count} from cache, {failed_count} failed"
                    )
                    save_geocode_cache(cache)  # Save periodically

            results.append(
                {
                    "address": address,
                    "street_name": row["street_name"],
                    "street_type": row["street_type"],
                    "zone": row["zone"],
                    "segment_type": row["segment_type"],
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                }
            )
        else:
            failed_count += 1

    # Save final cache
    save_geocode_cache(cache)

    print(f"\n   ✓ Geocoding complete:")
    print(f"     - Successfully geocoded: {len(results)}")
    print(f"     - From cache: {cached_count}")
    print(f"     - Newly geocoded: {geocoded_count}")
    print(f"     - Failed: {failed_count}")

    # Save processed data
    print(f"\n5. Saving processed data to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"   ✓ Saved {len(results)} geocoded streets")
    print("\n" + "=" * 60)
    print("✓ Preprocessing complete! The webapp will now load instantly.")
    print("=" * 60)


if __name__ == "__main__":
    main()
