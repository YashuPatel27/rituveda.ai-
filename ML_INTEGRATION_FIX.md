# RituVeda AI — Nationwide ML correction

The earlier version collected and trained on one city at a time (default Patna). This release replaces that flow with a resumable multi-location India pipeline.

1. `datasets/india_cities.csv` lists 100+ representative locations across all States and UTs.
2. `python -m ml.data_pipeline --years 10` collects ERA5 daily data for each location and saves incrementally.
3. `python -m ml.train_models --data datasets/weather_history.csv` trains one nationwide temperature regressor and rainfall classifier.
4. The app's ML panel loads these national models and uses selected location coordinates and recent local archive history.

ERA5 is reanalysis, not direct station observations. The app must keep ML output separate from external weather forecasts and official IMD bulletins. The current app does not claim IMD API integration unless valid official access has been configured and verified.
