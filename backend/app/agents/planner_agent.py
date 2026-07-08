"""Planner agent - generates the route skeleton using LLM.

Stage 3 of the pipeline. Calls the LLM with vehicle/weather/geo context
to produce the initial route plan (city sequence, daily segments, POIs, meals, hotels).
"""

import logging
from typing import Dict, Any, List

from app.services import llm_service
from app.prompts.planner import PLANNER_SYSTEM, build_planner_prompt

logger = logging.getLogger(__name__)


async def plan_route(
    departure: str,
    destination: str,
    start_date: str,
    days: int,
    trip_type: str,
    vehicle_type: str,
    adults: int,
    children: int,
    budget: float,
    theme: str,
    preferences: List[str],
    weather_info: str,
    geo_info: str,
) -> Dict[str, Any]:
    """Generate the route skeleton via LLM.

    Returns: parsed JSON dict with route structure, or empty dict on failure.
    """
    prompt = build_planner_prompt(
        departure=departure,
        destination=destination,
        start_date=start_date,
        days=days,
        trip_type=trip_type,
        vehicle_type=vehicle_type,
        adults=adults,
        children=children,
        budget=budget,
        theme=theme,
        preferences=preferences,
        weather_info=weather_info,
        geo_info=geo_info,
    )

    try:
        content = await llm_service.call_llm(
            prompt=prompt,
            system_prompt=PLANNER_SYSTEM,
            json_mode=True,
            max_tokens=16384,
            temperature=0.3,  # lower temp = faster reasoning, more deterministic
        )
        result = llm_service.parse_json_response(content)

        # Ensure required fields
        result.setdefault("title", f"{departure}至{destination}越野自驾")
        result.setdefault("theme", theme or "回归自然")
        result.setdefault("departure", departure)
        result.setdefault("destination", destination)
        result.setdefault("vehicle_type", vehicle_type)
        result.setdefault("trip_type", trip_type)
        result.setdefault("adults", adults)
        result.setdefault("children", children)
        result.setdefault("budget", budget)
        result.setdefault("status", "draft")
        result.setdefault("terrain_difficulty", 2)
        result.setdefault("nature_score", 4)
        result.setdefault("overall_tips", "")
        result.setdefault("day_plans", [])

        return result
    except Exception as e:
        logger.error(f"Route planning failed: {e}")
        raise
