"""Orchestrator - the main agent pipeline coordinator.

Runs 6 stages sequentially, emitting SSE events for progress tracking:
  1. Geocode  - address -> coordinates (Tencent Maps)
  2. Weather  - fetch weather for all cities (parallel)
  3. Planning - LLM generates route skeleton (vehicle/weather aware)
  4. Routing  - get real polylines from Tencent Maps direction API
  5. Enrichment - scenic/food/history agents enrich content (parallel)
  6. Assembly - images, costs, douyin links, save to DB
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, List

from app.config import settings
from app.services import qqmap_service, weather_service, llm_service, cost_service, image_service, douyin_service
from app.agents import weather_agent, planner_agent, content_agents
from app.prompts.planner import PLANNER_SYSTEM, build_planner_prompt

logger = logging.getLogger(__name__)


async def _emit(stage: str, status: str, message: str, progress: int) -> str:
    """Format an SSE event string."""
    data = json.dumps({
        "stage": stage,
        "status": status,
        "message": message,
        "progress": progress,
    }, ensure_ascii=False)
    return f"data: {data}\n\n"


async def generate_route_stream(
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
) -> AsyncGenerator[str, None]:
    """Run the full 6-stage agent pipeline, yielding SSE events.

    Yields SSE-formatted strings. The final event contains the complete route data.
    """
    try:
        # ─── Stage 1: Geocode ──────────────────────────────────────────────
        yield await _emit("geocode", "running", "正在定位出发地和目的地...", 5)

        dep_geo = await qqmap_service.geocode(departure)
        dest_geo = await qqmap_service.geocode(destination)

        if not dep_geo or not dest_geo:
            yield await _emit("geocode", "error", "无法定位城市，请检查地名", 5)
            return

        geo_info = (
            f"出发地 {departure}: {dep_geo['lat']},{dep_geo['lng']} ({dep_geo.get('province','')})\n"
            f"目的地 {destination}: {dest_geo['lat']},{dest_geo['lng']} ({dest_geo.get('province','')})"
        )

        yield await _emit("geocode", "done", f"定位完成：{departure} → {destination}", 10)

        # ─── Stage 2: Weather ──────────────────────────────────────────────
        yield await _emit("weather", "running", "正在获取沿途天气...", 15)

        # Cities to check weather for (departure, destination, and we'll add waypoints later)
        weather_cities = [departure, destination]
        weather_map = await weather_agent.fetch_weather_for_cities(weather_cities, days)
        weather_info = weather_agent.format_weather_for_planner(weather_map)
        weather_advisory = await weather_agent.generate_advisory(weather_map)

        yield await _emit("weather", "done", "天气获取完成", 25)

        # ─── Stage 3: Planning (LLM) ───────────────────────────────────────
        yield await _emit("planning", "running", "AI正在规划越野路线...", 30)

        route_data = await planner_agent.plan_route(
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

        # Add weather advisory to each day plan
        for day in route_data.get("day_plans", []):
            day["weather_advisory"] = weather_advisory

        yield await _emit("planning", "done", f"路线规划完成：{route_data.get('title', '')}", 50)

        # ─── Stage 4: Routing (Tencent Maps direction API) ─────────────────
        yield await _emit("routing", "running", "正在获取详细路况和导航...", 55)

        total_distance = 0.0
        total_duration = 0.0

        for day in route_data.get("day_plans", []):
            day_distance = 0.0
            day_duration = 0.0
            for seg in day.get("segments", []):
                # Geocode segment endpoints
                from_geo = await qqmap_service.geocode(seg["from_name"])
                to_geo = await qqmap_service.geocode(seg["to_name"])

                if from_geo and to_geo:
                    route_info = await qqmap_service.plan_driving_route(
                        from_geo["lat"], from_geo["lng"],
                        to_geo["lat"], to_geo["lng"],
                    )
                    if route_info:
                        seg["distance"] = route_info["distance"]
                        seg["duration"] = route_info["duration"]
                        seg["toll_cost"] = route_info["toll"]
                        seg["polyline"] = route_info["polyline"]
                        seg_cost = cost_service.calculate_segment_cost(
                            route_info["distance"], vehicle_type, toll_from_api=route_info["toll"]
                        )
                        seg["fuel_cost"] = seg_cost["fuel_cost"]
                        day_distance += route_info["distance"]
                        day_duration += route_info["duration"]

            day["day_distance"] = round(day_distance, 1)
            day["day_duration"] = round(day_duration, 1)
            total_distance += day_distance
            total_duration += day_duration

        route_data["total_distance"] = round(total_distance, 1)
        route_data["total_duration"] = round(total_duration, 1)

        yield await _emit("routing", "done", f"路况获取完成，总里程{total_distance:.0f}km", 70)

        # ─── Stage 5: Content Enrichment (parallel LLM calls) ──────────────
        yield await _emit("enrichment", "running", "正在丰富景点、美食、历史故事...", 75)

        route_data = await content_agents.enrich_all_cities(route_data)

        yield await _emit("enrichment", "done", "内容丰富完成", 90)

        # ─── Stage 6: Assembly (images, douyin, costs) ─────────────────────
        yield await _emit("assembly", "running", "正在组装图片和视频链接...", 92)

        # Fetch images for POIs (parallel)
        poi_image_tasks = []
        pois_to_update = []
        for day in route_data.get("day_plans", []):
            for poi in day.get("pois", []):
                if poi.get("name"):
                    poi_image_tasks.append(image_service.search_photo(poi["name"], poi["name"]))
                    pois_to_update.append(poi)

        if poi_image_tasks:
            images = await asyncio.gather(*poi_image_tasks, return_exceptions=True)
            for poi, img in zip(pois_to_update, images):
                if isinstance(img, str):
                    poi["image_url"] = img

        # Fetch images for meals
        meal_image_tasks = []
        meals_to_update = []
        for day in route_data.get("day_plans", []):
            for meal in day.get("meals", []):
                if meal.get("restaurant_name"):
                    meal_image_tasks.append(image_service.search_photo(meal["restaurant_name"]))
                    meals_to_update.append(meal)

        if meal_image_tasks:
            images = await asyncio.gather(*meal_image_tasks, return_exceptions=True)
            for meal, img in zip(meals_to_update, images):
                if isinstance(img, str):
                    meal["image_url"] = img

        # Generate Douyin links for all POIs, meals, stories
        douyin_links = []
        for day in route_data.get("day_plans", []):
            for poi in day.get("pois", []):
                if poi.get("name"):
                    city_name = ""
                    for seg in day.get("segments", []):
                        city_name = seg.get("to_name", "")
                        break
                    douyin_links.extend(
                        douyin_service.generate_douyin_links_for_poi(
                            poi["name"], city_name, poi.get("id", "")
                        )
                    )
            for meal in day.get("meals", []):
                if meal.get("restaurant_name"):
                    city_name = ""
                    for seg in day.get("segments", []):
                        city_name = seg.get("to_name", "")
                        break
                    douyin_links.extend(
                        douyin_service.generate_douyin_links_for_meal(
                            meal["restaurant_name"], meal.get("cuisine_type", ""), city_name
                        )
                    )

        for story in route_data.get("story_cards", []):
            if story.get("figure") or story.get("event"):
                douyin_links.extend(
                    douyin_service.generate_douyin_links_for_story(
                        story.get("figure", ""), story.get("event", ""),
                        story.get("related_city", "")
                    )
                )

        route_data["douyin_links"] = douyin_links

        # Calculate total cost
        scenic_count = sum(
            len([p for p in day.get("pois", []) if p.get("category") in ("scenic", "nature")])
            for day in route_data.get("day_plans", [])
        )
        cost_breakdown = cost_service.calculate_route_cost(
            total_distance=total_distance,
            days=days,
            adults=adults,
            children=children,
            vehicle_type=vehicle_type,
            scenic_count=scenic_count,
        )
        route_data["cost_breakdown"] = cost_breakdown

        yield await _emit("assembly", "done", "组装完成", 100)

        # ─── Final event: complete route data ──────────────────────────────
        final_data = json.dumps({"route": route_data, "error": ""}, ensure_ascii=False, default=str)
        yield f"data: {final_data}\n\n"

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        error_data = json.dumps({"route": None, "error": str(e)}, ensure_ascii=False)
        yield f"data: {error_data}\n\n"
