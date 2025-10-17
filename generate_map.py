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

    # Start building HTML
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Madrid SER - Regulated Parking Zones</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
        }
        #map {
            height: 100vh;
            width: 100%;
        }
        .overlay-panel {
            position: absolute;
            z-index: 1000;
            max-height: 80vh;
            overflow-y: auto;
        }
        .top-left {
            top: 10px;
            left: 10px;
            max-width: 350px;
        }
        .bottom-right {
            bottom: 40px;
            right: 10px;
            max-width: 250px;
        }
        .result-item {
            cursor: pointer;
            transition: background 0.2s;
        }
        .result-item:hover {
            background: #f8f9fa;
        }
        @media (max-width: 768px) {
            .top-left {
                max-width: calc(100vw - 20px);
                max-height: 50vh;
            }
            .bottom-right {
                bottom: 10px;
                right: 10px;
                left: 10px;
                max-width: none;
                font-size: 0.85rem;
            }
        }
    </style>
</head>
<body>
    <div id="map"></div>

    <!-- Info & Search Panel -->
    <div class="overlay-panel top-left">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Madrid SER - Parking</h5>
                <small>""" + f"{total_segments:,} segments | {total_spots:,} spots" + """</small>
            </div>
            <div class="card-body">
                <h6>Find Blue Parking</h6>
                <div class="input-group mb-2">
                    <input type="text" class="form-control" id="addressInput" placeholder="Enter Madrid address...">
                    <button class="btn btn-primary" onclick="searchAddress()">Search</button>
                    <button class="btn btn-secondary" onclick="clearSearch()">Clear</button>
                </div>
                <div id="errorMessage" class="text-danger small"></div>
                <div id="resultsPanel" class="mt-2" style="display: none;">
                    <div class="d-grid">
                        <button class="btn btn-sm btn-outline-primary" type="button" data-bs-toggle="collapse" data-bs-target="#resultsList">
                            <span id="resultsTitle">Nearest Blue Zones</span>
                            <span id="toggleIcon">▼</span>
                        </button>
                    </div>
                    <div class="collapse show" id="resultsList"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Legend -->
    <div class="overlay-panel bottom-right">
        <div class="card shadow-sm">
            <div class="card-body p-2">
                <div class="d-grid mb-1">
                    <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#legendContent">
                        <span>Zone Types</span>
                    </button>
                </div>
                <div class="collapse" id="legendContent">
"""

    for zone_type in sorted(ZONE_COLORS.keys()):
        if zone_type != 'Unknown':
            color = ZONE_COLORS[zone_type]
            html_content += f"""                    <div class="d-flex align-items-center mb-1">
                        <div style="width: 20px; height: 3px; background: {color}; margin-right: 8px;"></div>
                        <small>{zone_type}</small>
                    </div>
"""

    html_content += """                    <small class="text-muted fst-italic">Line thickness = spots</small>
                </div>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
"""

    # Embed zone data and boundary as JavaScript
    html_content += f"        const zoneData = {json.dumps(zone_data)};\n"
    html_content += f"        const zoneColors = {json.dumps(ZONE_COLORS)};\n"
    html_content += f"        const serBoundaries = {json.dumps(boundary_data)};\n"

    # JavaScript code
    js_code = """
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
            resultsPanel.style.display = 'none';

            if (!query) {
                errorDiv.textContent = 'Please enter an address';
                return;
            }

            errorDiv.textContent = 'Searching...';

            try {
                const geocodeUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Madrid, Spain')}&limit=1`;
                const response = await fetch(geocodeUrl);
                const data = await response.json();

                if (data.length === 0) {
                    errorDiv.textContent = 'Address not found.';
                    return;
                }

                errorDiv.textContent = '';
                const location = data[0];
                const lat = parseFloat(location.lat);
                const lon = parseFloat(location.lon);

                if (searchMarker) {
                    map.removeLayer(searchMarker);
                }

                searchMarker = L.marker([lat, lon], {
                    icon: L.divIcon({
                        className: 'search-marker',
                        html: '<div style="background: red; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                        iconSize: [20, 20]
                    })
                }).addTo(map);
                searchMarker.bindPopup(`<strong>Search Location</strong><br>${location.display_name}`);

                if (!isInRegulatedArea(lat, lon)) {
                    errorDiv.textContent = 'This address is not in a SER-regulated area.';
                    map.setView([lat, lon], 14);
                    return;
                }

                findNearestBlueParking(lat, lon, location.display_name);

            } catch (error) {
                errorDiv.textContent = 'Error searching. Please try again.';
                console.error('Search error:', error);
            }
        }

        function findNearestBlueParking(lat, lon, addressName) {
            const resultsPanel = document.getElementById('resultsPanel');
            const resultsList = document.getElementById('resultsList');

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
                resultsList.innerHTML = '<p class="text-muted p-2">No blue parking zones found nearby.</p>';
            } else {
                let html = '<div class="list-group list-group-flush">';
                nearest.forEach((item, index) => {
                    const distanceM = Math.round(item.distance);
                    const walkTime = Math.round(item.distance / 83);
                    html += `
                        <div class="list-group-item list-group-item-action result-item p-2" onclick="highlightSegment(${item.segment.id}, ${index})">
                            <div class="d-flex justify-content-between">
                                <strong class="text-primary">${index + 1}. ${item.segment.spots} spots</strong>
                                <small class="text-muted">${distanceM}m (~${walkTime} min)</small>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                resultsList.innerHTML = html;

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

                        allBounds.push([centroid[0], centroid[1]]);
                    }
                });

                allBounds.push([lat, lon]);

                if (allBounds.length > 0) {
                    const bounds = L.latLngBounds(allBounds);
                    map.fitBounds(bounds, {
                        padding: [50, 50],
                        maxZoom: 16
                    });
                }
            }

            resultsPanel.style.display = 'block';
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

        function clearSearch() {
            document.getElementById('addressInput').value = '';
            document.getElementById('errorMessage').textContent = '';
            document.getElementById('resultsPanel').style.display = 'none';

            if (searchMarker) {
                map.removeLayer(searchMarker);
                searchMarker = null;
            }

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
                        <h6 style="color: ${color};">${zoneType}</h6>
                        <p class="mb-1"><strong>Spots:</strong> ${segment.spots}</p>
                        <p class="mb-1"><strong>Type:</strong> ${segment.type}</p>
                        <p class="mb-0"><strong>ID:</strong> ${segment.id}</p>
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
    print("  - Bootstrap 5 responsive framework")


if __name__ == "__main__":
    generate_optimized_map()
