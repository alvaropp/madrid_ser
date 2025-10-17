"""
Generate an optimized static HTML file with compressed data.
Much faster loading than the standard Folium output.
"""
import geopandas as gpd
import json

# Configuration
DATA_FILE = "data/SHP_ZIP/Bandas_de_Aparcamiento.shp"
BOUNDARY_FILE = "data/SHP_ZIP/Barrios_Zona_SER.shp"
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

    print("Loading SER boundary...")
    boundary_gdf = gpd.read_file(BOUNDARY_FILE)
    boundary_gdf = boundary_gdf.to_crs(epsg=4326)

    # Filter out areas that are NOT in the SER zone
    boundary_gdf = boundary_gdf[boundary_gdf['NOMBAR'] != 'No está en la zona SER']

    # Convert boundary polygons to simplified coordinate lists
    boundary_data = []
    for idx, row in boundary_gdf.iterrows():
        coords = list(row['geometry'].exterior.coords)
        simplified_coords = simplify_coordinates(coords)
        boundary_data.append(simplified_coords)

    print(f"  Loaded {len(boundary_data)} SER boundary polygons (filtered out non-SER areas)")

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

    # Start building HTML - using regular string concatenation to avoid f-string brace issues
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Madrid SER - Regulated Parking Zones</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            height: 100vh;
            overflow: hidden;
        }
        #map {
            width: 100%;
            height: 100%;
        }
        .info-box {
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 15px 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
        }
        .info-box h2 {
            margin: 0;
            font-size: 20px;
        }
        .info-box p {
            margin: 5px 0 0 0;
            font-size: 14px;
            color: #666;
        }
        .legend {
            position: absolute;
            bottom: 30px;
            right: 30px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            font-size: 14px;
        }
        .legend-title {
            font-weight: bold;
            margin-bottom: 10px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin: 5px 0;
        }
        .legend-line {
            width: 20px;
            height: 3px;
            margin-right: 8px;
        }
        .legend-note {
            margin-top: 10px;
            font-size: 12px;
            color: #666;
            font-style: italic;
        }
        .loading {
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
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .search-box {
            position: absolute;
            top: 80px;
            left: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            width: 350px;
        }
        .search-box h3 {
            margin: 0 0 10px 0;
            font-size: 16px;
        }
        .search-input-container {
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
            width: 100%;
        }
        .search-box input {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .search-box button {
            padding: 8px 12px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            flex-shrink: 0;
        }
        .search-box button:hover {
            background: #0056b3;
        }
        .search-box button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .search-box button.clear-btn {
            background: #6c757d;
        }
        .search-box button.clear-btn:hover {
            background: #5a6268;
        }
        .results-panel {
            max-height: 400px;
            overflow-y: auto;
            margin-top: 10px;
            display: none;
        }
        .results-panel.show {
            display: block;
        }
        .results-header {
            padding: 10px;
            font-weight: bold;
            border-bottom: 2px solid #007bff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
        }
        .results-header:hover {
            background: #f5f5f5;
        }
        .toggle-icon {
            font-size: 12px;
            color: #666;
        }
        .results-list {
            display: block;
        }
        .results-list.collapsed {
            display: none;
        }
        .result-item {
            padding: 10px;
            border-top: 1px solid #eee;
            cursor: pointer;
            transition: background 0.2s;
        }
        .result-item:hover {
            background: #f5f5f5;
        }
        .result-item strong {
            color: #007bff;
        }
        .result-distance {
            color: #666;
            font-size: 13px;
        }
        .error-message {
            color: #dc3545;
            font-size: 13px;
            margin-top: 5px;
        }
        @media (max-width: 768px) {
            .info-box {
                top: 10px;
                left: 10px;
                right: 10px;
                transform: none;
                padding: 10px 15px;
            }
            .info-box h2 {
                font-size: 16px;
            }
            .info-box p {
                font-size: 12px;
            }
            .search-box {
                width: calc(100% - 20px);
                left: 10px;
                right: 10px;
                top: 80px;
            }
            .search-box h3 {
                font-size: 14px;
            }
            .search-box input {
                font-size: 13px;
                padding: 6px;
            }
            .search-box button {
                font-size: 12px;
                padding: 6px 10px;
            }
            .legend {
                bottom: 10px;
                right: 10px;
                left: 10px;
                font-size: 11px;
                padding: 10px;
            }
            .legend-item {
                margin: 3px 0;
            }
            .result-item {
                padding: 8px;
            }
            .results-panel {
                max-height: 250px;
            }
        }
        @media (max-width: 480px) {
            .info-box {
                position: relative;
                top: 0;
                left: 0;
                right: 0;
                margin: 0;
                border-radius: 0;
            }
            .search-box {
                top: auto;
                bottom: 60px;
                left: 10px;
                right: 10px;
                width: calc(100% - 20px);
            }
            .legend {
                bottom: 10px;
                left: 10px;
                right: 10px;
                font-size: 10px;
                padding: 8px;
            }
            .legend-title {
                margin-bottom: 5px;
            }
        }
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
        <p>""" + f"{total_segments:,} segments | {total_spots:,} parking spots" + """</p>
    </div>

    <div class="search-box">
        <h3>Find Blue Parking</h3>
        <div class="search-input-container">
            <input type="text" id="addressInput" placeholder="Enter Madrid address..." />
            <button onclick="searchAddress()">Search</button>
            <button class="clear-btn" onclick="clearSearch()">Clear</button>
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

    # Embed zone data and boundary as JavaScript
    html_content += f"        const zoneData = {json.dumps(zone_data)};\n"
    html_content += f"        const zoneColors = {json.dumps(ZONE_COLORS)};\n"
    html_content += f"        const serBoundaries = {json.dumps(boundary_data)};\n"

    # JavaScript code - using regular strings to avoid brace escaping issues
    js_code = """
        // Initialize map
        const map = L.map('map', {
            center: [40.4168, -3.7038],
            zoom: 13,
            preferCanvas: true
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);

        const layerGroups = {};
        const allPolylines = {};
        let searchMarker = null;
        let highlightedPolylines = [];
        let numberMarkers = [];

        function isPointInPolygon(lat, lon, polygon) {
            let inside = false;
            for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
                const lat_i = polygon[i][0], lon_i = polygon[i][1];
                const lat_j = polygon[j][0], lon_j = polygon[j][1];
                const intersect = ((lon_i > lon) !== (lon_j > lon))
                    && (lat < (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i);
                if (intersect) inside = !inside;
            }
            return inside;
        }

        function isInRegulatedArea(lat, lon) {
            for (const boundary of serBoundaries) {
                if (isPointInPolygon(lat, lon, boundary)) {
                    return true;
                }
            }
            return false;
        }

        function calculateDistance(lat1, lon1, lat2, lon2) {
            const R = 6371e3;
            const φ1 = lat1 * Math.PI / 180;
            const φ2 = lat2 * Math.PI / 180;
            const Δφ = (lat2 - lat1) * Math.PI / 180;
            const Δλ = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                    Math.cos(φ1) * Math.cos(φ2) *
                    Math.sin(Δλ/2) * Math.sin(Δλ/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }

        async function searchAddress() {
            const input = document.getElementById('addressInput');
            const query = input.value.trim();
            const errorDiv = document.getElementById('errorMessage');
            const resultsPanel = document.getElementById('resultsPanel');

            errorDiv.textContent = '';
            resultsPanel.innerHTML = '';
            resultsPanel.classList.remove('show');

            if (!query) {
                errorDiv.textContent = 'Please enter an address';
                return;
            }

            resultsPanel.innerHTML = '<div style="padding: 10px;">Searching...</div>';
            resultsPanel.classList.add('show');

            try {
                const geocodeUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Madrid, Spain')}&limit=1`;
                const response = await fetch(geocodeUrl);
                const data = await response.json();

                if (data.length === 0) {
                    errorDiv.textContent = 'Address not found. Try a different search.';
                    resultsPanel.classList.remove('show');
                    return;
                }

                const location = data[0];
                const lat = parseFloat(location.lat);
                const lon = parseFloat(location.lon);

                if (searchMarker) {
                    map.removeLayer(searchMarker);
                }

                searchMarker = L.marker([lat, lon], {
                    icon: L.divIcon({
                        className: 'search-marker',
                        html: '<div style="background: red; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>',
                        iconSize: [12, 12]
                    })
                }).addTo(map);
                searchMarker.bindPopup(`<strong>Search Location</strong><br>${location.display_name}`).openPopup();

                if (!isInRegulatedArea(lat, lon)) {
                    errorDiv.textContent = 'This address is not in a SER-regulated area.';
                    resultsPanel.classList.remove('show');
                    map.setView([lat, lon], 14);
                    return;
                }

                findNearestBlueParking(lat, lon, location.display_name);

            } catch (error) {
                errorDiv.textContent = 'Error searching. Please try again.';
                resultsPanel.classList.remove('show');
                console.error('Search error:', error);
            }
        }

        function findNearestBlueParking(lat, lon, addressName) {
            const resultsPanel = document.getElementById('resultsPanel');

            highlightedPolylines.forEach(p => {
                p.setStyle({
                    weight: p.options.originalWeight,
                    opacity: 0.8,
                    color: p.options.originalColor
                });
            });
            highlightedPolylines = [];

            numberMarkers.forEach(marker => {
                map.removeLayer(marker);
            });
            numberMarkers = [];

            const blueSegments = zoneData['Azul'] || [];
            const distances = blueSegments.map(segment => {
                const centroid = segment.centroid;
                const distance = calculateDistance(lat, lon, centroid[0], centroid[1]);
                return {
                    segment: segment,
                    distance: distance
                };
            });

            distances.sort((a, b) => a.distance - b.distance);
            const nearest = distances.slice(0, 10);

            if (nearest.length === 0) {
                resultsPanel.innerHTML = '<div style="padding: 10px;">No blue parking zones found nearby.</div>';
            } else {
                let html = '<div class="results-header" onclick="toggleResults()"><span>Nearest Blue Zones:</span><span class="toggle-icon" id="toggleIcon">▼</span></div>';
                html += '<div class="results-list" id="resultsList">';
                nearest.forEach((item, index) => {
                    const distanceM = Math.round(item.distance);
                    const walkTime = Math.round(item.distance / 83);
                    html += `
                        <div class="result-item" onclick="highlightSegment(${item.segment.id}, ${index})">
                            <strong>${index + 1}. ${item.segment.spots} spots</strong>
                            <div class="result-distance">
                                ${distanceM}m away (~${walkTime} min walk)
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                resultsPanel.innerHTML = html;

                // Auto-collapse on small screens
                if (window.innerWidth <= 768) {
                    const resultsList = document.getElementById('resultsList');
                    const toggleIcon = document.getElementById('toggleIcon');
                    if (resultsList && toggleIcon) {
                        resultsList.classList.add('collapsed');
                        toggleIcon.textContent = '▶';
                    }
                }

                // Collect all bounds for fitting the map view
                const allBounds = [];

                nearest.forEach((item, index) => {
                    const polyline = allPolylines[item.segment.id];
                    if (polyline) {
                        polyline.setStyle({
                            weight: 8,
                            opacity: 1,
                            color: '#ff6b6b'
                        });
                        highlightedPolylines.push(polyline);

                        const centroid = item.segment.centroid;
                        const marker = L.marker([centroid[0], centroid[1]], {
                            icon: L.divIcon({
                                className: 'number-marker',
                                html: `<div style="background: #007bff; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${index + 1}</div>`,
                                iconSize: [24, 24]
                            })
                        }).addTo(map);
                        numberMarkers.push(marker);

                        // Add to bounds
                        allBounds.push([centroid[0], centroid[1]]);
                    }
                });

                // Add search marker location to bounds
                allBounds.push([lat, lon]);

                // Fit map to show all markers
                if (allBounds.length > 0) {
                    const bounds = L.latLngBounds(allBounds);
                    map.fitBounds(bounds, {
                        padding: [50, 50],
                        maxZoom: 16
                    });
                }
            }

            resultsPanel.classList.add('show');
        }

        function highlightSegment(segmentId, index) {
            const polyline = allPolylines[segmentId];
            if (polyline) {
                polyline.setStyle({ weight: 12, opacity: 1 });
                setTimeout(() => polyline.setStyle({ weight: 8, opacity: 1 }), 200);
                setTimeout(() => polyline.setStyle({ weight: 12, opacity: 1 }), 400);
                setTimeout(() => polyline.setStyle({ weight: 8, opacity: 1 }), 600);

                const bounds = polyline.getBounds();
                map.fitBounds(bounds, { padding: [50, 50] });

                polyline.openPopup();
            }
        }

        function toggleResults() {
            const resultsList = document.getElementById('resultsList');
            const toggleIcon = document.getElementById('toggleIcon');
            if (resultsList && toggleIcon) {
                resultsList.classList.toggle('collapsed');
                toggleIcon.textContent = resultsList.classList.contains('collapsed') ? '▶' : '▼';
            }
        }

        function clearSearch() {
            // Clear input
            document.getElementById('addressInput').value = '';

            // Clear error message
            document.getElementById('errorMessage').textContent = '';

            // Hide results panel
            document.getElementById('resultsPanel').classList.remove('show');
            document.getElementById('resultsPanel').innerHTML = '';

            // Remove search marker
            if (searchMarker) {
                map.removeLayer(searchMarker);
                searchMarker = null;
            }

            // Reset highlighted polylines
            highlightedPolylines.forEach(p => {
                p.setStyle({
                    weight: p.options.originalWeight,
                    opacity: 0.8,
                    color: p.options.originalColor
                });
            });
            highlightedPolylines = [];

            // Remove number markers
            numberMarkers.forEach(marker => {
                map.removeLayer(marker);
            });
            numberMarkers = [];

            // Reset map view
            map.setView([40.4168, -3.7038], 13);
        }

        document.getElementById('addressInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchAddress();
            }
        });

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
                allPolylines[segment.id] = polyline;
            });

            layerGroups[zoneType] = layerGroup;
            layerGroup.addTo(map);
        });

        L.control.layers(null, layerGroups, {collapsed: false}).addTo(map);
        document.getElementById('loading').style.display = 'none';
        console.log('Map loaded successfully!');
    </script>
</body>
</html>
"""

    html_content += js_code

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
    print("  - SER boundary checking for address validation")


if __name__ == "__main__":
    generate_optimized_map()
