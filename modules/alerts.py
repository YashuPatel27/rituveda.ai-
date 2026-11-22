"""Illustrative application weather and air-quality alerts."""
def build_alerts(current, daily, air_quality=None):
    alerts = []
    temp = current.get("temperature_2m")
    max_wind = daily.get("wind_speed_10m_max", [])
    rain_prob = daily.get("precipitation_probability_max", [])
    max_temp = daily.get("temperature_2m_max", [])
    uv = daily.get("uv_index_max", [])

    if isinstance(temp, (int, float)) and temp >= 40:
        alerts.append({"level": "High", "title": "Very high temperature",
                       "message": f"Current temperature is {temp}°C. Avoid prolonged outdoor activity and stay hydrated."})
    elif isinstance(temp, (int, float)) and temp >= 35:
        alerts.append({"level": "Moderate", "title": "High temperature",
                       "message": f"Current temperature is {temp}°C. Limit strenuous outdoor activity during the hottest hours."})
    if rain_prob and isinstance(rain_prob[0], (int, float)) and rain_prob[0] >= 70:
        alerts.append({"level": "Moderate", "title": "Rain likely",
                       "message": f"Maximum forecast rain probability today is {rain_prob[0]}%. Consider carrying an umbrella."})
    if max_wind and isinstance(max_wind[0], (int, float)) and max_wind[0] >= 50:
        alerts.append({"level": "High", "title": "Strong winds possible",
                       "message": f"Forecast maximum wind speed is {max_wind[0]} km/h. Secure loose outdoor objects."})
    if max_temp and isinstance(max_temp[0], (int, float)) and max_temp[0] >= 40:
        alerts.append({"level": "High", "title": "Heat risk forecast",
                       "message": f"Today's forecast maximum is {max_temp[0]}°C. Follow local heat-safety advice."})
    if uv and isinstance(uv[0], (int, float)):
        if uv[0] >= 8:
            alerts.append({"level": "High", "title": "Very high UV index",
                           "message": f"Forecast UV index is {uv[0]}. Seek shade, wear protective clothing and use broad-spectrum sunscreen."})
        elif uv[0] >= 6:
            alerts.append({"level": "Moderate", "title": "High UV index",
                           "message": f"Forecast UV index is {uv[0]}. Reduce prolonged midday sun exposure."})

    if air_quality:
        aqi = (air_quality.get("current") or {}).get("us_aqi")
        if isinstance(aqi, (int, float)):
            if aqi > 150:
                level = "High"
                advice = "Limit prolonged outdoor exertion; sensitive groups should avoid strenuous outdoor activity."
            elif aqi > 100:
                level = "Moderate"
                advice = "Sensitive groups should consider reducing prolonged outdoor exertion."
            else:
                level = "Info"
                advice = "Air quality is currently in the lower US-AQI bands."
            if aqi > 50:
                alerts.append({"level": level, "title": "Air quality advisory",
                               "message": f"Modelled US AQI is {aqi}. {advice}"})
    return alerts
