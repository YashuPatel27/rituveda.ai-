# RituVeda AI — Data sources and validation

Historical ML training uses Open-Meteo Historical Weather API, ERA5 by default (global, approximately 0.1° / 9–11 km grid). ERA5 is an alternative for long-term climate consistency. Live forecast is a separate Open-Meteo forecast product.

NOAA GHCN-Daily station observations are recommended for independent validation where a nearby station has sufficient quality-controlled coverage. No NOAA validation score is claimed until those records are downloaded, matched and evaluated.

Train from the project root:
```powershell
python -m ml.data_pipeline --city Patna --years 10 --model era5
python -m ml.train_models --data datasets/weather_history.csv
python -m unittest discover -s tests -v
```

Use chronological holdout, not random splitting. Report temperature MAE/RMSE and rainfall precision/recall/F1/confusion matrix. Missing rainfall targets are excluded, not treated as zero. Metrics apply only to the city, dataset and test period. Train a separate model per city before showing that city's ML output.

Open-Meteo data is CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
Attribution: Weather data by Open-Meteo.com — https://open-meteo.com/
Hosted free API is intended for non-commercial use; check current terms before commercial deployment.
NOAA GHCN-Daily: https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily
