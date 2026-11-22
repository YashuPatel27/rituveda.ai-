# IMD official-system integration status

This build keeps third-party/modelled weather data and the locally trained ML output clearly separated. The existing live dashboard currently fetches its forecast from Open-Meteo. It does **not** claim that those values are IMD-issued forecasts.

For an official IMD connection, use the IMD API portal and its current API reference:
- https://api.imd.gov.in/public/
- https://api.imd.gov.in/public/api_reference.html

The IMD portal may require account registration, approved access, an API token and compliance with current terms. Do not hardcode credentials or guess endpoint paths/response fields. Once the project's IMD access details are available, implement the adapter against the exact documented endpoint and label its results as IMD. Until then, show IMD bulletins/advisories as an external official reference rather than presenting Open-Meteo output as IMD data.

This is intentional source transparency, not a claim that the IMD API is already connected.
