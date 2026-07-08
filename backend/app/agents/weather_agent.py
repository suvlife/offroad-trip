"""Weather agent - fetches weather and generates off-road driving advisories.

Stage 2 of the pipeline. Runs in parallel for all cities along the route.
"""

import logging
from typing import Dict, Any, List

from app.services import weather_service

logger = logging.getLogger(__name__)


async def fetch_weather_for_cities(cities: List[str], days: int = 7) -> Dict[str, Dict[str, Any]]:
    """Fetch weather for multiple cities in parallel.

    Returns: {city_name: weather_data}
    """
    import asyncio

    tasks = [weather_service.get_weather(city, days) for city in cities]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    weather_map = {}
    for city, result in zip(cities, results):
        if isinstance(result, Exception):
            logger.error(f"Weather fetch failed for {city}: {result}")
            weather_map[city] = {"city": city, "forecasts": [], "error": str(result)}
        else:
            weather_map[city] = result

    return weather_map


async def generate_advisory(weather_map: Dict[str, Dict[str, Any]]) -> str:
    """Generate a combined weather advisory for the entire route."""
    advisories = []
    for city, data in weather_map.items():
        advisory = await weather_service.get_weather_advisory(data)
        advisories.append(f"【{city}】{advisory}")
    return "\n\n".join(advisories)


def format_weather_for_planner(weather_map: Dict[str, Dict[str, Any]]) -> str:
    """Format weather data as a concise string for the planner agent prompt."""
    lines = []
    for city, data in weather_map.items():
        if not data.get("forecasts"):
            lines.append(f"{city}: 天气数据暂不可用")
            continue

        forecasts = data["forecasts"][:5]  # first 5 days
        weather_lines = []
        for f in forecasts:
            weather_lines.append(
                f"  {f['date']}: {f['weather_condition']}, "
                f"{f['temperature_low']}~{f['temperature_high']}°C, "
                f"降水{f.get('precipitation', 0)}mm"
            )
        lines.append(f"{city}:\n" + "\n".join(weather_lines))

    return "\n".join(lines) if lines else "天气数据暂不可用"
