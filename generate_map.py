"""
Generate an optimized static HTML file with compressed data.
Much faster loading than the standard Folium output.
"""
import geopandas as gpd
import json

# Configuration
DATA_FILE = "data/SHP_ZIP/Bandas_de_Aparcamiento.shp"
OUTPUT_FILE = "index.html"

# Color mapping for zone types
ZONE_COLORS = {
    'Verde': '#28a745',
    'Azul': '#007bff',
    'Naranja': '#fd7e14',
    'Rojo': '#dc3545',
    'Alta Rotación': '#6f42c1',
    'Unknown': '#6c757d'
}


def simplify_coordinates(coords, precision=5):
    """Simplify coordinates to reduce file size"""
    return [[round(lat, precision), round(lon, precision)] for lon, lat, *_ in coords]


def generate_optimized_map():
    """Generate optimized static map"""
    print("Loading parking segments from shapefile...")
    gdf = gpd.read_file(DATA_FILE)

    print(f"Converting {len(gdf)} segments to WGS84...")
    gdf = gdf.to_crs(epsg=4326)

    # Clean up the data
    gdf['Color'] = gdf['Color'].fillna('Unknown')
    gdf['Res_NumPla'] = gdf['Res_NumPla'].fillna(0).astype(int)

    print("Processing segments by zone type...")
    zone_data = {}

    for zone_type in sorted(gdf['Color'].unique()):
        print(f"  Processing {zone_type}...")
        zone_gdf = gdf[gdf['Color'] == zone_type]

        features = []
        for idx, row in zone_gdf.iterrows():
            coords = list(row['geometry'].coords)
            simplified_coords = simplify_coordinates(coords)

            features.append({
                'coords': simplified_coords,
                'spots': int(row['Res_NumPla']),
                'type': str(row['Bateria_Li']) if row['Bateria_Li'] else 'N/A',
                'id': int(row['ID'])
            })

        zone_data[zone_type] = features

    print("Generating HTML...")

    # Calculate statistics
    total_segments = len(gdf)
    total_spots = int(gdf['Res_NumPla'].sum())

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Madrid SER - Regulated Parking Zones</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            height: 100vh;
            overflow: hidden;
        }}
        #map {{
            width: 100%;
            height: 100%;
        }}
        .info-box {{
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 15px 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
        }}
        .info-box h2 {{
            margin: 0;
            font-size: 20px;
        }}
        .info-box p {{
            margin: 5px 0 0 0;
            font-size: 14px;
            color: #666;
        }}
        .legend {{
            position: absolute;
            bottom: 30px;
            right: 30px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            font-size: 14px;
        }}
        .legend-title {{
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .legend-line {{
            width: 20px;
            height: 3px;
            margin-right: 8px;
        }}
        .legend-note {{
            margin-top: 10px;
            font-size: 12px;
            color: #666;
            font-style: italic;
        }}
        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 2000;
            text-align: center;
        }}
        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div>Loading map...</div>
    </div>

    <div id="map"></div>

    <div class="info-box">
        <h2>Madrid SER - Regulated Parking Zones</h2>
        <p>{total_segments:,} segments | {total_spots:,} parking spots</p>
    </div>

    <div class="legend">
        <div class="legend-title">Zone Types</div>
"""

    for zone_type in sorted(ZONE_COLORS.keys()):
        if zone_type != 'Unknown':
            color = ZONE_COLORS[zone_type]
            html_content += f"""        <div class="legend-item">
            <div class="legend-line" style="background-color: {color};"></div>
            <span>{zone_type}</span>
        </div>
"""

    html_content += """        <div class="legend-note">Line thickness = number of spots</div>
    </div>

    <script>
"""

    # Embed zone data as JavaScript
    html_content += f"        const zoneData = {json.dumps(zone_data)};\n"
    html_content += f"        const zoneColors = {json.dumps(ZONE_COLORS)};\n"

    html_content += """
        // Initialize map
        const map = L.map('map', {
            center: [40.4168, -3.7038],
            zoom: 13,
            preferCanvas: true  // Use canvas for better performance with many features
        });

        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);

        // Layer groups for each zone type
        const layerGroups = {};

        // Add segments to map
        Object.keys(zoneData).forEach(zoneType => {
            const color = zoneColors[zoneType] || '#6c757d';
            const layerGroup = L.layerGroup();

            zoneData[zoneType].forEach(segment => {
                const weight = Math.min(Math.max(segment.spots * 0.3, 3), 10);

                const polyline = L.polyline(segment.coords, {
                    color: color,
                    weight: weight,
                    opacity: 0.8
                });

                polyline.bindPopup(`
                    <div style="font-family: Arial;">
                        <h4 style="margin: 0 0 10px 0; color: ${color};">${zoneType}</h4>
                        <p style="margin: 5px 0;"><strong>Spots:</strong> ${segment.spots}</p>
                        <p style="margin: 5px 0;"><strong>Type:</strong> ${segment.type}</p>
                        <p style="margin: 5px 0;"><strong>ID:</strong> ${segment.id}</p>
                    </div>
                `);

                polyline.bindTooltip(`${zoneType}: ${segment.spots} spots`);

                polyline.addTo(layerGroup);
            });

            layerGroups[zoneType] = layerGroup;
            layerGroup.addTo(map);
        });

        // Add layer control
        L.control.layers(null, layerGroups, {collapsed: false}).addTo(map);

        // Hide loading indicator
        document.getElementById('loading').style.display = 'none';

        console.log('Map loaded successfully!');
    </script>
</body>
</html>
"""

    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

    file_size_mb = len(html_content.encode('utf-8')) / (1024 * 1024)

    print(f"✓ Optimized map generated successfully!")
    print(f"  File: {OUTPUT_FILE}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Segments: {total_segments:,}")
    print(f"  Total spots: {total_spots:,}")
    print("\nOptimizations applied:")
    print("  - Direct Leaflet.js (no Folium overhead)")
    print("  - Canvas rendering for better performance")
    print("  - Simplified coordinates (5 decimal places)")
    print("  - Compressed data structure")


if __name__ == "__main__":
    generate_optimized_map()
