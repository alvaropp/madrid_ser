# Madrid SER - Regulated Parking Zones Visualization

Interactive map showing all regulated parking zones (SER - Servicio de Estacionamiento Regulado) in Madrid with color-coded segments and parking spot counts.

## Features

- **34,102 parking segments** across Madrid
- **179,031 total parking spots**
- **Color-coded zones**: Verde (Green), Azul (Blue), Naranja (Orange), Rojo (Red), Alta Rotación (Purple)
- **Address Search**: Find nearest blue parking zones from any Madrid address
  - Shows top 10 nearest zones with distances and walking time
  - Visual highlighting and numbered markers on map
  - Click results to zoom and view details
- **Interactive**: Click segments for details, toggle layers on/off
- **Line thickness** represents number of parking spots

## Live Map

View the interactive map at: **https://alvaropp.github.io/madrid_ser/**

## Updating the Map

When you have new data and want to update the live map:

```bash
# Install dependencies (first time only)
pip install -r requirements.txt

# Generate and deploy the updated map to GitHub Pages
./deploy.sh
```

This will:
1. Generate a new `index.html` with the latest data
2. Push it to the `gh-pages` branch
3. Update the live website automatically


### Data Sources

- `data/calles_SER_2025.csv` comes from
https://datos.madrid.es/portal/site/egob/menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/?vgnextoid=4973b0dd4a872510VgnVCM1000000b205a0aRCRD&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD&vgnextfmt=default.
- `data/SHP_ZIP` comes from https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=9506daa5-e317-11ec-8359-60634c31c0aa# under 'Descargas'.
