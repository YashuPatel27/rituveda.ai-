"""
RituVeda AI conversational engine.

Includes a rule-based NLP fallback (no API key required) and optional Gemini
response generation. Weather facts are always taken from the supplied
Open-Meteo response; the assistant must not invent measurements.
"""
import os
import re
import json
from datetime import datetime, date, timedelta

import requests


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]


def _clean(text):
    """Normalize common punctuation and Hinglish weather phrases."""
    q = (text or "").lower().strip()
    # Normalize Devanagari before regex cleanup: vowel marks are combining characters.
    devanagari_map = {
        "बारिश": "rain", "मौसम": "weather", "तापमान": "temperature",
        "गर्मी": "hot", "ठंड": "cold", "हवा": "wind", "नमी": "humidity",
        "आज": "today", "अभी": "current", "कल": "tomorrow", "परसों": "day after tomorrow",
        "क्या": "what", "होगी": "will be", "होगा": "will be", "है": "is",
        "बताओ": "tell me", "कितना": "how much", "कितनी": "how much"
    }
    for hindi_word, english_word in devanagari_map.items():
        q = q.replace(hindi_word, english_word)
    q = q.replace("°", " degree ")
    q = re.sub(r"[^\w\s'-]", " ", q)
    q = re.sub(r"\s+", " ", q)
    replacements = {
         "मौसम": "weather", "बारिश": "rain", "तापमान": "temperature",
        "गर्मी": "hot", "ठंड": "cold", "हवा": "wind", "नमी": "humidity",
        "आज": "today", "अभी": "current", "कल": "tomorrow", "क्या": "what",
        "बताओ": "tell me", "कितना": "how much", "मौसम": "weather",
        "mausam": "weather", "mosam": "weather", "baarish": "rain",
        "barish": "rain", "barishh": "rain", "pani": "rain",
        "garmi": "hot", "thand": "cold", "sardi": "cold",
        "hawa": "wind", "tez hawa": "strong wind", "nami": "humidity",
        "aaj": "today", "abhi": "current", "filhal": "current",
        "kal": "tomorrow", "parso": "day after tomorrow",
        "agle hafte": "next week", "is hafte": "this week",
        "kitna": "how much", "kitni": "how much", "kya": "what",
        "rahega": "will be", "rahegi": "will be", "hoga": "will be",
        "hogi": "will be", "batao": "tell me", "btao": "tell me",
        "chahiye": "should i", "le jana": "carry",
    }
    # Replace longer phrases first.
    for old in sorted(replacements, key=len, reverse=True):
        q = re.sub(r"\b" + re.escape(old) + r"\b", replacements[old], q)
    return q


def _safe(values, index, default=None):
    if not isinstance(values, list) or index is None or index < 0 or index >= len(values):
        return default
    value = values[index]
    return default if value is None else value


def _forecast_dates(daily):
    return daily.get("time", []) if isinstance(daily, dict) else []


def _resolve_day(question, daily, history=None):
    """Return forecast index for today/tomorrow/weekdays/weekend."""
    dates = _forecast_dates(daily)
    if not dates:
        return None
    q = _clean(question)
    if "day after tomorrow" in q or "parso" in q:
        return 2 if len(dates) > 2 else None
    if "tomorrow" in q or "next day" in q:
        return 1 if len(dates) > 1 else None
    # Follow-up date: "what about tomorrow?" inherits the previous topic,
    # but date selection is still based on the new question.
    for i, day_string in enumerate(dates):
        try:
            weekday = datetime.strptime(day_string, "%Y-%m-%d").strftime("%A").lower()
        except ValueError:
            continue
        if re.search(r"\b" + weekday + r"\b", q):
            return i

    if "weekend" in q:
        for i, day_string in enumerate(dates):
            try:
                if datetime.strptime(day_string, "%Y-%m-%d").weekday() in (5, 6):
                    return i
            except ValueError:
                pass
    if "today" in q or "current" in q or "now" in q or "aaj" in q:
        return 0
    if "next week" in q:
        return min(7, len(dates) - 1)
    if "forecast" in q or "next few days" in q or "coming days" in q:
        return 0
    return None


