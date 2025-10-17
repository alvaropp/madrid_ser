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


def calculate_centroid(coords):
    """Calculate the centroid of a line segment"""
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return [sum(lats) / len(lats), sum(lons) / len(lons)]


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

            feature = {
                'coords': simplified_coords,
                'spots': int(row['Res_NumPla']),
                'type': str(row['Bateria_Li']) if row['Bateria_Li'] else 'N/A',
                'id': int(row['ID']),
                'centroid': calculate_centroid(simplified_coords)
            }
            features.append(feature)

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
        .search-box {{
            position: absolute;
            top: 80px;
            left: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            width: 300px;
        }}
        .search-box h3 {{
            margin: 0 0 10px 0;
            font-size: 16px;
        }}
        .search-input-container {{
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
        }}
        .search-box input {{
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        .search-box button {{
            padding: 8px 15px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        .search-box button:hover {{
            background: #0056b3;
        }}
        .search-box button:disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}
        .results-panel {{
            max-height: 400px;
            overflow-y: auto;
            margin-top: 10px;
            display: none;
        }}
        .results-panel.show {{
            display: block;
        }}
        .result-item {{
            padding: 10px;
            border-top: 1px solid #eee;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .result-item:hover {{
            background: #f5f5f5;
        }}
        .result-item strong {{
            color: #007bff;
        }}
        .result-distance {{
            color: #666;
            font-size: 13px;
        }}
        .error-message {{
            color: #dc3545;
            font-size: 13px;
            margin-top: 5px;
        }}
        @media (max-width: 768px) {{
            .search-box {{
                width: calc(100% - 20px);
                left: 10px;
                right: 10px;
            }}
            .legend {{
                bottom: 10px;
                right: 10px;
                font-size: 12px;
            }}
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

    <div class="search-box">
        <h3>Find Blue Parking</h3>
        <div class="search-input-container">
            <input type="text" id="addressInput" placeholder="Enter Madrid address..." />
            <button onclick="searchAddress()">Search</button>
        </div>
        <div id="errorMessage" class="error-message"></div>
        <div id="resultsPanel" class="results-panel"></div>
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
        const allPolylines = {}; // Store polylines for highlighting

        // Variables for search functionality
        let searchMarker = null;
        let highlightedPolylines = [];

        // Calculate distance between two points (Haversine formula)
        function calculateDistance(lat1, lon1, lat2, lon2) {{
            const R = 6371e3; // Earth radius in meters
            const φ1 = lat1 * Math.PI / 180;
            const φ2 = lat2 * Math.PI / 180;
            const Δφ = (lat2 - lat1) * Math.PI / 180;
            const Δλ = (lon2 - lon1) * Math.PI / 180;

            const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                    Math.cos(φ1) * Math.cos(φ2) *
                    Math.sin(Δλ/2) * Math.sin(Δλ/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

            return R * c; // Distance in meters
        }}

        // Search for address using Nominatim
        async function searchAddress() {{
            const input = document.getElementById('addressInput');
            const query = input.value.trim();
            const errorDiv = document.getElementById('errorMessage');
            const resultsPanel = document.getElementById('resultsPanel');

            errorDiv.textContent = '';
            resultsPanel.innerHTML = '';
            resultsPanel.classList.remove('show');

            if (!query) {{
                errorDiv.textContent = 'Please enter an address';
                return;
            }}

            // Show loading
            resultsPanel.innerHTML = '<div style="padding: 10px;">Searching...</div>';
            resultsPanel.classList.add('show');

            try {{
                // Geocode address using Nominatim
                const geocodeUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${{encodeURIComponent(query + ', Madrid, Spain')}}&limit=1`;
                const response = await fetch(geocodeUrl);
                const data = await response.json();

                if (data.length === 0) {{
                    errorDiv.textContent = 'Address not found. Try a different search.';
                    resultsPanel.classList.remove('show');
                    return;
                }}

                const location = data[0];
                const lat = parseFloat(location.lat);
                const lon = parseFloat(location.lon);

                // Find nearest blue parking zones
                findNearestBlueParking(lat, lon, location.display_name);

            }} catch (error) {{
                errorDiv.textContent = 'Error searching. Please try again.';
                resultsPanel.classList.remove('show');
                console.error('Search error:', error);
            }}
        }}

        // Find nearest blue parking zones
        function findNearestBlueParking(lat, lon, addressName) {{
            const resultsPanel = document.getElementById('resultsPanel');

            // Clear previous search marker
            if (searchMarker) {{
                map.removeLayer(searchMarker);
            }}

            // Clear previous highlights
            highlightedPolylines.forEach(p => {{
                p.setStyle({{
                    weight: p.options.originalWeight,
                    opacity: 0.8,
                    color: p.options.originalColor
                }});
            }});
            highlightedPolylines = [];

            // Add marker at searched location
            searchMarker = L.marker([lat, lon], {{
                icon: L.divIcon({{
                    className: 'search-marker',
                    html: '<div style="background: red; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>',
                    iconSize: [12, 12]
                }})
            }}).addTo(map);
            searchMarker.bindPopup(`<strong>Search Location</strong><br>${{addressName}}`).openPopup();

            // Zoom to location
            map.setView([lat, lon], 16);

            // Calculate distances to all blue parking segments
            const blueSegments = zoneData['Azul'] || [];
            const distances = blueSegments.map(segment => {{
                const centroid = segment.centroid;
                const distance = calculateDistance(lat, lon, centroid[0], centroid[1]);
                return {{
                    segment: segment,
                    distance: distance
                }};
            }});

            // Sort by distance and take top 10
            distances.sort((a, b) => a.distance - b.distance);
            const nearest = distances.slice(0, 10);

            // Display results
            if (nearest.length === 0) {{
                resultsPanel.innerHTML = '<div style="padding: 10px;">No blue parking zones found nearby.</div>';
            }} else {{
                let html = '<div style="padding: 10px; font-weight: bold; border-bottom: 2px solid #007bff;">Nearest Blue Zones:</div>';
                nearest.forEach((item, index) => {{
                    const distanceM = Math.round(item.distance);
                    const walkTime = Math.round(item.distance / 83); // 5 km/h = 83 m/min
                    html += `
                        <div class="result-item" onclick="highlightSegment(${{item.segment.id}}, ${{index}})">
                            <strong>${{index + 1}}. ${{item.segment.spots}} spots</strong>
                            <div class="result-distance">
                                ${{distanceM}}m away (~${{walkTime}} min walk)
                            </div>
                        </div>
                    `;
                }});
                resultsPanel.innerHTML = html;

                // Highlight the nearest zones on map
                nearest.slice(0, 5).forEach((item, index) => {{
                    const polyline = allPolylines[item.segment.id];
                    if (polyline) {{
                        polyline.setStyle({{
                            weight: 8,
                            opacity: 1,
                            color: '#ff6b6b'
                        }});
                        highlightedPolylines.push(polyline);

                        // Add numbered marker at segment centroid
                        const centroid = item.segment.centroid;
                        L.marker([centroid[0], centroid[1]], {{
                            icon: L.divIcon({{
                                className: 'number-marker',
                                html: `<div style="background: #007bff; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${{index + 1}}</div>`,
                                iconSize: [24, 24]
                            }})
                        }}).addTo(map);
                    }}
                }});
            }}

            resultsPanel.classList.add('show');
        }}

        // Highlight a specific segment when clicked from results
        function highlightSegment(segmentId, index) {{
            const polyline = allPolylines[segmentId];
            if (polyline) {{
                // Flash animation
                polyline.setStyle({{ weight: 12, opacity: 1 }});
                setTimeout(() => polyline.setStyle({{ weight: 8, opacity: 1 }}), 200);
                setTimeout(() => polyline.setStyle({{ weight: 12, opacity: 1 }}), 400);
                setTimeout(() => polyline.setStyle({{ weight: 8, opacity: 1 }}), 600);

                // Pan to segment
                const bounds = polyline.getBounds();
                map.fitBounds(bounds, {{ padding: [50, 50] }});

                // Open popup
                polyline.openPopup();
            }}
        }}

        // Allow search on Enter key
        document.getElementById('addressInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchAddress();
            }}
        }});

        // Add segments to map
        Object.keys(zoneData).forEach(zoneType => {
            const color = zoneColors[zoneType] || '#6c757d';
            const layerGroup = L.layerGroup();

            zoneData[zoneType].forEach(segment => {
                const weight = Math.min(Math.max(segment.spots * 0.3, 3), 10);

                const polyline = L.polyline(segment.coords, {
                    color: color,
                    weight: weight,
                    opacity: 0.8,
                    originalColor: color,
                    originalWeight: weight
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

                // Store polyline for later highlighting
                allPolylines[segment.id] = polyline;
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
