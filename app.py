import streamlit as st
import pandas as pd
from datetime import date, timedelta
from modules.weather import geocode_city, get_forecast, get_archive
from modules.air_quality import get_air_quality, get_cpcb_data
from modules.assistant import answer_weather_question
from modules.alerts import build_alerts
from modules.predictions import predict_tomorrow

st.set_page_config(page_title="ऋतुवेद AI | RituVeda", page_icon="🌙", layout="wide")
st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: radial-gradient(ellipse at 15% 0%, #172554 0%, #0b1224 42%, #050914 100%); color:#e5edf9; }
.block-container { max-width:1500px; padding-top:1.4rem; padding-bottom:3rem; }
h1,h2,h3,h4 { color:#f1f5ff !important; font-weight:760 !important; }
p,label,li,[data-testid="stMarkdownContainer"] { color:#cbd5e1; }
[data-testid="stMetric"] { background:linear-gradient(145deg,#17243b,#101a2d)!important; border:1px solid #334766; border-radius:18px; padding:17px; box-shadow:0 8px 24px rgba(0,0,0,.22); }
[data-testid="stTabs"] button { color:#cbd5e1!important; font-weight:650; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#93c5fd!important; border-bottom-color:#60a5fa!important; }
.stButton>button { background:linear-gradient(100deg,#2563eb,#0ea5e9); color:white!important; border:0; border-radius:12px; font-weight:700; padding:.55rem 1rem; }
.stTextInput input, [data-baseweb="input"] input { background:#111c30!important; color:#f8fafc!important; border-color:#3a4c68!important; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0b1426,#101c32); border-right:1px solid #263954; }
[data-testid="stChatMessage"] { background:#121f34; border:1px solid #334766; border-radius:14px; padding:10px; }
[data-testid="stDataFrame"], [data-testid="stTable"] { background:#101a2d; }
hr { border-color:#334155!important; }
.weather-scene { position:relative; overflow:hidden; min-height:190px; border:1px solid rgba(148,163,184,.25); border-radius:24px; margin:10px 0 22px; padding:24px 28px; display:flex; flex-direction:column; justify-content:center; background:linear-gradient(120deg,#142b4c,#0b172b 70%); box-shadow:0 14px 40px rgba(0,0,0,.25); }
.weather-scene .scene-title {font-size:1.75rem;font-weight:800;color:#f8fafc;position:relative;z-index:2}
.weather-scene .scene-sub {color:#dbeafe;position:relative;z-index:2}
.weather-scene .orb {position:absolute;width:100px;height:100px;border-radius:50%;right:12%;top:25px;background:radial-gradient(circle at 35% 35%,#fff7ae,#f59e0b 65%,#ea580c);box-shadow:0 0 55px #f59e0b;animation:pulse 4s ease-in-out infinite}
.weather-scene.sunny {background:linear-gradient(120deg,#164e63,#0f2744 72%)}
.weather-scene.cloudy {background:linear-gradient(120deg,#334155,#111c30 78%)}
.weather-scene.cloudy:after {content:"☁️";position:absolute;right:12%;top:34px;font-size:5rem;animation:drift 7s ease-in-out infinite}
.weather-scene.rainy {background:linear-gradient(120deg,#172b46,#080f1e)}
.weather-scene.rainy:after {content:"🌧️";position:absolute;right:12%;top:27px;font-size:5rem;animation:drift 5s ease-in-out infinite}
.weather-scene.snowy:after {content:"❄️";position:absolute;right:12%;top:27px;font-size:5rem;animation:floaty 4s ease-in-out infinite}
.weather-scene.night {background:linear-gradient(120deg,#090d27,#111b3a 75%)}
.weather-scene.night:after {content:"☾";position:absolute;right:13%;top:8px;font-size:7rem;color:#e2e8f0;text-shadow:0 0 35px #93c5fd;animation:floaty 6s ease-in-out infinite}
.weather-scene.night:before {content:"✦  ·   ✧     ·  ✦       ✧";position:absolute;right:3%;top:12px;color:#e0f2fe;font-size:1.5rem;letter-spacing:12px;animation:twinkle 3s ease-in-out infinite}
.weather-scene.rainy .rain {position:absolute;inset:0;background-image:repeating-linear-gradient(105deg,transparent 0 18px,rgba(147,197,253,.38) 19px,transparent 20px 38px);background-size:100% 100%;animation:rainfall .55s linear infinite;opacity:.65}
@keyframes rainfall {from{background-position:0 -30px}to{background-position:0 80px}}
@keyframes pulse {50%{transform:scale(1.08);box-shadow:0 0 75px #fbbf24}}
@keyframes drift {50%{transform:translateX(-16px)}}
@keyframes floaty {50%{transform:translateY(-12px)}}
@keyframes twinkle {50%{opacity:.35}}
@media (prefers-reduced-motion: reduce) { *,*::before,*::after {animation:none!important;transition:none!important} }

/* RituVeda premium visual system */
.block-container {max-width:1540px!important;padding-top:1.1rem!important;padding-left:clamp(1rem,3vw,3rem)!important;padding-right:clamp(1rem,3vw,3rem)!important}
.rv-brand {display:flex;align-items:center;gap:18px;padding:22px 26px;margin:4px 0 22px;border:1px solid rgba(125,211,252,.22);border-radius:24px;background:linear-gradient(112deg,rgba(14,116,144,.26),rgba(30,41,86,.62) 52%,rgba(88,28,135,.22));box-shadow:0 18px 48px rgba(2,8,23,.35);overflow:hidden}
.rv-mark {width:62px;height:62px;flex:0 0 62px;border-radius:19px;display:grid;place-items:center;font-size:31px;background:linear-gradient(145deg,#22d3ee,#6366f1 58%,#a78bfa);box-shadow:0 8px 28px rgba(34,211,238,.25)}
.rv-title-wrap {min-width:0;flex:1}
.rv-hindi {font-family:'Noto Sans Devanagari','Mangal',sans-serif;font-size:clamp(1.55rem,3.4vw,2.5rem);line-height:1.55;letter-spacing:.01em;font-weight:850;color:#f8fafc;white-space:normal;overflow-wrap:anywhere;margin:0;padding:0}
.rv-english {font-size:clamp(.9rem,1.7vw,1.15rem);font-weight:750;letter-spacing:.22em;text-transform:uppercase;color:#67e8f9;margin-top:3px}
.rv-tagline {font-size:.92rem;color:#cbd5e1;margin-top:6px;line-height:1.5}
.rv-pill {display:inline-block;border:1px solid rgba(103,232,249,.28);background:rgba(8,145,178,.14);color:#a5f3fc;border-radius:999px;padding:7px 12px;font-size:.78rem;font-weight:700;white-space:nowrap}
[data-testid="stMetric"] {background:linear-gradient(145deg,rgba(20,38,68,.96),rgba(12,23,43,.98))!important;border:1px solid rgba(125,170,220,.25)!important;border-radius:18px!important;padding:16px 18px!important;min-height:112px;box-shadow:0 10px 30px rgba(0,0,0,.2)}
[data-testid="stMetricLabel"] {color:#a5b4fc!important;font-weight:650}
[data-testid="stMetricValue"] {color:#f8fafc!important;font-weight:800}
[data-testid="stTabs"] {background:rgba(15,23,42,.42);padding:8px 10px;border:1px solid rgba(148,163,184,.13);border-radius:18px}
[data-testid="stTabs"] button {font-size:.9rem!important;padding:10px 8px!important}
.stButton>button {background:linear-gradient(105deg,#0891b2,#4f46e5 70%,#7c3aed)!important;border:1px solid rgba(165,243,252,.22)!important;box-shadow:0 7px 22px rgba(37,99,235,.18);transition:transform .18s ease,filter .18s ease}
.stButton>button:hover {filter:brightness(1.13);transform:translateY(-1px)}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#091426,#111c38 65%,#171334)!important}
[data-testid="stExpander"] {border:1px solid rgba(148,163,184,.2)!important;border-radius:15px!important}
div[data-testid="stDataFrame"] {border:1px solid rgba(148,163,184,.18);border-radius:14px;overflow:hidden}
@media(max-width:700px){.rv-brand{padding:16px;gap:12px}.rv-mark{width:48px;height:48px;flex-basis:48px;font-size:24px;border-radius:15px}.rv-pill{display:none}.rv-hindi{font-size:1.55rem;line-height:1.6}}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="rv-brand">
  <div class="rv-mark">🌦️</div>
  <div class="rv-title-wrap">
    <div class="rv-hindi">ऋतुवेद AI</div>
    <div class="rv-english">RITUVEDA INTELLIGENCE</div>
    <div class="rv-tagline">भारत का मौसम, वायु गुणवत्ता और जलवायु — एक intelligent dashboard में</div>
  </div>
  <div class="rv-pill">INDIA WEATHER INTELLIGENCE</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📍 Location")
    city = st.text_input("Enter city", value="Patna")
    st.caption("Live weather and forecast: Open-Meteo for the city selected above. The ML model is trained across the India-wide city dataset.")
    st.caption("ML training coverage: 107 Indian cities across all 28 States + 8 UTs.")
    st.caption("Historical training data: Open-Meteo / ERA5 reanalysis · CC BY 4.0 attribution required.")
    st.divider()
    st.markdown("**Project:** SIH26068")
    st.markdown("**Domain:** Artificial Intelligence & Machine Learning")
    st.markdown("**ML models:** Random Forest Regression + Classification")
    st.caption("CPCB station data requires a configured data.gov.in API resource.")

for key, default in [("weather_data", None), ("location_data", None),
                     ("air_data", None), ("chat_history", [])]:
    if key not in st.session_state:
        st.session_state[key] = default

if st.button("🔄 Get latest weather", type="primary"):
    st.session_state.weather_data = None
    st.session_state.location_data = None
    st.session_state.air_data = None
    st.session_state.chat_history = []

if st.session_state.get("loaded_city") != city.strip():
    st.session_state.weather_data = None
    st.session_state.location_data = None
    st.session_state.air_data = None
    st.session_state.loaded_city = city.strip()

if st.session_state.weather_data is None and city.strip():
    try:
        with st.spinner("Loading weather, forecast and air quality..."):
            loc = geocode_city(city.strip())
            if loc:
                st.session_state.location_data = loc
                st.session_state.weather_data = get_forecast(loc["latitude"], loc["longitude"])
                try:
                    st.session_state.air_data = get_air_quality(loc["latitude"], loc["longitude"])
                except Exception as air_exc:
                    st.session_state.air_data = None
                    st.warning(f"Air-quality service is temporarily unavailable: {air_exc}")
            else:
                st.error("City not found. Check the spelling.")
    except Exception as exc:
        st.error(f"Could not load data: {exc}")

loc, wx, air = (st.session_state.location_data, st.session_state.weather_data,
                st.session_state.air_data)

if loc and wx:
    current, daily = wx.get("current", {}), wx.get("daily", {})
    place = ", ".join(x for x in [loc.get("name"), loc.get("admin1"), loc.get("country")] if x)
    st.subheader(f"Weather in {place}")
    st.caption(f"Last data timestamp: {current.get('time', 'Not available')} · Time zone: {wx.get('timezone', 'local')}")
    code = current.get("weather_code")
    is_day = current.get("is_day", 1)
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = -1
    if not is_day:
        scene_class, scene_label, scene_desc = "night", "Night sky", "Night-time conditions · Live local weather"
    elif code in (0, 1):
        scene_class, scene_label, scene_desc = "sunny", "Clear and sunny", "Bright conditions · Live local weather"
    elif code in (2, 3, 45, 48):
        scene_class, scene_label, scene_desc = "cloudy", "Clouds moving overhead", "Cloudy conditions · Live local weather"
    elif code in (71, 73, 75, 77, 85, 86):
        scene_class, scene_label, scene_desc = "snowy", "Snow conditions", "Snow or snow showers · Live local weather"
    elif code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99):
        scene_class, scene_label, scene_desc = "rainy", "Rain in the area", "Rain or storm conditions · Live local weather"
    else:
        scene_class, scene_label, scene_desc = "cloudy", "Current weather", "Live local weather conditions"
    icon_html = '<div class="orb"></div>' if scene_class == "sunny" else ('<div class="rain"></div>' if scene_class == "rainy" else '')
    st.markdown(f'<div class="weather-scene {scene_class}">{icon_html}<div class="scene-title">{scene_label}</div><div class="scene-sub">{scene_desc}</div></div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🌡️ Temperature", f"{current.get('temperature_2m','—')} °C")
    c2.metric("💧 Humidity", f"{current.get('relative_humidity_2m','—')}%")
    c3.metric("🌬️ Wind speed", f"{current.get('wind_speed_10m','—')} km/h")
    c4.metric("🌧️ Precipitation", f"{current.get('precipitation','—')} mm")

    tabs = st.tabs(["📊 Forecast", "💬 AI Assistant", "🚨 Alerts", "🌫️ AQI", "🤖 My ML Models", "🌍 Climate", "🏙️ Compare Cities"])

    with tabs[0]:
        st.subheader("7-day forecast")
        if daily.get("time"):
            df = pd.DataFrame({
                "Date": daily["time"], "Maximum (°C)": daily.get("temperature_2m_max", []),
                "Minimum (°C)": daily.get("temperature_2m_min", []),
                "Rain probability (%)": daily.get("precipitation_probability_max", []),
                "Rainfall (mm)": daily.get("precipitation_sum", []),
                "UV index": daily.get("uv_index_max", [])
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.line_chart(df.set_index("Date")[["Maximum (°C)", "Minimum (°C)"]])
            st.bar_chart(df.set_index("Date")[["Rainfall (mm)"]])
            st.caption("UV index is a forecast indicator. Follow local public-health advice.")
        else:
            st.info("Daily forecast is unavailable.")

    with tabs[1]:
        st.subheader("Ask RituVeda AI")
        st.write("Ask in English, Hindi or Hinglish. Example: *Kal baarish hogi kya?*, *AQI kya hai?*, *Will it rain tomorrow?*")
        for item in st.session_state.chat_history:
            with st.chat_message(item["role"]):
                st.markdown(item["content"])
        question = st.chat_input("Ask about weather, AQI, UV or forecasts...")
        if question:
            st.session_state.chat_history.append({"role":"user","content":question})
            weather_context = dict(wx)
            weather_context["air_quality"] = air or {}
            try:
                reply = answer_weather_question(question, place, weather_context,
                                                location=loc,
                                                history=st.session_state.chat_history[:-1])
            except Exception as exc:
                reply = f"I couldn't process that question. Please try again. ({exc})"
            st.session_state.chat_history.append({"role":"assistant","content":reply})
            st.rerun()

    with tabs[2]:
        st.subheader("Weather and UV safety alerts")
        alerts = build_alerts(current, daily, air)
        if alerts:
            for alert in alerts:
                msg = f"**{alert['title']}** — {alert['message']}"
                if alert["level"] == "High": st.error("🚨 " + msg)
                elif alert["level"] == "Moderate": st.warning("⚠️ " + msg)
                else: st.info("ℹ️ " + msg)
        else:
            st.success("No application threshold alerts are triggered by available data.")
        st.caption("Illustrative thresholds only, not official IMD/CPCB warnings. Follow official advisories.")

    with tabs[3]:
        st.subheader("Air Quality Intelligence")
        if air and air.get("current"):
            aq = air["current"]
            a,b,c,d = st.columns(4)
            a.metric("US AQI (modelled)", aq.get("us_aqi", "—"))
            b.metric("European AQI", aq.get("european_aqi", "—"))
            c.metric("PM2.5", f"{aq.get('pm2_5','—')} µg/m³")
            d.metric("PM10", f"{aq.get('pm10','—')} µg/m³")
            pollutants = {k: aq.get(k) for k in ["carbon_monoxide","nitrogen_dioxide","sulphur_dioxide","ozone","uv_index"]}
            st.write("**Other indicators**")
            st.dataframe(pd.DataFrame([{"Pollutant / indicator":k.replace("_"," ").upper(),"Value":v} for k,v in pollutants.items()]), hide_index=True, use_container_width=True)
            hourly = air.get("hourly", {})
            if hourly.get("time") and hourly.get("us_aqi"):
                aqi_df = pd.DataFrame({"Time":hourly["time"],"US AQI":hourly["us_aqi"],"PM2.5":hourly.get("pm2_5",[])})
                st.line_chart(aqi_df.set_index("Time")[["US AQI","PM2.5"]])
            st.info("Open-Meteo air-quality values are modelled estimates, not direct CPCB monitoring-station measurements.")
        else:
            st.warning("Air-quality data is not available at the moment.")
        st.markdown("#### India CPCB / data.gov.in station data")
        try:
            cpcb = get_cpcb_data(loc["latitude"], loc["longitude"])
            if cpcb and cpcb.get("records"):
                st.dataframe(pd.DataFrame(cpcb["records"]), use_container_width=True, hide_index=True)
                st.caption("Records returned by your configured data.gov.in resource. Check station, timestamp and units.")
            else:
                st.caption("CPCB adapter is optional. Configure DATA_GOV_IN_API_KEY and CPCB_RESOURCE_ID (plus resource-specific filters) to query a data.gov.in resource.")
        except Exception as exc:
            st.warning(f"Configured CPCB/data.gov.in source could not be queried: {exc}")

    with tabs[4]:
        st.subheader("Your independently trained ML models")
        st.write("India-wide Random Forest models trained locally on multi-city historical weather. Their output is separate from external forecast services.")
        model_dir = st.container()
        try:
            end_day = date.today() - timedelta(days=5)
            start_day = end_day - timedelta(days=20)
            with st.spinner("Preparing recent observed weather inputs..."):
                hist = get_archive(loc["latitude"], loc["longitude"], start_day.isoformat(), end_day.isoformat())
            prediction = predict_tomorrow(hist.get("daily", {}), location=loc)
            if prediction:
                p1,p2,p3 = st.columns(3)
                p1.metric("ML predicted maximum", f"{prediction['max_temp_c']} °C")
                p2.metric("ML predicted minimum", f"{prediction['min_temp_c']} °C")
                p3.metric("ML rain probability", f"{prediction['rain_probability']}%")
                st.caption(f"Models trained through {prediction['trained_through']}. Prediction target is the day after the latest available archive observation (archive data is delayed), not necessarily tomorrow.")
            else:
                st.warning("Trained model files not found. Follow the training steps below.")
        except Exception as exc:
            st.warning(f"Could not create an ML prediction: {exc}")
        st.markdown("**Train the India-wide models (run both commands in VS Code terminal from the project folder):**")
        st.code("python -m ml.data_pipeline --years 10\npython -m ml.train_models --data datasets/weather_history.csv", language="powershell")
        st.markdown("The collector downloads historical data for 100+ Indian locations and saves after every city. If interrupted, run the same command again; completed cities are skipped. The full 10-year download can take time depending on internet/API response. Training is RAM-bounded for a normal laptop. Model files and `models/evaluation.json` are created after successful training.")
        st.caption("One shared India-wide model is trained across all locations in datasets/india_cities.csv. The model uses recent local weather history plus latitude/longitude to make a location-aware prediction.")
        st.caption("Coverage depends on the cities listed in datasets/india_cities.csv. ERA5 is reanalysis (model-based reconstruction), not direct station observations.")
        report_path = "models/evaluation.json"
        try:
            import json, os
            if os.path.exists(report_path):
                report = json.load(open(report_path, encoding="utf-8"))
                st.markdown("**Saved evaluation report**")
                st.json(report)
        except Exception as exc:
            st.caption(f"Evaluation report unavailable: {exc}")

    with tabs[5]:
        st.subheader("Climate trends and historical analysis")
        st.write("Use multi-year observations for trend context. Weather variation over a short window is not proof of climate change.")
        years = st.selectbox("Historical period", [1, 3, 5, 10], index=1)
        if st.button("Load climate history"):
            try:
                end_day = date.today() - timedelta(days=5)
                start_day = end_day - timedelta(days=365*years)
                with st.spinner(f"Loading {years} years of historical observations..."):
                    hist = get_archive(loc["latitude"], loc["longitude"], start_day.isoformat(), end_day.isoformat())
                hd = hist.get("daily", {})
                if hd.get("time"):
                    climate_df = pd.DataFrame({
                        "Date": pd.to_datetime(hd["time"]),
                        "Maximum temperature (°C)": hd.get("temperature_2m_max", []),
                        "Minimum temperature (°C)": hd.get("temperature_2m_min", []),
                        "Rainfall (mm)": hd.get("precipitation_sum", [])
                    }).dropna(subset=["Date"])
                    climate_df["Year"] = climate_df["Date"].dt.year
                    yearly = climate_df.groupby("Year").agg(
                        Mean_max_temp=("Maximum temperature (°C)","mean"),
                        Mean_min_temp=("Minimum temperature (°C)","mean"),
                        Total_rainfall=("Rainfall (mm)","sum")
                    ).reset_index()
                    st.dataframe(yearly.round(2), use_container_width=True, hide_index=True)
                    st.line_chart(yearly.set_index("Year")[["Mean_max_temp","Mean_min_temp"]])
                    st.bar_chart(yearly.set_index("Year")[["Total_rainfall"]])
                    st.caption("Reanalysis-based historical estimates; trends depend on location, period and dataset.")
                else:
                    st.info("No historical records returned.")
            except Exception as exc:
                st.error(f"Climate history could not be loaded: {exc}")

    with tabs[6]:
        st.subheader("Compare weather between cities")
        compare_city = st.text_input("Second city", value="Delhi", key="compare_city")
        if st.button("Compare cities"):
            try:
                other = geocode_city(compare_city.strip())
                if not other:
                    st.error("Second city not found.")
                else:
                    other_wx = get_forecast(other["latitude"], other["longitude"])
                    oc = other_wx.get("current", {})
                    comparison = pd.DataFrame([
                        {"Metric":"Temperature (°C)","Selected city":current.get("temperature_2m"),"Comparison city":oc.get("temperature_2m")},
                        {"Metric":"Humidity (%)","Selected city":current.get("relative_humidity_2m"),"Comparison city":oc.get("relative_humidity_2m")},
                        {"Metric":"Wind speed (km/h)","Selected city":current.get("wind_speed_10m"),"Comparison city":oc.get("wind_speed_10m")},
                        {"Metric":"Precipitation (mm)","Selected city":current.get("precipitation"),"Comparison city":oc.get("precipitation")}
                    ])
                    st.write(f"**{place} vs {other.get('name')}, {other.get('country','')}**")
                    st.dataframe(comparison, use_container_width=True, hide_index=True)
                    st.bar_chart(comparison.set_index("Metric")[["Selected city","Comparison city"]])
            except Exception as exc:
                st.error(f"City comparison failed: {exc}")

    st.divider()
    st.caption("RituVeda AI is an educational prototype. Forecasts and model estimates are not guarantees. Verify severe-weather and air-quality advisories with official authorities.")
else:
    st.info("Enter a city in the sidebar and load weather data to begin.")
