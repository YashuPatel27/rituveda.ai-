"""Air-quality integrations.

Open-Meteo values are modelled estimates. The optional data.gov.in/CPCB
adapter is configured by environment variables and is not presented as
official CPCB data unless a valid CPCB-linked resource is configured.
"""
import os
import requests

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def get_air_quality(latitude, longitude):
    params = {
        "latitude": latitude, "longitude": longitude,
        "current": ["us_aqi", "european_aqi", "pm10", "pm2_5",
                    "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide",
                    "ozone", "uv_index"],
        "hourly": ["us_aqi", "european_aqi", "pm10", "pm2_5",
                   "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide",
                   "ozone", "uv_index"],
        "forecast_days": 2, "timezone": "auto"
    }
    response = requests.get(AIR_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def get_cpcb_data(latitude=None, longitude=None):
    """Optional data.gov.in adapter. Supply resource ID and API key in env.

    data.gov.in resources have resource-specific query schemas. This adapter
    supports the common filters; configure CPCB_RESOURCE_ID for a resource
    that accepts state/city filters. If no resource is configured, returns
    None rather than fabricating official station data.
    """
    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    resource_id = os.getenv("CPCB_RESOURCE_ID")
    if not api_key or not resource_id:
        return None
    url = f"https://api.data.gov.in/resource/{resource_id}"
    params = {"api-key": api_key, "format": "json", "limit": 100}
    if os.getenv("CPCB_STATE"):
        params["filters[state]"] = os.getenv("CPCB_STATE")
    if os.getenv("CPCB_CITY"):
        params["filters[city]"] = os.getenv("CPCB_CITY")
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()