def _intent(q):
    """Recognize everyday weather questions without requiring model training."""
    q = re.sub(r"\s+", " ", (q or "").lower()).strip()
    # Natural, short questions people commonly type in a chat assistant.
    if any(x in q for x in ["compare", "compared", "difference", "colder than",
                             "hotter than", "warmer than", "cooler than"]):
        return "compare"
    if any(x in q for x in ["umbrella", "carry", "picnic", "outdoor", "travel",
                             "safe to go", "should i go", "what should i wear",
                             "wear", "plan my day"]):
        return "advice"
    if any(x in q for x in ["rain", "raining", "rainfall", "precipitation", "shower",
                             "storm", "baarish", "barish", "will it pour", "wet today"]):
        return "rain"
    if any(x in q for x in ["humidity", "humid", "moisture"]):
        return "humidity"
    if any(x in q for x in ["wind", "breeze", "gust"]):
        return "wind"
    if any(x in q for x in ["aqi", "air quality", "pollution", "pm2", "pm10"]):
        return "aqi"
    if any(x in q for x in ["uv", "sunburn", "sun index", "sunlight"]):
        return "uv"
    if any(x in q for x in ["sunrise", "sunset"]):
        return "sun"
    if any(x in q for x in ["temperature", "temp", "hot", "cold", "warm",
                             "cool", "degree", "feels like", "how many degrees",
                             "is it chilly", "is it hot", "is it cold"]):
        return "temperature"
    if any(x in q for x in ["forecast", "next 7", "next seven", "next week",
                             "coming days", "weekend"]):
        return "forecast"
    if any(x in q for x in ["weather", "condition", "mausam", "mosam",
                             "how is it outside", "what is it like outside",
                             "how is the day", "weather like"]):
        return "weather"
    if any(x in q for x in ["explain", "why", "what causes", "meaning of"]):
        return "explanation"
    return "unknown"


def _fmt(value, unit="", digits=1):
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}{unit}"
    return "not available"


def _day_label(daily, index):
    return _safe(_forecast_dates(daily), index, "the selected day")


def _current_summary(city, current):
    return (
        f"Current conditions in **{city}**:\n\n"
        f"- Temperature: **{_fmt(current.get('temperature_2m'), ' °C')}**\n"
        f"- Feels like: **{_fmt(current.get('apparent_temperature'), ' °C')}**\n"
        f"- Relative humidity: **{_fmt(current.get('relative_humidity_2m'), '%', 0)}**\n"
        f"- Wind speed: **{_fmt(current.get('wind_speed_10m'), ' km/h')}**\n"
        f"- Precipitation now: **{_fmt(current.get('precipitation'), ' mm')}**"
    )


def _day_values(daily, idx):
    return {
        "date": _day_label(daily, idx),
        "high": _safe(daily.get("temperature_2m_max", []), idx),
        "low": _safe(daily.get("temperature_2m_min", []), idx),
        "rain_probability": _safe(daily.get("precipitation_probability_max", []), idx),
        "rainfall": _safe(daily.get("precipitation_sum", []), idx),
        "wind": _safe(daily.get("wind_speed_10m_max", []), idx),
        "uv": _safe(daily.get("uv_index_max", []), idx),
        "sunrise": _safe(daily.get("sunrise", []), idx),
        "sunset": _safe(daily.get("sunset", []), idx),
    }


def _hourly_average_for_date(weather, field, day_string):
    hourly = weather.get("hourly", {}) or {}
    times = hourly.get("time", [])
    values = hourly.get(field, [])
    selected = [v for t, v in zip(times, values)
                if isinstance(t, str) and t.startswith(day_string)
                and isinstance(v, (int, float))]
    return round(sum(selected) / len(selected), 1) if selected else None


