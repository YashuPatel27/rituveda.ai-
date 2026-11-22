"""Open-Meteo weather data access helpers."""
import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def geocode_city(city):
    params = {"name": city, "count": 5, "language": "en", "format": "json"}
    response = requests.get(GEOCODING_URL, params=params, timeout=15)
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return None
    exact = next((x for x in results if x.get("name", "").lower() == city.lower()), None)
    return exact or results[0]


def get_forecast(latitude, longitude):
    params = {
        "latitude": latitude, "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature",
                    "precipitation", "wind_speed_10m", "wind_direction_10m",
                    "weather_code", "cloud_cover", "surface_pressure", "is_day"],
        "hourly": ["temperature_2m", "precipitation_probability", "precipitation",
                   "relative_humidity_2m", "wind_speed_10m", "uv_index", "visibility"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                  "precipitation_probability_max", "wind_speed_10m_max", "uv_index_max",
                  "sunrise", "sunset", "weather_code"],
        "forecast_days": 7, "timezone": "auto"
    }
    response = requests.get(FORECAST_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def get_archive(latitude, longitude, start_date, end_date, model="era5_land"):
    params = {
        "latitude": latitude, "longitude": longitude, "start_date": start_date,
        "end_date": end_date,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                  "wind_speed_10m_max", "relative_humidity_2m_mean", "surface_pressure_mean"],
        "timezone": "auto", "models": model
    }
    response = requests.get(ARCHIVE_URL, params=params, timeout=40)
    response.raise_for_status()
    return response.json()
