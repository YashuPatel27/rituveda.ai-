"""Train and evaluate one nationwide model using all city histories."""
import argparse, json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix,
    roc_auc_score)

BASE = ["tmax", "tmin", "rain_mm", "wind_max", "humidity_mean", "pressure_mean"]
def make_supervised(raw):
    df = raw.copy()
    required = {"date", "city", "latitude", "longitude"}
    missing = required - set(df.columns)
    # Keep the feature-builder usable for unit tests / legacy single-city CSVs;
    # the actual training function still rejects single-city datasets.
    if "city" not in df: df["city"] = "Legacy single location"
    if "latitude" not in df: df["latitude"] = np.nan
    if "longitude" not in df: df["longitude"] = np.nan
    if "date" not in df:
        raise ValueError("Dataset must contain a date column.")
    df["date"] = pd.to_datetime(df.date, errors="coerce")
    for col in BASE:
        if col not in df: df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "city"]).sort_values(["city", "date"]).drop_duplicates(["city","date"])
    grouped = df.groupby("city", sort=False)
    feature_cols = []
    for col in BASE:
        for lag in (1,2,3):
            name=f"{col}_lag{lag}"
            df[name]=grouped[col].shift(lag-1)
            feature_cols.append(name)
        name=f"{col}_mean7"
        df[name]=grouped[col].transform(lambda s:s.rolling(7,min_periods=3).mean())
        feature_cols.append(name)
    day = df.date.dt.dayofyear
    df["day_sin"]=np.sin(2*np.pi*day/365.25); df["day_cos"]=np.cos(2*np.pi*day/365.25)
    df["month_sin"]=np.sin(2*np.pi*df.date.dt.month/12); df["month_cos"]=np.cos(2*np.pi*df.date.dt.month/12)
    feature_cols += ["day_sin","day_cos","month_sin","month_cos","latitude","longitude"]
    for target in ("tmax","tmin","rain_mm"):
        df[f"target_{target}_next"] = grouped[target].shift(-1)
    df["target_rain_next"]=(df["target_rain_mm_next"] > 0.1).astype(float)
    df.loc[df["target_rain_mm_next"].isna(),"target_rain_next"]=np.nan
    df=df.dropna(subset=["target_tmax_next","target_tmin_next","target_rain_next"])
    return df, feature_cols

def train(data_path="datasets/weather_history.csv", model_dir="models"):
    raw=pd.read_csv(data_path)
    data, features=make_supervised(raw)
    if data.city.nunique()<2:
        raise ValueError(f"Only {data.city.nunique()} city found. Need nationwide CSV, not Patna-only. Run: python -m ml.data_pipeline --years 10")
    if len(data)<1000: raise ValueError(f"Only {len(data)} training rows. Download more historical data.")
    # Global chronological holdout: no future dates in training.
    unique_dates=np.array(sorted(data.date.unique()))
    split_date=pd.Timestamp(unique_dates[int(len(unique_dates)*0.8)])
    train_df=data[data.date < split_date]
    test_df=data[data.date >= split_date]
    # Bound RAM/time on ordinary laptops while keeping every city represented.
    train_df=(train_df.groupby("city", group_keys=False)
              .apply(lambda part: part.sample(n=min(len(part), 1800), random_state=42))
              .sort_values("date"))
    if len(test_df)<50: raise ValueError("Not enough test rows for reliable evaluation.")
    Xtr=train_df[features]; Xte=test_df[features]
    ytr=train_df[["target_tmax_next","target_tmin_next"]]
    yte=test_df[["target_tmax_next","target_tmin_next"]]
    temp=Pipeline([("imputer",SimpleImputer(strategy="median")),
        ("model",RandomForestRegressor(n_estimators=110,max_depth=14,min_samples_leaf=3,
                                       max_features=0.85,random_state=42,n_jobs=-1))])
    temp.fit(Xtr,ytr); pred=temp.predict(Xte)
    temp_metrics={
        "mae_max_temp_c":round(float(mean_absolute_error(yte.iloc[:,0],pred[:,0])),3),
        "rmse_max_temp_c":round(float(np.sqrt(mean_squared_error(yte.iloc[:,0],pred[:,0]))),3),
        "mae_min_temp_c":round(float(mean_absolute_error(yte.iloc[:,1],pred[:,1])),3),
        "rmse_min_temp_c":round(float(np.sqrt(mean_squared_error(yte.iloc[:,1],pred[:,1]))),3),
        "r2_max_temp":round(float(r2_score(yte.iloc[:,0],pred[:,0])),3),
        "r2_min_temp":round(float(r2_score(yte.iloc[:,1],pred[:,1])),3),
    }
    yr=train_df.target_rain_next.astype(int); yt=test_df.target_rain_next.astype(int)
    rain=Pipeline([("imputer",SimpleImputer(strategy="median")),
        ("model",RandomForestClassifier(n_estimators=110,max_depth=14,min_samples_leaf=3,
                                        class_weight="balanced",random_state=42,n_jobs=-1))])
    rain.fit(Xtr,yr); rp=rain.predict(Xte)
    rm={"accuracy":round(float(accuracy_score(yt,rp)),3),
        "precision":round(float(precision_score(yt,rp,zero_division=0)),3),
        "recall":round(float(recall_score(yt,rp,zero_division=0)),3),
        "f1":round(float(f1_score(yt,rp,zero_division=0)),3),
        "confusion_matrix":confusion_matrix(yt,rp,labels=[0,1]).tolist()}
    if yt.nunique()>1 and len(rain.classes_)>1:
        rm["roc_auc"]=round(float(roc_auc_score(yt,rain.predict_proba(Xte)[:,list(rain.classes_).index(1)])),3)
    dest=Path(model_dir); dest.mkdir(parents=True,exist_ok=True)
    meta={"scope":"India multi-location","cities":sorted(raw.city.dropna().unique().tolist()),
          "city_count":int(raw.city.nunique()),"states_count":int(raw.state.nunique()) if "state" in raw else None,
          "historical_model":str(raw.historical_model.dropna().iloc[0]) if "historical_model" in raw and raw.historical_model.notna().any() else "ERA5",
          "data_start":str(data.date.min().date()),"data_end":str(data.date.max().date())}
    bundle={"pipeline":temp,"features":features,"trained_through":str(train_df.date.max().date()),"metadata":meta}
    joblib.dump(bundle,dest/"temperature_model.joblib")
    joblib.dump({"pipeline":rain,"features":features,"trained_through":str(train_df.date.max().date()),"metadata":meta},dest/"rainfall_model.joblib")
    report={"scope":"India-wide multi-city model","coverage":meta,"training_rows":len(train_df),"test_rows":len(test_df),
            "test_period_start":str(test_df.date.min().date()),"test_period_end":str(test_df.date.max().date()),
            "temperature_regression":temp_metrics,"rainfall_classification":rm,
            "data_source":"Open-Meteo Historical Weather API / ERA5 reanalysis (reanalysis estimates, not direct station observations)",
            "split":"Chronological 80/20 date holdout; cities retained in both periods; no random row split",
            "rain_target":"Next-day precipitation > 0.1 mm"}
    (dest/"evaluation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2)); return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="datasets/weather_history.csv")
    p.add_argument("--models",default="models")
    a=p.parse_args(); train(a.data,a.models)