def _local_answer(question, city, weather, history=None):
    current = weather.get("current", {}) or {}
    daily = weather.get("daily", {}) or {}
    q = _clean(question)
    intent = _intent(q)
    idx = _resolve_day(question, daily, history)

    if intent == "aqi":
        air = weather.get("air_quality", {}) or {}
        aq = air.get("current", {}) or {}
        if aq.get("us_aqi") is None and aq.get("european_aqi") is None:
            return "Live air-quality values are not available right now. Please try again later."
        return ("### Air quality information\\n\\n"
                f"- Modelled US AQI: **{aq.get('us_aqi', 'not available')}**\\n"
                f"- European AQI: **{aq.get('european_aqi', 'not available')}**\\n"
                f"- PM2.5: **{aq.get('pm2_5', 'not available')} µg/m³**\\n"
                f"- PM10: **{aq.get('pm10', 'not available')} µg/m³**\\n\\n"
                "These are Open-Meteo model estimates, not official CPCB station readings.")

    if intent == "unknown":
        # Use previous user intent for short follow-up messages.
        if history:
            previous = next((x.get("content", "") for x in reversed(history)
                             if x.get("role") == "user"), "")
            if len(q.split()) <= 5 and previous:
                inherited = _intent(_clean(previous))
                if inherited != "unknown":
                    intent = inherited
        if intent == "unknown":
            return (
                f"I’m your weather assistant for **{city}**. I can answer questions "
                "about current conditions, temperature, rain, humidity, wind, UV, "
                "sunrise/sunset, forecasts and weather-based plans.\n\n"
                "Try: *Will it rain tomorrow?*, *Compare today and Friday*, "
                "*Should I carry an umbrella?* or *How windy will it be this weekend?*"
            )

    if intent == "compare":
        if idx is None:
            idx = 1 if len(_forecast_dates(daily)) > 1 else 0
        today = _day_values(daily, 0)
        target = _day_values(daily, idx)
        if idx == 0:
            idx = 1 if len(_forecast_dates(daily)) > 1 else 0
            target = _day_values(daily, idx)
        if today["high"] is None or target["high"] is None:
            return "I don't have enough temperature data to make that comparison."
        difference = target["high"] - today["high"]
        comparison = "about the same" if abs(difference) < 1 else (
            f"{abs(difference):.1f}°C warmer" if difference > 0 else
            f"{abs(difference):.1f}°C cooler")
        return (f"**Temperature comparison for {city}**\n\n"
                f"- Today ({today['date']}): **{today['high']}°C** maximum\n"
                f"- {target['date']}: **{target['high']}°C** maximum\n\n"
                f"The selected day's forecast high is **{comparison}** compared with today.")

    if intent == "forecast" and ("next 7" in q or "next seven" in q or
                                 "next week" in q or "coming days" in q or
                                 "weekend" in q):
        dates = _forecast_dates(daily)
        if not dates:
            return "The daily forecast is not available right now."
        lines = []
        for i, day in enumerate(dates):
            vals = _day_values(daily, i)
            lines.append(
                f"- **{day}**: high {_fmt(vals['high'], '°C')}, "
                f"low {_fmt(vals['low'], '°C')}, rain chance "
                f"{_fmt(vals['rain_probability'], '%', 0)}, "
                f"rainfall {_fmt(vals['rainfall'], ' mm')}"
            )
        return f"### 7-day forecast for {city}\n\n" + "\n".join(lines)

    if intent == "weather":
        if idx is not None and idx > 0:
            vals = _day_values(daily, idx)
            return (f"### Weather outlook for {city} — {vals['date']}\n\n"
                    f"- Maximum: **{_fmt(vals['high'], '°C')}**\n"
                    f"- Minimum: **{_fmt(vals['low'], '°C')}**\n"
                    f"- Rain chance: **{_fmt(vals['rain_probability'], '%', 0)}**\n"
                    f"- Expected rainfall: **{_fmt(vals['rainfall'], ' mm')}**")
        return _current_summary(city, current)

    if intent in ("rain", "advice"):
        if intent == "rain" and any(token in q for token in ["next 7", "next seven", "next week", "coming days", "when"]):
            rainy_days = []
            for i, day_string in enumerate(_forecast_dates(daily)):
                vals = _day_values(daily, i)
                if isinstance(vals["rain_probability"], (int, float)) and vals["rain_probability"] >= 20:
                    rainy_days.append(f"- **{day_string}**: {vals['rain_probability']}% chance, {_fmt(vals['rainfall'], ' mm')} expected")
            if rainy_days:
                return f"### Upcoming rain outlook for {city}\\n\\n" + "\\n".join(rainy_days)
            return f"The available 7-day forecast for **{city}** does not show a day with a rain probability of 20% or higher. Small amounts of rain can still occur."
        target_idx = idx if idx is not None else 0
        vals = _day_values(daily, target_idx)
        probability = vals["rain_probability"]
        rainfall = vals["rainfall"]
        if probability is None:
            return "Rain-probability data is not available for that date."
        if intent == "advice":
            if probability >= 60:
                advice = "Rain is reasonably likely, so carrying an umbrella or raincoat is a sensible choice."
            elif probability >= 30:
                advice = "There is some chance of rain. Check again before leaving; carrying a compact umbrella may be useful."
            else:
                advice = "The forecast indicates a low chance of rain. An umbrella may not be necessary based on this forecast."
            return (f"For **{city}** on **{vals['date']}**, the maximum forecast rain "
                    f"probability is **{probability}%** and expected rainfall is "
                    f"**{_fmt(rainfall, ' mm')}**.\n\n{advice}\n\n"
                    "This is a forecast, not a guarantee.")
        return (f"### Rain forecast for {city} — {vals['date']}\n\n"
                f"- Maximum rain probability: **{probability}%**\n"
                f"- Expected rainfall: **{_fmt(rainfall, ' mm')}**\n\n"
                + ("Rain is more likely; plan accordingly." if probability >= 60 else
                   "The forecast currently indicates a lower chance of rain."))

    if intent == "temperature":
        if any(token in q for token in ["next 7", "next seven", "next week", "coming days"]):
            lines = []
            for i, day_string in enumerate(_forecast_dates(daily)):
                vals = _day_values(daily, i)
                lines.append(f"- **{day_string}**: high {_fmt(vals['high'], '°C')}, low {_fmt(vals['low'], '°C')}")
            if lines:
                return f"### 7-day temperature outlook for {city}\\n\\n" + "\\n".join(lines)
        if idx is not None and idx > 0:
            vals = _day_values(daily, idx)
            return (f"### Temperature forecast for {city} — {vals['date']}\n\n"
                    f"- Maximum: **{_fmt(vals['high'], '°C')}**\n"
                    f"- Minimum: **{_fmt(vals['low'], '°C')}**")
        return _current_summary(city, current)

    if intent == "humidity":
        if idx is not None and idx > 0:
            day_string = _day_label(daily, idx)
            humidity = _hourly_average_for_date(weather, "relative_humidity_2m", day_string)
            if humidity is not None:
                return f"Forecast average relative humidity in **{city}** on **{day_string}** is approximately **{humidity}%**."
            return f"Hourly humidity data for **{city}** on **{day_string}** is not available in the current response."
        humidity = current.get("relative_humidity_2m")
        if humidity is None:
            return "Humidity data is not available right now."
        explanation = ("High humidity can make warm weather feel more uncomfortable because sweat evaporates more slowly."
                       if humidity >= 65 else
                       "Humidity is not especially high at the moment.")
        return f"Current relative humidity in **{city}** is **{humidity}%**. {explanation}"

    if intent == "wind":
        if idx is not None and idx > 0:
            vals = _day_values(daily, idx)
            return f"Maximum forecast wind speed in **{city}** on **{vals['date']}** is **{_fmt(vals['wind'], ' km/h')}**."
        return f"Current wind speed in **{city}** is **{_fmt(current.get('wind_speed_10m'), ' km/h')}**."

    if intent == "uv":
        target_idx = idx if idx is not None else 0
        vals = _day_values(daily, target_idx)
        if vals["uv"] is None:
            return "UV-index data is not available in the current forecast."
        level = ("low" if vals["uv"] < 3 else "moderate" if vals["uv"] < 6
                 else "high" if vals["uv"] < 8 else "very high" if vals["uv"] < 11
                 else "extreme")
        return f"The maximum UV index forecast for **{city}** on **{vals['date']}** is **{vals['uv']}** ({level}). Consider sun protection when outdoors, especially at higher levels."

    if intent == "sun":
        target_idx = idx if idx is not None else 0
        vals = _day_values(daily, target_idx)
        field = "sunrise" if "sunrise" in q else "sunset"
        value = vals[field]
        if value:
            return f"Forecast {field} in **{city}** on **{vals['date']}** is **{value}** (local time)."
        return f"{field.title()} data is not available for that date."

    if intent == "explanation":
        return ("I can explain weather concepts such as humidity, wind chill, rain probability "
                "and UV index. Ask me which term you want explained, and I’ll relate it to "
                "the latest available weather observations for your selected city.")

    return _current_summary(city, current)




