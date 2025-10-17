# Madrid SER - Regulated Parking Zones Visualization

Interactive map showing all regulated parking zones (SER - Servicio de Estacionamiento Regulado) in Madrid with color-coded segments and parking spot counts.

## Quick Start

Simply open `static_map.html` in your browser - no installation or server required!

## Map Features

- **34,102 parking segments** across Madrid
- **179,031 total parking spots**
- **Color-coded zones**: Verde (Green), Azul (Blue), Naranja (Orange), Rojo (Red), Alta Rotación (Purple)
- **Interactive**: Click segments for details, toggle layers on/off
- **Line thickness** represents number of parking spots

## Regenerating the Map

If you need to update the map with new data:

```bash
# Install dependencies
pip install -r requirements.txt

# Regenerate the static map
python generate_static_map.py
```

This will create a new `static_map.html` with all data embedded.

<CLAUDE DO NOT TOUCH>

### Data Sources

- `data/calles_SER_2025.csv` comes from
https://datos.madrid.es/portal/site/egob/menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/?vgnextoid=4973b0dd4a872510VgnVCM1000000b205a0aRCRD&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD&vgnextfmt=default.
- `data/SHP_ZIP` comes from https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=9506daa5-e317-11ec-8359-60634c31c0aa# under 'Descargas'.
