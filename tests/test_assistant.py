import unittest
from modules.assistant import answer_weather_question


SAMPLE_WEATHER = {
    "current": {
        "temperature_2m": 28.4,
        "apparent_temperature": 29.1,
        "relative_humidity_2m": 65,
        "wind_speed_10m": 12.5,
        "precipitation": 0.0
    },
    "daily": {
        "time": ["2026-11-13", "2026-11-14", "2026-11-15",
                 "2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19"],
        "temperature_2m_max": [27.6, 28.2, 29.5, 28.4, 26.2, 25.8, 25.6],
        "temperature_2m_min": [19.5, 19.5, 19.1, 19.2, 16.1, 15.6, 15.1],
        "precipitation_probability_max": [0, 10, 20, 5, 0, 0, 2],
        "precipitation_sum": [0.1, 0, 0, 0, 0, 0, 0],
        "wind_speed_10m_max": [12, 14, 15, 12, 10, 9, 9],
        "uv_index_max": [5, 6, 6, 5, 4, 4, 4],
        "sunrise": ["06:00"] * 7,
        "sunset": ["17:00"] * 7
    },
    "hourly": {
        "time": [f"2026-11-14T{hour:02d}:00" for hour in range(24)],
        "relative_humidity_2m": [60 + hour % 5 for hour in range(24)]
    }
}


class WeatherAssistantTests(unittest.TestCase):
    def ask(self, question, history=None):
        return answer_weather_question(
            question, "Patna, Bihar, India", SAMPLE_WEATHER, history=history
        )

    def test_current_temperature(self):
        self.assertIn("28.4", self.ask("What is the current temperature?"))

    def test_rain_tomorrow(self):
        answer = self.ask("Will it rain tomorrow?")
        self.assertIn("2026-11-14", answer)
        self.assertIn("10%", answer)

    def test_hinglish(self):
        answer = self.ask("Kal baarish hogi kya?")
        self.assertIn("2026-11-14", answer)

    def test_seven_day_forecast(self):
        answer = self.ask("Show me the forecast for next 7 days")
        self.assertIn("2026-11-19", answer)

    def test_weekday_resolution(self):
        answer = self.ask("Will it rain on Monday?")
        self.assertIn("2026-11-16", answer)

    def test_follow_up_context(self):
        history = [{"role": "user", "content": "How humid is it?"}]
        answer = self.ask("What about tomorrow?", history)
        self.assertIn("2026-11-14", answer)


if __name__ == "__main__":
    unittest.main()