def _is_hindi_or_hinglish(question):
    q = (question or "").lower()
    devanagari = any("\u0900" <= ch <= "\u097f" for ch in q)
    hinglish = any(word in q.split() for word in
                   ["kal", "aaj", "kya", "mausam", "baarish", "barish", "kitna",
                    "kitni", "batao", "hogi", "hoga", "hai", "kaisa", "kaisi"])
    return devanagari or hinglish


def _hindi_local_answer(question, city, weather, history=None):
    current = weather.get("current", {}) or {}
    daily = weather.get("daily", {}) or {}
    q = _clean(question)
    intent = _intent(q)
    idx = _resolve_day(question, daily, history)
    if intent == "aqi":
        aq = (weather.get("air_quality") or {}).get("current", {}) or {}
        if aq.get("us_aqi") is None and aq.get("european_aqi") is None:
            return "अभी वायु गुणवत्ता (AQI) का डेटा उपलब्ध नहीं है। कृपया थोड़ी देर बाद फिर कोशिश करें।"
        return (f"### {city} की वायु गुणवत्ता\n\n"
                f"- अनुमानित US AQI: **{aq.get('us_aqi', 'उपलब्ध नहीं')}**\n"
                f"- European AQI: **{aq.get('european_aqi', 'उपलब्ध नहीं')}**\n"
                f"- PM2.5: **{aq.get('pm2_5', 'उपलब्ध नहीं')} µg/m³**\n"
                f"- PM10: **{aq.get('pm10', 'उपलब्ध नहीं')} µg/m³**\n\n"
                "ये Open-Meteo के मॉडल-आधारित अनुमान हैं, आधिकारिक CPCB स्टेशन रीडिंग नहीं।")
    if intent == "rain":
        i = idx if idx is not None else 0
        vals = _day_values(daily, i)
        if vals["rain_probability"] is None:
            return "इस तारीख के लिए बारिश की संभावना का डेटा उपलब्ध नहीं है।"
        advice = "छाता साथ रखना अच्छा रहेगा।" if vals["rain_probability"] >= 40 else "फिलहाल बारिश की संभावना कम दिख रही है।"
        return (f"**{city} — {vals['date']}**\n\n"
                f"बारिश की संभावना: **{vals['rain_probability']}%**\n\n"
                f"अनुमानित बारिश: **{_fmt(vals['rainfall'], ' mm')}**। {advice} यह केवल पूर्वानुमान है, गारंटी नहीं।")
    if intent in ("temperature", "weather"):
        if idx is not None and idx > 0:
            vals = _day_values(daily, idx)
            return (f"**{city} — {vals['date']}**\n\n"
                    f"अधिकतम तापमान: **{_fmt(vals['high'], '°C')}**\n"
                    f"न्यूनतम तापमान: **{_fmt(vals['low'], '°C')}**")
        return (f"**{city} का वर्तमान मौसम**\n\n"
                f"- तापमान: **{_fmt(current.get('temperature_2m'), ' °C')}**\n"
                f"- महसूस होने वाला तापमान: **{_fmt(current.get('apparent_temperature'), ' °C')}**\n"
                f"- नमी: **{_fmt(current.get('relative_humidity_2m'), '%', 0)}**\n"
                f"- हवा की गति: **{_fmt(current.get('wind_speed_10m'), ' km/h')}**")
    if intent == "humidity":
        return f"अभी {city} में नमी **{_fmt(current.get('relative_humidity_2m'), '%', 0)}** है।"
    if intent == "wind":
        return f"अभी {city} में हवा की गति **{_fmt(current.get('wind_speed_10m'), ' km/h')}** है।"
    if intent == "uv":
        vals = _day_values(daily, idx if idx is not None else 0)
        return f"{city} में {vals['date']} का अधिकतम UV index **{_fmt(vals['uv'])}** है। तेज UV में छाया में रहें और त्वचा की सुरक्षा करें।"
    return (f"मैं {city} के मौसम, तापमान, बारिश, हवा, UV और AQI के बारे में मदद कर सकता हूँ। "
            "उदाहरण: 'कल बारिश होगी क्या?' या 'AQI कितना है?'")


