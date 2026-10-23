"""Live Weather Service with OpenWeatherMap integration, caching, and fallback.

Strictly distinguishes:
- 'live': Real-time or 5-day/3-hour forecast from OpenWeatherMap API
- 'historical': Sourced from the historical menu dataset CSV for past dates
- 'demo': Explicitly requested demo condition
- 'unavailable': API key missing, network failure, or no historical entry

Never claims historical data is a live forecast.
Never fabricates a live response when the API key is missing.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any
import httpx

from backend.app.services.dataset_service import get_dataset

logger = logging.getLogger("food_optimizer.weather_service")

# Cache for OpenWeatherMap API responses (key: f"{lat}_{lon}", value: (data, timestamp))
_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes


def get_weather_config() -> dict[str, Any]:
    return {
        "api_key": os.getenv("OPENWEATHER_API_KEY", "").strip(),
        "lat": float(os.getenv("WEATHER_LAT", "12.9698")),  # Default: Vellore, Tamil Nadu
        "lon": float(os.getenv("WEATHER_LON", "79.1559")),
        "city": os.getenv("WEATHER_CITY", "Vellore"),
    }


def _get_meal_hour_window(meal: str) -> tuple[int, int]:
    """Return start and end hour for meal periods."""
    m = meal.lower()
    if "breakfast" in m:
        return (7, 10)
    elif "lunch" in m:
        return (12, 15)
    elif "snack" in m:
        return (16, 18)
    elif "dinner" in m:
        return (19, 22)
    return (12, 15)


def fetch_live_weather(lat: float, lon: float, api_key: str) -> dict[str, Any] | None:
    """Query OpenWeatherMap 5-day / 3-hour forecast."""
    cache_key = f"{lat}_{lon}"
    now = time.time()
    if cache_key in _CACHE:
        cached_data, cached_at = _CACHE[cache_key]
        if now - cached_at < CACHE_TTL_SECONDS:
            logger.info("Serving OpenWeatherMap forecast from cache.")
            return cached_data

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                _CACHE[cache_key] = (data, now)
                return data
            elif resp.status_code == 401:
                logger.warning("OpenWeatherMap 401: Invalid or expired API key.")
                return None
            else:
                logger.warning(f"OpenWeatherMap HTTP {resp.status_code}: {resp.text[:200]}")
                return None
    except Exception as e:
        logger.warning(f"OpenWeatherMap request failed: {e}")
        return None


def get_weather_for_meal(
    target_date: str, meal: str = "Lunch", demo_mode: str | None = None
) -> dict[str, Any]:
    """Retrieve weather data distinguishing live, historical, demo, and unavailable states."""
    config = get_weather_config()
    api_key = config["api_key"]
    lat = config["lat"]
    lon = config["lon"]
    city = config["city"]

    # 1. Handle explicit demo mode
    if demo_mode == "rain_storm":
        return {
            "source": "demo_simulation",
            "is_live": False,
            "city": city,
            "target_date": target_date,
            "meal": meal,
            "temperature_c": 24.5,
            "rainfall_mm": 18.5,
            "weather_condition": "Heavy Rain",
            "rain_expected_during_meal": True,
            "rain_forecast_mm": 18.5,
            "pop": 0.90,
            "retrieval_time": datetime.now(timezone.utc).isoformat(),
            "notes": "Demonstration weather profile simulating a monsoonal downpour during meal service.",
        }

    # 2. Try live OpenWeatherMap forecast if API key is present
    if api_key:
        live_data = fetch_live_weather(lat, lon, api_key)
        if live_data and "list" in live_data:
            meal_start, meal_end = _get_meal_hour_window(meal)
            matching_forecasts = []
            
            for item in live_data["list"]:
                # dt_txt format: '2026-10-23 12:00:00'
                dt_txt = item.get("dt_txt", "")
                if target_date in dt_txt:
                    try:
                        item_dt = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
                        if meal_start <= item_dt.hour <= meal_end + 1:
                            matching_forecasts.append(item)
                    except Exception:
                        pass

            if matching_forecasts:
                target_slice = matching_forecasts[0]
                temp = float(target_slice["main"]["temp"])
                weather_desc = target_slice["weather"][0]["description"].title()
                rain_mm = float(target_slice.get("rain", {}).get("3h", 0.0))
                pop = float(target_slice.get("pop", 0.0))
                has_rain = rain_mm > 1.0 or pop >= 0.50

                return {
                    "source": "live_openweathermap",
                    "is_live": True,
                    "city": live_data.get("city", {}).get("name", city),
                    "target_date": target_date,
                    "meal": meal,
                    "temperature_c": round(temp, 1),
                    "rainfall_mm": round(rain_mm, 1),
                    "weather_condition": weather_desc,
                    "rain_expected_during_meal": has_rain,
                    "rain_forecast_mm": round(rain_mm, 1),
                    "pop": round(pop, 2),
                    "forecast_timestamp": target_slice.get("dt_txt"),
                    "retrieval_time": datetime.now(timezone.utc).isoformat(),
                    "notes": f"Live OpenWeatherMap 3-hour forecast for {meal} window ({meal_start}:00 - {meal_end}:00).",
                }

    # 3. Check historical menu dataset for past date
    try:
        df = get_dataset()
        match = df[(df["date"] == target_date) & (df["meal"].str.lower() == meal.lower())]
        if not match.empty:
            row = match.iloc[0]
            temp = float(row["temperature_c"])
            rain_mm = float(row["rainfall_mm"])
            has_rain = rain_mm >= 2.0
            cond = "Rain Showers" if has_rain else ("Sunny / Clear" if temp > 30 else "Partly Cloudy")
            return {
                "source": "dataset_historical",
                "is_live": False,
                "city": city,
                "target_date": target_date,
                "meal": meal,
                "temperature_c": round(temp, 1),
                "rainfall_mm": round(rain_mm, 1),
                "weather_condition": cond,
                "rain_expected_during_meal": has_rain,
                "rain_forecast_mm": round(rain_mm, 1),
                "pop": 0.85 if has_rain else 0.10,
                "retrieval_time": datetime.now(timezone.utc).isoformat(),
                "notes": "Historical observation recorded in dataset for August 2026. This is NOT a live forecast.",
            }
    except Exception as e:
        logger.debug(f"Historical weather lookup failed: {e}")

    # 4. Weather unavailable state
    return {
        "source": "unavailable",
        "is_live": False,
        "city": city,
        "target_date": target_date,
        "meal": meal,
        "temperature_c": None,
        "rainfall_mm": None,
        "weather_condition": "Weather Data Unavailable",
        "rain_expected_during_meal": False,
        "rain_forecast_mm": 0.0,
        "pop": 0.0,
        "retrieval_time": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "Live weather forecast unavailable (OPENWEATHER_API_KEY not configured or outside forecast horizon), "
            "and no historical CSV record exists for this date."
        ),
    }
