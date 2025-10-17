import geopandas as gpd
from flask import Flask, jsonify, render_template, request
import folium

app = Flask(__name__)

# Configuration
DATA_FILE = "data/SHP_ZIP/Bandas_de_Aparcamiento.shp"

# Color mapping for zone types
ZONE_COLORS = {
    'Verde': '#28a745',      # Green
    'Azul': '#007bff',       # Blue
    'Naranja': '#fd7e14',    # Orange
    'Rojo': '#dc3545',       # Red
    'Alta Rotación': '#6f42c1',  # Purple
}


def load_data(sample_size=None):
    """Load parking segment data from shapefile"""
    # Read shapefile
    gdf = gpd.read_file(DATA_FILE)

    # Convert to WGS84 (EPSG:4326) for Folium
    gdf = gdf.to_crs(epsg=4326)

    # Sample data if requested
    if sample_size and sample_size < len(gdf):
        gdf = gdf.sample(n=sample_size, random_state=42)

    # Clean up the data
    gdf['Color'] = gdf['Color'].fillna('Unknown')
    gdf['Res_NumPla'] = gdf['Res_NumPla'].fillna(0).astype(int)

    return gdf


def create_map(gdf):
    """Create Folium map with parking segments from shapefile"""
    # Initialize map centered on Madrid
    madrid_map = folium.Map(
        location=[40.4168, -3.7038],
        zoom_start=13,
        tiles="OpenStreetMap"
    )

    # Create feature groups for each zone type
    zone_groups = {}
    for zone_type in gdf['Color'].unique():
        if zone_type:
            zone_groups[zone_type] = folium.FeatureGroup(name=zone_type)

    # Add each parking segment as a line
    for idx, row in gdf.iterrows():
        zone_type = row['Color']
        num_spots = row['Res_NumPla']
        parking_type = row['Bateria_Li']

        # Get color for this zone type
        color = ZONE_COLORS.get(zone_type, '#6c757d')

        # Calculate line weight based on number of spots
        weight = min(max(num_spots * 0.3, 3), 10)

        # Extract coordinates from LineString geometry
        coords = list(row['geometry'].coords)
        # Convert to lat/lon format for Folium (swap x,y to lat,lon)
        # Handle 3D coordinates (x, y, z) by ignoring z
        line_coords = [[lat, lon] for lon, lat, *_ in coords]

        # Create popup content
        popup_html = f"""
        <div style="font-family: Arial; min-width: 150px;">
            <h4 style="margin: 0 0 10px 0; color: {color};">{zone_type}</h4>
            <p style="margin: 5px 0;"><strong>Spots:</strong> {num_spots}</p>
            <p style="margin: 5px 0;"><strong>Type:</strong> {parking_type}</p>
            <p style="margin: 5px 0;"><strong>Segment ID:</strong> {row['ID']}</p>
        </div>
        """

        # Add polyline segment
        folium.PolyLine(
            line_coords,
            color=color,
            weight=weight,
            opacity=0.8,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{zone_type}: {num_spots} spots"
        ).add_to(zone_groups.get(zone_type, madrid_map))

    # Add all feature groups to map
    for group in zone_groups.values():
        group.add_to(madrid_map)

    # Add layer control
    folium.LayerControl().add_to(madrid_map)

    # Add legend
    legend_html = """
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 200px; height: auto;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <p style="margin: 0 0 10px 0;"><strong>Zone Types</strong></p>
    """

    for zone_type in sorted([z for z in gdf['Color'].unique() if z]):
        color = ZONE_COLORS.get(zone_type, '#6c757d')
        legend_html += f'<p style="margin: 5px 0;"><span style="background-color:{color}; width:20px; height:3px; display:inline-block; margin-right:5px;"></span>{zone_type}</p>'

    legend_html += '<p style="margin: 10px 0 5px 0; font-size: 12px; font-style: italic;">Line thickness = number of spots</p>'
    legend_html += '</div>'
    madrid_map.get_root().html.add_child(folium.Element(legend_html))

    return madrid_map


@app.route("/")
def index():
    """Main page"""
    return render_template("index.html")


@app.route("/map")
def get_map():
    """Generate and return the map"""
    sample_size = request.args.get("sample", default=None, type=int)

    print(f"Loading data (sample_size={sample_size})...")
    df = load_data(sample_size=sample_size)
    print(f"Loaded {len(df)} parking segments")

    madrid_map = create_map(df)

    # Return map as HTML
    return madrid_map._repr_html_()


@app.route("/stats")
def get_stats():
    """Get statistics about the data"""
    gdf = load_data()

    # Calculate stats by zone type
    zone_stats = gdf.groupby('Color').agg({
        'Res_NumPla': ['count', 'sum']
    }).round(0)

    zone_stats.columns = ['segments', 'total_spots']
    zone_stats = zone_stats.reset_index()
    zone_stats.columns = ['zone_type', 'segments', 'total_spots']
    zone_stats = zone_stats.to_dict('records')

    stats = {
        "total_segments": len(gdf),
        "total_spots": int(gdf['Res_NumPla'].sum()),
        "zone_types": zone_stats
    }

    return jsonify(stats)


if __name__ == "__main__":
    print("Starting Madrid SER Parking Visualization App...")
    print(f"Data file: {DATA_FILE}")
    print("Loading data...")

    # Quick data check
    gdf = load_data(sample_size=100)
    print(f"Sample loaded: {len(gdf)} parking segments")
    print(f"Zone types: {sorted([z for z in gdf['Color'].unique() if z])}")

    app.run(debug=True, host="0.0.0.0", port=5001)
