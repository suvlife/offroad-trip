"""Weather service - 和风天气 (QWeather) optimized for China.

Falls back to wttr.in (free, no key) if QWeather key not configured.
Weather data feeds the weather agent for off-road driving decisions.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def get_weather_qweather(city: str, days: int = 7) -> Optional[Dict[str, Any]]:
    """Fetch weather from QWeather (和风天气). Needs QWEATHER_KEY."""
    api_key = settings.QWEATHER_KEY
    if not api_key:
        return None

    base = settings.QWEATHER_BASE_URL

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: city lookup -> location ID
            lookup_resp = await client.get(
                f"{base}/geo/v2/city/lookup",
                params={"location": city, "key": api_key, "number": 1},
            )
            lookup_resp.raise_for_status()
            lookup_data = lookup_resp.json()

        if not lookup_data.get("location"):
            return None

        location_id = lookup_data["location"][0]["id"]
        lat = lookup_data["location"][0]["lat"]
        lon = lookup_data["location"][0]["lon"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 2: 7-day forecast
            forecast_resp = await client.get(
                f"{base}/v7/weather/7d",
                params={"location": location_id, "key": api_key},
            )
            forecast_resp.raise_for_status()
            forecast_data = forecast_resp.json()

        forecasts = []
        for day in forecast_data.get("daily", [])[:days]:
            forecasts.append({
                "date": day.get("fxDate", ""),
                "temperature_high": float(day.get("tempMax", 0)),
                "temperature_low": float(day.get("tempMin", 0)),
                "weather_condition": day.get("textDay", ""),
                "icon": day.get("iconDay", ""),
                "humidity": float(day.get("humidity", 0)),
                "wind_speed": float(day.get("windSpeedDay", 0)),
                "precipitation": float(day.get("precip", 0)),
            })

        return {
            "city": city,
            "lat": lat,
            "lng": lon,
            "forecasts": forecasts,
        }
    except Exception as e:
        logger.error(f"QWeather API error for {city}: {e}")
        return None


async def get_weather_wttr(city: str, days: int = 7) -> Optional[Dict[str, Any]]:
    """Fallback: fetch weather from wttr.in (free, no key)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://wttr.in/{city}?format=j1")
            resp.raise_for_status()
            data = resp.json()

        forecasts = []
        for day in data.get("weather", [])[:days]:
            hourly = day.get("hourly", [{}])
            forecasts.append({
                "date": day.get("date", ""),
                "temperature_high": float(day.get("maxtempC", 0)),
                "temperature_low": float(day.get("mintempC", 0)),
                "weather_condition": hourly[0].get("weatherDesc", [{}])[0].get("value", ""),
                "icon": hourly[0].get("weatherCode", ""),
                "humidity": float(hourly[0].get("humidity", "0")),
                "wind_speed": float(hourly[0].get("windspeedKmph", "0")),
                "precipitation": float(hourly[0].get("precipMM", "0")),
            })

        current = data.get("current_condition", [{}])[0]
        return {
            "city": city,
            "current": {
                "temperature": current.get("temp_C", ""),
                "weather_desc": current.get("weatherDesc", [{}])[0].get("value", ""),
            },
            "forecasts": forecasts,
        }
    except Exception as e:
        logger.error(f"wttr.in API error for {city}: {e}")
        return None


async def get_weather(city: str, days: int = 7) -> Dict[str, Any]:
    """Get weather for a city. Tries QWeather first, falls back to wttr.in."""
    # Try QWeather (better for China)
    if settings.QWEATHER_KEY:
        result = await get_weather_qweather(city, days)
        if result:
            return result

    # Fallback to wttr.in
    result = await get_weather_wttr(city, days)
    if result:
        return result

    # Ultimate fallback
    return {
        "city": city,
        "forecasts": [],
        "error": "Weather data unavailable",
    }


async def get_weather_advisory(weather_data: Dict[str, Any]) -> str:
    """Generate a weather advisory for off-road driving.

    Simple rule-based: heavy rain / snow -> avoid off-road; light rain -> caution.
    """
    if not weather_data or not weather_data.get("forecasts"):
        return "天气数据暂不可用，建议出发前查看实时天气。"

    advisories = []
    for day in weather_data["forecasts"]:
        condition = day.get("weather_condition", "")
        precip = day.get("precipitation", 0)
        temp_low = day.get("temperature_low", 0)

        date = day.get("date", "")
        notes = []

        if any(w in condition for w in ["大雨", "暴雨", "大暴雨"]):
            notes.append("大雨天气，非铺装路面易泥泞打滑，建议避开越野路段，走铺装公路")
        elif any(w in condition for w in ["中雨", "阵雨"]):
            notes.append("有降雨，轻度越野路段需谨慎驾驶，注意防滑")
        elif any(w in condition for w in ["雪", "暴雪"]):
            notes.append(f"降雪天气（最低{temp_low}°C），需雪地胎/防滑链，越野路段建议绕行")
        elif any(w in condition for w in ["雾", "霾"]):
            notes.append("能见度低，山路弯道需减速慢行，开启雾灯")
        elif precip > 10:
            notes.append(f"降水量较大（{precip}mm），注意路面积水")
        else:
            notes.append("天气良好，适合越野及户外活动")

        if temp_low < 0:
            notes.append(f"气温较低（{temp_low}°C），注意防寒保暖，检查防冻液")

        advisories.append(f"{date}: {'；'.join(notes)}")

    return "；\n".join(advisories)
