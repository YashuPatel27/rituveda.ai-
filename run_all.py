"""One-command RituVeda AI data download + local ML training."""
import argparse
from ml.data_pipeline import collect_india
from ml.train_models import train

def main():
    p = argparse.ArgumentParser(description="Download India-wide weather data and train RituVeda AI models")
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--request-delay", type=int, default=3)
    p.add_argument("--batch-delay", type=int, default=20)
    p.add_argument("--model", choices=["era5", "era5_land"], default="era5")
    a = p.parse_args()

    print("\\n=== STEP 1/2: RESUMABLE INDIA-WIDE DATA DOWNLOAD ===", flush=True)
    data = collect_india(
        years=a.years, model=a.model, resume=True,
        batch_size=a.batch_size, request_delay=a.request_delay,
        batch_delay=a.batch_delay
    )
    print("\\n=== STEP 2/2: TRAINING INDIA-WIDE ML MODELS ===", flush=True)
    report = train("datasets/weather_history.csv", "models")
    print("\\nSUCCESS: Data collection and ML training completed.")
    print(f"Cities in dataset: {data.city.nunique()}")
    print(f"Training rows: {report['training_rows']:,}")
    print("Models saved in models/")

if __name__ == "__main__":
    main()
