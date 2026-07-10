"""Generate router - SSE streaming endpoint for the agent pipeline."""

import json
import secrets
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.schemas.route import GenerateRequest, RouteCreate, DayPlanCreate, RouteSegmentCreate
from app.models.route import Route, DayPlan, RouteSegment, POI, Meal, Hotel, StoryCard, DouyinLink, WeatherForecast
from app.agents.orchestrator import generate_route_stream

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate")
async def generate_route(req: GenerateRequest):
    """Generate a route plan via the 6-stage agent pipeline.

    Returns an SSE stream: progress events + final route data.
    The final route is also saved to the database.
    """

    async def event_stream():
        async for sse_event in generate_route_stream(
            departure=req.departure,
            destination=req.destination,
            start_date=req.start_date,
            days=req.days,
            trip_type=req.trip_type,
            vehicle_type=req.vehicle_type,
            adults=req.adults,
            children=req.children,
            budget=req.budget,
            theme=req.theme,
            preferences=req.preferences,
        ):
            # Intercept the final route event: persist to DB and inject the
            # generated id BEFORE forwarding to the client, so the frontend
            # receives a route it can later refetch / share by id.
            if sse_event.startswith("data: ") and '"route"' in sse_event:
                try:
                    payload = json.loads(sse_event[6:].strip())
                except json.JSONDecodeError:
                    yield sse_event
                    continue

                route_data = payload.get("route")
                if route_data:
                    db = SessionLocal()
                    try:
                        route_id = _save_route_to_db(db, route_data)
                        route_data["id"] = route_id
                    except Exception as e:
                        logger.error(f"Failed to save route to DB: {e}")
                    finally:
                        db.close()
                    payload["route"] = route_data
                    yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
                else:
                    yield sse_event
            else:
                yield sse_event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _save_route_to_db(db: Session, route_data: dict):
    """Persist the generated route to the database."""
    share_id = secrets.token_hex(8)

    route = Route(
        share_id=share_id,
        title=route_data.get("title", ""),
        departure=route_data.get("departure", ""),
        destination=route_data.get("destination", ""),
        total_distance=route_data.get("total_distance", 0),
        total_duration=route_data.get("total_duration", 0),
        trip_type=route_data.get("trip_type", "越野自驾"),
        theme=route_data.get("theme", "回归自然"),
        vehicle_type=route_data.get("vehicle_type", "SUV"),
        terrain_difficulty=route_data.get("terrain_difficulty", 2),
        nature_score=route_data.get("nature_score", 4),
        adults=route_data.get("adults", 2),
        children=route_data.get("children", 0),
        budget=route_data.get("budget", 0),
        status="draft",
        overall_tips=route_data.get("overall_tips", ""),
    )
    db.add(route)
    db.flush()  # get route.id

    # Save day plans
    for day_data in route_data.get("day_plans", []):
        day_plan = DayPlan(
            route_id=route.id,
            day_number=day_data.get("day_number", 1),
            date=day_data.get("date", ""),
            theme=day_data.get("theme", ""),
            day_distance=day_data.get("day_distance", 0),
            day_duration=day_data.get("day_duration", 0),
            day_cost=day_data.get("day_cost", 0),
            weather_advisory=day_data.get("weather_advisory", ""),
            scenery_description=day_data.get("scenery_description", ""),
            terrain_note=day_data.get("terrain_note", ""),
        )
        db.add(day_plan)
        db.flush()

        # Save segments
        for seg_data in day_data.get("segments", []):
            seg = RouteSegment(
                day_plan_id=day_plan.id,
                from_name=seg_data.get("from_name", ""),
                to_name=seg_data.get("to_name", ""),
                distance=seg_data.get("distance", 0),
                duration=seg_data.get("duration", 0),
                toll_cost=seg_data.get("toll_cost", 0),
                fuel_cost=seg_data.get("fuel_cost", 0),
                polyline=seg_data.get("polyline", []),
                sort_order=seg_data.get("sort_order", 0),
            )
            db.add(seg)

        # Save POIs (per-day, not per-segment)
        for poi_data in day_data.get("pois", []):
            poi = POI(
                day_plan_id=day_plan.id,
                segment_id=None,
                type=poi_data.get("type", "scenic"),
                category=poi_data.get("category", "scenic"),
                name=poi_data.get("name", ""),
                lat=poi_data.get("lat", 0),
                lng=poi_data.get("lng", 0),
                rating=poi_data.get("rating", 0),
                price_level=poi_data.get("price_level", ""),
                image_url=poi_data.get("image_url", ""),
                description=poi_data.get("description", ""),
                duration_minutes=poi_data.get("duration_minutes", 0),
                sort_order=poi_data.get("sort_order", 0),
                feature=poi_data.get("feature", ""),
                anecdote=poi_data.get("anecdote", ""),
                historical_figure=poi_data.get("historical_figure", ""),
                historical_event=poi_data.get("historical_event", ""),
            )
            db.add(poi)

        # Save meals
        for meal_data in day_data.get("meals", []):
            meal = Meal(
                day_plan_id=day_plan.id,
                type=meal_data.get("type", "lunch"),
                restaurant_name=meal_data.get("restaurant_name", ""),
                cuisine_type=meal_data.get("cuisine_type", ""),
                cost_per_person=meal_data.get("cost_per_person", 0),
                image_url=meal_data.get("image_url", ""),
                rating=meal_data.get("rating", 0),
                recommendation=meal_data.get("recommendation", ""),
                is_local_specialty=meal_data.get("is_local_specialty", False),
                story=meal_data.get("story", ""),
                image_urls=meal_data.get("image_urls", []),
            )
            db.add(meal)

        # Save hotels
        for hotel_data in day_data.get("hotels", []):
            hotel = Hotel(
                day_plan_id=day_plan.id,
                name=hotel_data.get("name", ""),
                lat=hotel_data.get("lat", 0),
                lng=hotel_data.get("lng", 0),
                price_per_night=hotel_data.get("price_per_night", 0),
                rating=hotel_data.get("rating", 0),
                image_url=hotel_data.get("image_url", ""),
                address=hotel_data.get("address", ""),
                phone=hotel_data.get("phone", ""),
            )
            db.add(hotel)

    # Save story cards
    for story_data in route_data.get("story_cards", []):
        story = StoryCard(
            route_id=route.id,
            related_city=story_data.get("related_city", ""),
            figure=story_data.get("figure", ""),
            event=story_data.get("event", ""),
            anecdote=story_data.get("anecdote", ""),
            story_text=story_data.get("story_text", ""),
            image_url=story_data.get("image_url", ""),
        )
        db.add(story)

    # Save douyin links
    for dl_data in route_data.get("douyin_links", []):
        dl = DouyinLink(
            route_id=route.id,
            related_type=dl_data.get("related_type", "poi"),
            related_id=dl_data.get("related_id", ""),
            keyword=dl_data.get("keyword", ""),
            search_url=dl_data.get("search_url", ""),
            qr_code_data=dl_data.get("qr_code_data", ""),
            label=dl_data.get("label", ""),
        )
        db.add(dl)

    # Save weather forecasts
    weather_map = route_data.get("_weather_map", {})
    for city, forecasts in weather_map.items():
        for f in forecasts:
            wf = WeatherForecast(
                route_id=route.id,
                city_name=city,
                date=f.get("date", ""),
                temperature_high=f.get("temperature_high", 0),
                temperature_low=f.get("temperature_low", 0),
                weather_condition=f.get("weather_condition", ""),
                icon=f.get("icon", ""),
                humidity=f.get("humidity", 0),
                wind_speed=f.get("wind_speed", 0),
                precipitation=f.get("precipitation", 0),
            )
            db.add(wf)

    db.commit()
    # Expose persisted identifiers back through the route dict so the SSE final
    # event can carry them to the frontend (enables refetch + share by id).
    route_data["id"] = route.id
    route_data["share_id"] = share_id
    logger.info(f"Route saved: {route.id} (share_id: {share_id})")
    return route.id
