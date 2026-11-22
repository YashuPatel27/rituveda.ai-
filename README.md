# RituVeda AI — SIH26068

Conversational weather, air-quality and climate-information dashboard with **your own trainable machine-learning models**.

## Included features

- Existing Streamlit dashboard, city geocoding, current weather and 7-day forecast.
- Existing rule-based weather assistant and optional Gemini API integration.
- English, common Hinglish and common Devanagari weather questions.
- Weather, rainfall, heat, wind and UV threshold alerts.
- Open-Meteo Air Quality API: modelled US AQI, European AQI, PM2.5, PM10, CO, NO2, SO2, O3 and UV.
- Optional CPCB/data.gov.in adapter. This requires your own data.gov.in API key and a suitable resource ID; the adapter does not fabricate station readings.
- City-to-city current weather comparison.
- Multi-year climate history and annual temperature/rainfall summaries.
- Two independently trained local ML models:
  - Random Forest regression: next-observation maximum and minimum temperature.
  - Random Forest classification: next-observation rain/no-rain probability.
- Chronological holdout evaluation with MAE, RMSE, R², accuracy, precision, recall, F1 and confusion matrix.
- Saved model artifacts under `models/` and a JSON evaluation report.

## Important distinction: forecast API vs your own model

Open-Meteo supplies live weather observations/forecasts and historical training data. The Random Forest models are trained locally by running the scripts below. The local ML output is displayed separately from the Open-Meteo forecast. It predicts the day after the latest available historical archive observation; archive data is delayed, so this may not be tomorrow. Do not describe the model as trained until the training commands have completed successfully and model files/evaluation report exist.

Open-Meteo air-quality outputs are modelled estimates, not direct CPCB monitoring-station readings. The CPCB/data.gov.in connection is optional and resource-specific. An official CPCB reading should only be claimed when a valid CPCB-linked resource, station and timestamp are actually returned.

## Recommended setup on Windows

Python 3.11 or 3.12 is recommended for broad scientific-package compatibility. Python 3.14 may work if compatible wheels are available for all dependencies.

1. Extract the ZIP.
2. Open the extracted `RituVeda AI_Upgraded` folder in VS Code.
3. Open Terminal in that folder.
4. Create and activate a virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. Alternatively use Command Prompt: `.venv\Scripts\activate.bat`.

5. Upgrade pip and install packages:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

6. Start the dashboard:

   ```powershell
   python -m streamlit run app.py
   ```

7. Open the local URL printed by Streamlit (usually `http://localhost:8501`). If port 8501 is busy, use `python -m streamlit run app.py --server.port 8503`.

## Train your own India-wide models (100+ locations)

The included `datasets/india_cities.csv` contains 100+ representative Indian cities, covering all States and Union Territories. It is not every Indian settlement; add more rows to expand coverage.

Run from the project root (same folder as `app.py`):

```powershell
python -m ml.data_pipeline --years 10
python -m ml.train_models --data datasets/weather_history.csv
```

The collector downloads ERA5 daily history for every listed location and saves after each city. If the download is interrupted, run the same command again: completed cities are skipped. To start fresh, delete `datasets/weather_history.csv` first or use `--no-resume`.

Generated outputs:
- `datasets/weather_history.csv` — multi-city daily history with city, state and coordinates.
- `models/temperature_model.joblib` — nationwide next-day maximum/minimum temperature regressor.
- `models/rainfall_model.joblib` — nationwide next-day rain/no-rain classifier.
- `models/evaluation.json` — chronological holdout metrics and exact coverage metadata.

The model uses each city's past observations, rolling means, seasonal features and latitude/longitude. Training uses a chronological date split (not a random row split). To keep RAM use manageable on a typical laptop, the training stage caps sampled rows per city. It is one regional model trained on the entire listed Indian city set, not a separate Patna-only model. The app applies the trained model to the selected city's recent archive history and coordinates.

The target is the next available daily ERA5 reanalysis record. Archive data is delayed, so do not describe the result as a guaranteed live tomorrow forecast. Do not claim the model is trained until both `.joblib` files and `evaluation.json` exist after successful execution. Report the metrics exactly as generated; never invent accuracy.

## AQI sources

### Open-Meteo (works without an API key)

The app requests the Open-Meteo Air Quality API for modelled AQI and pollutant estimates. See https://open-meteo.com/en/docs/air-quality-api.

### CPCB / data.gov.in (optional)

The adapter requires a data.gov.in API key and a resource ID for a dataset that exposes CPCB-linked station observations. Create a local `.env` from `.env.example` only as a reminder; this project does not automatically load `.env`. Set environment variables in PowerShell before starting Streamlit:

```powershell
$env:DATA_GOV_IN_API_KEY="YOUR_DATA_GOV_IN_KEY"
$env:CPCB_RESOURCE_ID="YOUR_RESOURCE_ID"
$env:CPCB_STATE="Bihar"
$env:CPCB_CITY="Patna"
python -m streamlit run app.py
```

The data.gov.in API is resource-specific. Verify the chosen resource's actual field names and filters in its portal documentation; adjust `get_cpcb_data()` in `modules/air_quality.py` if that resource uses different filter names. Do not treat missing CPCB configuration as a zero AQI.

## Optional Gemini assistant

The local assistant works without a Gemini key. To enable Gemini, create a key at https://aistudio.google.com/apikey and set it in the same PowerShell terminal:

```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_KEY"
python -m streamlit run app.py
```

Never commit API keys or place them directly in source code. Gemini output is generative; the assistant prompt instructs it to use supplied weather/air data and avoid inventing measurements.

## Example questions and checks

- `Will it rain tomorrow?`
- `Should I carry an umbrella?`
- `Kal baarish hogi kya?`
- `कल बारिश होगी क्या?`
- `AQI kya hai?`
- `What is the UV index?`
- `Compare today's weather with Friday.`

## Run existing tests

```powershell
python -m unittest discover -s tests -v
```

## Project structure

```text
RituVeda AI_Upgraded/
├── app.py
├── requirements.txt
├── modules/
│   ├── weather.py
│   ├── air_quality.py
│   ├── alerts.py
│   ├── assistant.py
│   └── predictions.py
├── ml/
│   ├── data_pipeline.py
│   └── train_models.py
├── datasets/
├── models/
└── tests/
```

## Limitations and responsible use

- The application is an educational prototype, not an official meteorological or medical warning service.
- Open-Meteo forecasts and air-quality estimates can differ from local station observations.
- The CPCB adapter requires a valid data.gov.in resource and may need resource-specific filter changes.
- A model's accuracy is specific to its training location and test period. Rain/no-rain accuracy can be misleading when rain days are rare; inspect precision, recall, F1 and the confusion matrix too.
- Historical reanalysis is an estimate. A short trend or a single location does not establish climate change.
- Verify severe weather and air-quality advisories with IMD, CPCB and local authorities.


## One-command full download + ML training (updated)

From the project root (the folder containing `app.py`), run this single command:

```powershell
python run_all.py --years 10
```

This downloads historical data for all cities in `datasets/india_cities.csv` in sequential batches of four, waits between requests and batches, retries Open-Meteo rate limits (HTTP 429) with backoff, saves a checkpoint after every successful city, resumes completed cities on rerun, and then trains both local ML models automatically. Do not close the terminal while it is running. It can take a long time because it retrieves roughly a decade of daily data for 100+ locations. If interrupted, run the same command again; it resumes from saved data.

To use more conservative API pacing, run:

```powershell
python run_all.py --years 10 --batch-size 4 --request-delay 5 --batch-delay 45
```

Do not delete `datasets/weather_history.csv` if you want resume behavior.
