"""Content enrichment agents - scenic, food, history.

Stage 5 of the pipeline. These run in parallel, each enriching the route
skeleton with detailed content for each city along the route.
"""

import logging
from typing import Dict, Any, List

from app.services import llm_service
from app.prompts.content import (
    build_scenic_prompt,
    build_food_prompt,
    build_history_prompt,
)

logger = logging.getLogger(__name__)


async def enrich_scenic(city: str, pois: List[Dict]) -> List[Dict]:
    """Enrich POIs with detailed features and anecdotes.

    Args:
        city: city name
        pois: list of POI dicts (will be enriched in-place)

    Returns: enriched POIs
    """
    if not pois:
        return pois

    scenic_list = "\n".join(
        f"- {p.get('name', '')}: {p.get('description', '')}"
        for p in pois if p.get("name")
    )

    if not scenic_list.strip():
        return pois

    system, prompt = build_scenic_prompt(city, scenic_list)

    try:
        content = await llm_service.call_llm(
            prompt=prompt, system_prompt=system, json_mode=True, max_tokens=4096
        )
        result = llm_service.parse_json_response(content)
        enriched_pois = result.get("pois", [])

        # Merge enriched data back into original POIs by name
        enriched_map = {p["name"]: p for p in enriched_pois if p.get("name")}
        for poi in pois:
            match = enriched_map.get(poi.get("name", ""))
            if match:
                poi["feature"] = match.get("feature", poi.get("feature", ""))
                poi["anecdote"] = match.get("anecdote", poi.get("anecdote", ""))
                poi["historical_figure"] = match.get("historical_figure", "")
                poi["historical_event"] = match.get("historical_event", "")
                if match.get("description"):
                    poi["description"] = match["description"]
                if match.get("duration_minutes"):
                    poi["duration_minutes"] = match["duration_minutes"]

        return pois
    except Exception as e:
        logger.error(f"Scenic enrichment failed for {city}: {e}")
        return pois


async def enrich_food(city: str, meals: List[Dict]) -> List[Dict]:
    """Enrich meals with stories and local specialty info."""
    if not meals:
        return meals

    food_list = "\n".join(
        f"- {m.get('restaurant_name', '')} ({m.get('cuisine_type', '')})"
        for m in meals if m.get("restaurant_name")
    )

    if not food_list.strip():
        return meals

    system, prompt = build_food_prompt(city, food_list)

    try:
        content = await llm_service.call_llm(
            prompt=prompt, system_prompt=system, json_mode=True, max_tokens=4096
        )
        result = llm_service.parse_json_response(content)
        enriched_meals = result.get("meals", [])

        # Merge by restaurant_name
        enriched_map = {m["restaurant_name"]: m for m in enriched_meals if m.get("restaurant_name")}
        for meal in meals:
            match = enriched_map.get(meal.get("restaurant_name", ""))
            if match:
                meal["story"] = match.get("story", "")
                meal["is_local_specialty"] = match.get("is_local_specialty", False)
                if match.get("recommendation"):
                    meal["recommendation"] = match["recommendation"]
                if match.get("cost_per_person"):
                    meal["cost_per_person"] = match["cost_per_person"]

        return meals
    except Exception as e:
        logger.error(f"Food enrichment failed for {city}: {e}")
        return meals


async def enrich_history(city: str, scenic_names: List[str]) -> List[Dict]:
    """Generate history story cards for a city.

    Returns: list of story card dicts.
    """
    names = "、".join(scenic_names) if scenic_names else city

    system, prompt = build_history_prompt(city, names)

    try:
        content = await llm_service.call_llm(
            prompt=prompt, system_prompt=system, json_mode=True, max_tokens=4096
        )
        result = llm_service.parse_json_response(content)
        stories = result.get("stories", [])

        for story in stories:
            story.setdefault("related_city", city)
            story.setdefault("figure", "")
            story.setdefault("event", "")
            story.setdefault("anecdote", "")
            story.setdefault("story_text", "")

        return stories
    except Exception as e:
        logger.error(f"History enrichment failed for {city}: {e}")
        return []


async def enrich_all_cities(route_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich all cities in the route in parallel.

    Runs scenic, food, and history agents for each city concurrently.
    """
    import asyncio

    # Group POIs and meals by city (using segment to_name as city proxy)
    city_data: Dict[str, Dict] = {}

    for day in route_data.get("day_plans", []):
        day_cities = set()
        for seg in day.get("segments", []):
            day_cities.add(seg.get("to_name", ""))
            day_cities.add(seg.get("from_name", ""))

        for city in day_cities:
            if not city:
                continue
            if city not in city_data:
                city_data[city] = {"pois": [], "meals": [], "scenic_names": []}

            # Collect POIs for this city (all POIs in days that touch this city)
            for poi in day.get("pois", []):
                city_data[city]["pois"].append(poi)
                city_data[city]["scenic_names"].append(poi.get("name", ""))

            for meal in day.get("meals", []):
                city_data[city]["meals"].append(meal)

    # Run enrichment in parallel for all cities
    tasks = []
    cities = list(city_data.keys())

    for city in cities:
        data = city_data[city]
        tasks.append(enrich_scenic(city, data["pois"]))
        tasks.append(enrich_food(city, data["meals"]))
        tasks.append(enrich_history(city, data["scenic_names"]))

    results = await asyncio.gather(*results if False else [], return_exceptions=True) if False else await _run_tasks(tasks, cities)

    # Collect all story cards
    all_stories = []
    # results layout: for each city [scenic_result, food_result, history_result]
    for i, city in enumerate(cities):
        base = i * 3
        # scenic and food results are merged in-place, history returns new list
        if base + 2 < len(results):
            history_result = results[base + 2]
            if isinstance(history_result, list):
                all_stories.extend(history_result)

    route_data["story_cards"] = all_stories
    return route_data


async def _run_tasks(tasks, cities):
    """Helper to run tasks and return results."""
    import asyncio
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
