"""Open-Meteo geocoding + daily forecast. Failures come back as {"ok": False, "error": ...}, never invented weather."""
from datetime import date, timedelta

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 16  # Open-Meteo's free forecast horizon: today + 15 days

# WMO weather codes used by Open-Meteo, mapped to plain words
WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "heavy rain showers", 82: "violent rain showers", 85: "snow showers", 86: "snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail",
}


def _get(url: str, params: dict) -> dict:
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()  # 4xx/5xx become requests.HTTPError (a RequestException)
    return resp.json()


def get_forecast(city: str, start: date, end: date, today: date | None = None) -> dict:
    today = today or date.today()
    horizon = today + timedelta(days=FORECAST_DAYS - 1)
    first, last = max(start, today), min(end, horizon)  # the part of the trip that can be forecast
    if first > last:
        reason = "the trip dates are in the past" if end < today else f"Open-Meteo only forecasts up to {horizon}"
        return {"ok": False, "error": f"No forecast available for {start} to {end}: {reason}."}

    try:
        places = _get(GEOCODE_URL, {"name": city, "count": 1, "language": "en", "format": "json"}).get("results")
        if not places:
            return {"ok": False, "error": f"Destination '{city}' was not found by the geocoding service."}
        place = places[0]
        daily = _get(FORECAST_URL, {
            "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
            "start_date": first.isoformat(), "end_date": last.isoformat(),
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        })["daily"]
        days = [
            {"date": d, "conditions": WMO_CODES.get(code, f"code {code}"), "min_c": lo, "max_c": hi,
             "precipitation_mm": mm, "rain_chance_pct": pct}
            for d, code, lo, hi, mm, pct in zip(
                daily["time"], daily["weather_code"], daily["temperature_2m_min"], daily["temperature_2m_max"],
                daily["precipitation_sum"], daily["precipitation_probability_max"])
        ]
    except (requests.RequestException, ValueError, KeyError) as exc:  # network, HTTP, bad JSON, unexpected shape
        return {"ok": False, "error": f"Weather service unavailable ({type(exc).__name__}: {exc})."}

    # Pre-computed totals so the small model never has to do arithmetic
    chances = [d["rain_chance_pct"] for d in days if d["rain_chance_pct"] is not None]
    result = {
        "ok": True,
        "location": ", ".join(p for p in (place.get("name"), place.get("country")) if p),
        "summary": {
            "lowest_c": min((d["min_c"] for d in days if d["min_c"] is not None), default=None),
            "highest_c": max((d["max_c"] for d in days if d["max_c"] is not None), default=None),
            "total_precipitation_mm": round(sum(d["precipitation_mm"] or 0 for d in days), 1),
            "max_rain_chance_pct": max(chances, default=None),
        },
        "days": days,
        "source": "Open-Meteo.com",
    }
    if (first, last) != (start, end):
        result["note"] = f"Forecast covers only {first} to {last}; other trip days are outside the forecast window."
    return result