def _gemini_answer(question, city, weather, history=None):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    try:
        import streamlit as st
        api_key = api_key or str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        pass
    if not api_key:
        return None

    context = {
        "city": city,
        "timezone": weather.get("timezone"),
        "current": weather.get("current", {}),
        "daily_forecast": weather.get("daily", {}),
        "air_quality": weather.get("air_quality", {}),
        "hourly_forecast_sample": {
            key: values[:24] for key, values in weather.get("hourly", {}).items()
            if isinstance(values, list)
        }
    }
    recent_history = [
        {"role": x.get("role"), "content": x.get("content")}
        for x in (history or [])[-8:]
        if x.get("role") in ("user", "assistant")
    ]
    prompt = f"""
You are RituVeda AI, a bilingual conversational weather and environmental assistant. Use reliable live data and clearly distinguish measured values, forecasts, and ML estimates.
Understand natural language, paraphrases, misspellings, follow-up questions and Hindi/Hinglish.
Answer in the language used by the user when practical.
Use the supplied weather data as the only source for live weather facts.
Never invent temperature, rainfall, forecast, location, or official warnings.
If a requested date or measurement is not in the data, clearly say it is unavailable.
For recommendations, explain uncertainty and do not present forecasts as guarantees.
For general science questions, you may explain established weather science, but separate
general explanation from current measured facts. If the question is unrelated to weather,
politely explain the assistant's weather-focused scope.
Keep the answer clear, specific and helpful. Use a short table or bullets when useful.

WEATHER DATA:
{json.dumps(context, ensure_ascii=False)}

RECENT CONVERSATION:
{json.dumps(recent_history, ensure_ascii=False)}

USER QUESTION:
{question}
"""
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    response = requests.post(
        endpoint,
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.25, "maxOutputTokens": 700}
        },
        timeout=25
    )
    response.raise_for_status()
    body = response.json()
    return body["candidates"][0]["content"]["parts"][0]["text"].strip()


def answer_weather_question(question, city, weather, location=None, history=None):
    """Public entry point retained for compatibility with the original app."""
    if not question or not question.strip():
        return "Please enter a weather question."
    # Use Gemini when configured for broad language understanding. The local
    # engine remains available as a reliable fallback if the API is unavailable.
    try:
        generated = _gemini_answer(question, city, weather, history)
        if generated:
            return generated
    except Exception:
        pass
    local = _local_answer(question, city, weather, history)
    if _is_hindi_or_hinglish(question):
        return _hindi_local_answer(question, city, weather, history)
    return local
