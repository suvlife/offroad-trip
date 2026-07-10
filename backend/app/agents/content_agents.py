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
            prompt=prompt, system_prompt=system, json_mode=True, max_tokens=16384
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
            prompt=prompt, system_prompt=system, json_mode=True, max_tokens=16384
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
            prompt=prompt, system_prompt=system, json_mode=True, max_tokens=16384
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
    """Enrich every day's POIs, meals, and history in parallel.

    POIs/meals belong to a day_plan, so we group by day (not by city) and enrich
    each item exactly once, using the day's destination city (last segment's
    to_name) as LLM context. This avoids the previous behaviour where a POI on a
    multi-segment day (A->B->C) was collected under every endpoint city and thus
    enriched several times, with concurrent tasks mutating the same POI dict.
    """
    import asyncio

    tasks = []
    task_meta = []  # parallel list: (kind, day) describing each task

    for day in route_data.get("day_plans", []):
        segments = day.get("segments", [])
        city = ""
        if segments:
            city = segments[-1].get("to_name", "") or segments[0].get("from_name", "")
        if not city:
            city = day.get("theme", "") or route_data.get("destination", "")

        pois = day.get("pois", [])
        meals = day.get("meals", [])
        scenic_names = [p.get("name", "") for p in pois if p.get("name")]

        tasks.append(enrich_scenic(city, pois))
        task_meta.append(("scenic", day))
        tasks.append(enrich_food(city, meals))
        task_meta.append(("food", day))
        tasks.append(enrich_history(city, scenic_names))
        task_meta.append(("history", day))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Scenic/food results are merged in-place; history returns new story lists.
    all_stories = []
    for (kind, day), result in zip(task_meta, results):
        if kind == "history" and isinstance(result, list):
            for story in result:
                story.setdefault("day_number", day.get("day_number", 0))
            all_stories.extend(result)

    route_data["story_cards"] = all_stories
    return route_data
