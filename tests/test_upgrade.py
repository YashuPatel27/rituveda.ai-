import unittest
import pandas as pd
from modules.alerts import build_alerts
from ml.train_models import make_supervised
from modules.assistant import answer_weather_question


class UpgradeTests(unittest.TestCase):
    def test_uv_alert(self):
        alerts = build_alerts(
            {"temperature_2m": 25},
            {"uv_index_max": [9], "precipitation_probability_max": [0],
             "temperature_2m_max": [28], "wind_speed_10m_max": [10]},
            None
        )
        self.assertTrue(any("UV" in a["title"] for a in alerts))

    def test_air_quality_alert(self):
        alerts = build_alerts(
            {"temperature_2m": 25},
            {"uv_index_max": [2], "precipitation_probability_max": [0],
             "temperature_2m_max": [28], "wind_speed_10m_max": [10]},
            {"current": {"us_aqi": 165}}
        )
        self.assertTrue(any("Air quality" in a["title"] for a in alerts))

    def test_devanagari_hindi_response(self):
        weather = {
            "current": {"temperature_2m": 28, "apparent_temperature": 29,
                        "relative_humidity_2m": 60, "wind_speed_10m": 8},
            "daily": {"time": ["2026-11-13", "2026-11-14"],
                      "temperature_2m_max": [30, 31], "temperature_2m_min": [20, 21],
                      "precipitation_probability_max": [5, 65],
                      "precipitation_sum": [0, 4], "wind_speed_10m_max": [8, 9],
                      "uv_index_max": [5, 6]},
        }
        answer = answer_weather_question("कल बारिश होगी क्या?", "Patna", weather)
        self.assertIn("बारिश की संभावना", answer)
        self.assertIn("2026-11-14", answer)

    def test_aqi_assistant_answer(self):
        weather = {"current": {}, "daily": {},
                   "air_quality": {"current": {"us_aqi": 72, "european_aqi": 45,
                                               "pm2_5": 18, "pm10": 30}}}
        answer = answer_weather_question("AQI kya hai?", "Patna", weather)
        self.assertIn("AQI", answer)
        self.assertIn("72", answer)

    def test_supervised_data_uses_next_day_target(self):
        raw = pd.DataFrame({
             "date": pd.date_range("2024-01-01", periods=12).astype(str),
            "city": ["Patna"] * 12, "latitude": [25.59] * 12, "longitude": [85.13] * 12,
            "tmax": list(range(20, 32)), "tmin": list(range(10, 22)),
            "rain_mm": [0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            "wind_max": [5] * 12, "humidity_mean": [60] * 12,
            "pressure_mean": [1010] * 12
        })
        frame, features = make_supervised(raw)
        self.assertEqual(frame.iloc[0]["target_tmax_next"], 21)
        self.assertIn("tmax_lag1", features)
        self.assertLess(len(frame), len(raw))


if __name__ == "__main__":
    unittest.main()
