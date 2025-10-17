# Madrid SER - Regulated Parking Zones Visualization

Interactive map showing all regulated parking zones (SER - Servicio de Estacionamiento Regulado) in Madrid with color-coded segments and parking spot counts.


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
