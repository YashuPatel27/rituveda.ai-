"""Resumable India-wide Open-Meteo historical data collector.

Downloads sequentially in batches, retries rate limits, and checkpoints after
each city. Run from the project root:
    python run_all.py --years 10
"""
from datetime import date, timedelta
from pathlib import Path
import argparse
import email.utils
import time
import random

import pandas as pd
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
RAW_MAP = {
    "temperature_2m_max": "tmax",
    "temperature_2m_min": "tmin",
    "precipitation_sum": "rain_mm",
    "wind_speed_10m_max": "wind_max",
    "relative_humidity_2m_mean": "humidity_mean",
    "pressure_msl_mean": "pressure_mean",
}

def _retry_wait(response, attempt):
    """Respect Retry-After where supplied; otherwise exponential backoff."""
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            return min(300.0, max(5.0, float(retry_after)))
        except ValueError:
            try:
                dt = email.utils.parsedate_to_datetime(retry_after)
                return min(300.0, max(5.0, (dt - email.utils.parsedate_to_datetime(
                    email.utils.formatdate(usegmt=True))).total_seconds()))
            except Exception:
                pass
    return min(180.0, 15.0 * (2 ** attempt)) + random.uniform(0, 3)

def fetch_city(city, state, lat, lon, start, end, model="era5",
               session=None, max_retries=7):
    params = {
        "latitude": float(lat), "longitude": float(lon),
        "start_date": start, "end_date": end,
        "daily": list(RAW_MAP), "timezone": "auto", "models": model
    }
    client = session or requests.Session()
    last_error = None
    for attempt in range(max_retries):
        response = None
        try:
            response = client.get(ARCHIVE_URL, params=params, timeout=(20, 180))
            if response.status_code == 429 or response.status_code >= 500:
                last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
                if attempt + 1 < max_retries:
                    wait = _retry_wait(response, attempt)
                    print(f"  API HTTP {response.status_code}; waiting {wait:.0f}s "
                          f"(retry {attempt + 1}/{max_retries})", flush=True)
                    time.sleep(wait)
                    continue
                break
            response.raise_for_status()
            payload = response.json()
            daily = payload.get("daily", {})
            if not daily.get("time"):
                raise RuntimeError("API returned no daily records")
            frame = pd.DataFrame({"date": daily["time"]})
            for api_col, col in RAW_MAP.items():
                values = daily.get(api_col)
                frame[col] = values if values is not None else [None] * len(frame)
            frame["city"], frame["state"], frame["country"] = city, state, "India"
            frame["latitude"], frame["longitude"] = float(lat), float(lon)
            frame["historical_model"] = model
            return frame
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            if response is not None and response.status_code == 429:
                wait = _retry_wait(response, attempt)
            else:
                wait = min(120.0, 5.0 * (2 ** attempt)) + random.uniform(0, 2)
            if attempt + 1 < max_retries:
                print(f"  {type(exc).__name__}: {exc}; retrying in {wait:.0f}s "
                      f"({attempt + 1}/{max_retries})", flush=True)
                time.sleep(wait)
    raise RuntimeError(f"{city}: request failed after {max_retries} attempts: {last_error}")

def collect_india(years=10, cities_file="datasets/india_cities.csv",
                  output="datasets/weather_history.csv", model="era5",
                  resume=True, batch_size=4, request_delay=3, batch_delay=20):
    cities = pd.read_csv(cities_file)
    required = {"city", "state", "latitude", "longitude"}
    missing = required - set(cities.columns)
    if missing:
        raise ValueError(f"City file missing columns: {sorted(missing)}")

    end = date.today() - timedelta(days=5)
    start = end - timedelta(days=365 * int(years))
    expected_days = (end - start).days + 1
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    existing = pd.read_csv(out) if resume and out.exists() else pd.DataFrame()
    # Only skip cities whose stored history covers essentially the requested period.
    completed = set()
    if not existing.empty and {"city", "date"}.issubset(existing.columns):
        counts = existing.dropna(subset=["date"]).groupby("city")["date"].nunique()
        completed = set(counts[counts >= int(expected_days * 0.97)].index.astype(str))

    frames = [existing] if not existing.empty else []
    session = requests.Session()
    session.headers.update({"User-Agent": "RituVedaAI/1.0 (historical weather data collector)"})
    total = len(cities)
    pending = [(i, row) for i, row in cities.iterrows()
               if str(row["city"]) not in completed]
    print(f"INDIA DATA COLLECTION: {total} locations | {start} to {end} | "
          f"{model} | batch size {batch_size}", flush=True)
    print(f"Already complete: {len(completed)} | Remaining: {len(pending)}", flush=True)

    for pos, (i, row) in enumerate(pending):
        city = str(row["city"])
        print(f"[{i+1}/{total}] Downloading {city}, {row['state']}...", flush=True)
        frame = fetch_city(city, row["state"], row["latitude"], row["longitude"],
                           start.isoformat(), end.isoformat(), model, session)
        frames.append(frame)
        # Durable checkpoint after every successful city.
        combined = pd.concat(frames, ignore_index=True)
        combined = combined.drop_duplicates(["city", "date"], keep="last")
        combined.to_csv(out, index=False)
        print(f"  SAVED {len(frame):,} daily rows | total cities "
              f"{combined['city'].nunique()}", flush=True)

        # Small spacing between API calls, plus a longer pause after each batch.
        if pos + 1 < len(pending):
            time.sleep(max(0, request_delay))
            if (pos + 1) % max(1, batch_size) == 0:
                print(f"--- Batch {(pos + 1)//max(1,batch_size)} complete; "
                      f"cooling down {batch_delay}s ---", flush=True)
                time.sleep(max(0, batch_delay))

    if not frames:
        raise RuntimeError("No weather records collected.")
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(["city", "date"], keep="last")
    combined = combined.sort_values(["city", "date"])
    combined.to_csv(out, index=False)
    print("\nCOLLECTION COMPLETE", flush=True)
    print(f"Cities: {combined.city.nunique()} | Rows: {len(combined):,} | File: {out}", flush=True)
    return combined

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect India-wide historical weather")
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--cities", default="datasets/india_cities.csv")
    parser.add_argument("--output", default="datasets/weather_history.csv")
    parser.add_argument("--model", choices=["era5", "era5_land"], default="era5")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--request-delay", type=int, default=3)
    parser.add_argument("--batch-delay", type=int, default=20)
    args = parser.parse_args()
    collect_india(args.years, args.cities, args.output, args.model,
                  not args.no_resume, args.batch_size, args.request_delay, args.batch_delay)
