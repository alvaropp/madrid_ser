"""
Generate a static HTML file with all parking data embedded.
Run this script once to create the map, then serve it directly.
"""
import geopandas as gpd
import folium

# Configuration
DATA_FILE = "data/SHP_ZIP/Bandas_de_Aparcamiento.shp"
OUTPUT_FILE = "static_map.html"

# Color mapping for zone types
ZONE_COLORS = {
    'Verde': '#28a745',      # Green
    'Azul': '#007bff',       # Blue
    'Naranja': '#fd7e14',    # Orange
    'Rojo': '#dc3545',       # Red
    'Alta Rotación': '#6f42c1',  # Purple
}


def style_function(feature):
    """Style function for GeoJSON features"""
    zone_type = feature['properties']['Color']
    num_spots = feature['properties']['Res_NumPla']

    color = ZONE_COLORS.get(zone_type, '#6c757d')
    weight = min(max(num_spots * 0.3, 3), 10)

    return {
        'color': color,
        'weight': weight,
        'opacity': 0.8
    }


def generate_map():
    """Generate static map with all data embedded"""
    print("Loading parking segments from shapefile...")
    gdf = gpd.read_file(DATA_FILE)

    print(f"Converting {len(gdf)} segments to WGS84...")
    gdf = gdf.to_crs(epsg=4326)

    # Clean up the data
    gdf['Color'] = gdf['Color'].fillna('Unknown')
    gdf['Res_NumPla'] = gdf['Res_NumPla'].fillna(0).astype(int)

    print("Creating map...")
    madrid_map = folium.Map(
        location=[40.4168, -3.7038],
        zoom_start=13,
        tiles="OpenStreetMap"
    )

    # Add each zone type as a separate GeoJSON layer
    for zone_type in sorted([z for z in gdf['Color'].unique() if z]):
        print(f"  Adding {zone_type} layer...")
        zone_gdf = gdf[gdf['Color'] == zone_type].copy()

        folium.GeoJson(
            zone_gdf,
            name=zone_type,
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=['Color', 'Res_NumPla'],
                aliases=['Zone:', 'Spots:'],
                localize=True
            ),
            popup=folium.GeoJsonPopup(
                fields=['Color', 'Res_NumPla', 'Bateria_Li', 'ID'],
                aliases=['Zone:', 'Spots:', 'Type:', 'ID:'],
                localize=True
            )
        ).add_to(madrid_map)

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

    # Add title and stats header
    title_html = """
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                background-color: white; padding: 15px 30px; z-index:9999;
                border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.2);">
        <h2 style="margin: 0; font-family: Arial;">Madrid SER - Regulated Parking Zones</h2>
        <p style="margin: 5px 0 0 0; font-size: 14px; color: #666;">
            {total_segments:,} segments | {total_spots:,} parking spots
        </p>
    </div>
    """.format(
        total_segments=len(gdf),
        total_spots=int(gdf['Res_NumPla'].sum())
    )
    madrid_map.get_root().html.add_child(folium.Element(title_html))

    print(f"Saving to {OUTPUT_FILE}...")
    madrid_map.save(OUTPUT_FILE)

    print(f"✓ Static map generated successfully!")
    print(f"  File: {OUTPUT_FILE}")
    print(f"  Segments: {len(gdf):,}")
    print(f"  Total spots: {int(gdf['Res_NumPla'].sum()):,}")
    print("\nYou can now open this file directly in a browser - no server needed!")


if __name__ == "__main__":
    generate_map()
