"""Load India-wide trained models and predict from recent city weather history."""
from pathlib import Path
import math
import joblib
import pandas as pd

BASE=["tmax","tmin","rain_mm","wind_max","humidity_mean","pressure_mean"]
MAP={"temperature_2m_max":"tmax","temperature_2m_min":"tmin","precipitation_sum":"rain_mm",
     "wind_speed_10m_max":"wind_max","relative_humidity_2m_mean":"humidity_mean",
     "pressure_msl_mean":"pressure_mean","surface_pressure_mean":"pressure_mean"}

def _feature_frame(history_daily, location=None):
    raw=pd.DataFrame({"date":history_daily.get("time",[])})
    for source,target in MAP.items():
        if target not in raw:
            vals=history_daily.get(source)
            if vals is not None: raw[target]=vals
    for col in BASE:
        if col not in raw: raw[col]=None
        raw[col]=pd.to_numeric(raw[col],errors="coerce")
    raw=raw.sort_values("date")
    row={}
    for col in BASE:
        vals=raw[col]
        for lag in (1,2,3): row[f"{col}_lag{lag}"]=vals.iloc[-lag] if len(vals)>=lag else None
        row[f"{col}_mean7"]=vals.tail(7).mean()
    last=pd.to_datetime(raw.date.iloc[-1])
    row["day_sin"]=math.sin(2*math.pi*last.dayofyear/365.25)
    row["day_cos"]=math.cos(2*math.pi*last.dayofyear/365.25)
    row["month_sin"]=math.sin(2*math.pi*last.month/12)
    row["month_cos"]=math.cos(2*math.pi*last.month/12)
    row["latitude"]=float((location or {}).get("latitude",25.0))
    row["longitude"]=float((location or {}).get("longitude",85.0))
    return pd.DataFrame([row])

def predict_tomorrow(history_daily,model_dir="models",location=None):
    directory=Path(model_dir)
    tf,rf=directory/"temperature_model.joblib",directory/"rainfall_model.joblib"
    if not tf.exists() or not rf.exists(): return None
    tb,rb=joblib.load(tf),joblib.load(rf)
    meta=tb.get("metadata",{})
    features=_feature_frame(history_daily,location)
    tx=features[tb["features"]]
    temp=tb["pipeline"].predict(tx)[0]
    rx=features[rb["features"]]
    model=rb["pipeline"]; rain_class=int(model.predict(rx)[0])
    classes=list(model.classes_)
    prob=float(model.predict_proba(rx)[0][classes.index(1)]) if 1 in classes else 0.0
    return {"max_temp_c":round(float(temp[0]),1),"min_temp_c":round(float(temp[1]),1),
            "rain_class":rain_class,"rain_probability":round(prob*100,1),
            "trained_through":tb.get("trained_through","unknown"),
            "trained_city":"India-wide model","city_count":meta.get("city_count",0),
            "historical_model":meta.get("historical_model","ERA5")}
