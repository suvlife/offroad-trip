"""Routes CRUD + share router."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.route import Route, DayPlan, RouteSegment, POI, Meal, Hotel, StoryCard, DouyinLink, WeatherForecast
from app.schemas.route import RouteListItem, RouteOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/routes", response_model=List[RouteListItem])
async def list_routes(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """List all routes."""
    offset = (page - 1) * page_size
    routes = (
        db.query(Route)
        .order_by(Route.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return routes


@router.get("/routes/{route_id}", response_model=RouteOut)
async def get_route(route_id: str, db: Session = Depends(get_db)):
    """Get a route by ID with all related data."""
    route = _load_route_with_relations(db, Route.id == route_id)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")

    # Increment view count
    route.view_count = (route.view_count or 0) + 1
    db.commit()

    return _build_route_out(route)


@router.post("/routes/{route_id}/share")
async def share_route(route_id: str, db: Session = Depends(get_db)):
    """Publish a route and return its share ID."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")

    route.status = "published"
    db.commit()

    return {"share_id": route.share_id, "url": f"/share/{route.share_id}"}


@router.delete("/routes/{route_id}")
async def delete_route(route_id: str, db: Session = Depends(get_db)):
    """Delete a route and all its related data."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")

    db.delete(route)
    db.commit()
    return {"success": True}


@router.get("/share/{share_id}", response_model=RouteOut)
async def get_share(share_id: str, db: Session = Depends(get_db)):
    """Get route by share ID (public, read-only)."""
    route = _load_route_with_relations(db, Route.share_id == share_id)
    if not route:
        raise HTTPException(status_code=404, detail="分享链接无效")

    return _build_route_out(route)


def _load_route_with_relations(db: Session, *filters):
    """Load a route with all nested relationships in a single query."""
    return (
        db.query(Route)
        .options(
            selectinload(Route.day_plans)
                .selectinload(DayPlan.segments),
            selectinload(Route.day_plans)
                .selectinload(DayPlan.pois),
            selectinload(Route.day_plans)
                .selectinload(DayPlan.meals),
            selectinload(Route.day_plans)
                .selectinload(DayPlan.hotels),
            selectinload(Route.story_cards),
            selectinload(Route.weather_forecasts),
        )
        .filter(*filters)
        .first()
    )


def _build_route_out(route: Route) -> dict:
    """Build the full RouteOut dict from an eagerly-loaded route."""
    result = {
        "id": route.id,
        "share_id": route.share_id,
        "title": route.title,
        "departure": route.departure,
        "destination": route.destination,
        "total_distance": route.total_distance,
        "total_duration": route.total_duration,
        "trip_type": route.trip_type,
        "theme": route.theme,
        "vehicle_type": route.vehicle_type,
        "terrain_difficulty": route.terrain_difficulty,
        "nature_score": route.nature_score,
        "adults": route.adults,
        "children": route.children,
        "budget": route.budget,
        "status": route.status,
        "overall_tips": route.overall_tips,
        "created_at": route.created_at,
        "view_count": route.view_count,
        "day_plans": [],
        "weather_forecasts": [],
        "story_cards": [],
    }

    for dp in route.day_plans:
        day_out = {
            "id": dp.id,
            "route_id": dp.route_id,
            "day_number": dp.day_number,
            "date": dp.date,
            "theme": dp.theme,
            "day_distance": dp.day_distance,
            "day_duration": dp.day_duration,
            "day_cost": dp.day_cost,
            "weather_advisory": dp.weather_advisory,
            "scenery_description": dp.scenery_description,
            "terrain_note": dp.terrain_note,
            "segments": [],
            "pois": [],
            "meals": [],
            "hotels": [],
        }

        # Segments with their POIs
        for seg in dp.segments:
            day_out["segments"].append({
                "id": seg.id,
                "day_plan_id": seg.day_plan_id,
                "from_name": seg.from_name,
                "to_name": seg.to_name,
                "distance": seg.distance,
                "duration": seg.duration,
                "toll_cost": seg.toll_cost,
                "fuel_cost": seg.fuel_cost,
                "polyline": seg.polyline or [],
                "sort_order": seg.sort_order,
                "pois": [_poi_to_dict(p) for p in seg.pois],
            })

        # Day-level POIs (no segment assigned)
        for poi in dp.pois:
            if not poi.segment_id:
                day_out["pois"].append(_poi_to_dict(poi))

        for meal in dp.meals:
            day_out["meals"].append({
                "id": meal.id,
                "day_plan_id": meal.day_plan_id,
                "type": meal.type,
                "restaurant_name": meal.restaurant_name,
                "cuisine_type": meal.cuisine_type,
                "cost_per_person": meal.cost_per_person,
                "image_url": meal.image_url,
                "rating": meal.rating,
                "recommendation": meal.recommendation,
                "is_local_specialty": meal.is_local_specialty,
                "story": meal.story,
                "image_urls": meal.image_urls or [],
            })

        for hotel in dp.hotels:
            day_out["hotels"].append({
                "id": hotel.id,
                "day_plan_id": hotel.day_plan_id,
                "name": hotel.name,
                "lat": hotel.lat,
                "lng": hotel.lng,
                "price_per_night": hotel.price_per_night,
                "rating": hotel.rating,
                "image_url": hotel.image_url,
                "booking_url": hotel.booking_url,
                "address": hotel.address,
                "phone": hotel.phone,
            })

        result["day_plans"].append(day_out)

    for s in route.story_cards:
        result["story_cards"].append({
            "id": s.id,
            "route_id": s.route_id,
            "related_city": s.related_city,
            "day_number": s.day_number,
            "figure": s.figure,
            "event": s.event,
            "anecdote": s.anecdote,
            "story_text": s.story_text,
            "image_url": s.image_url,
        })

    for f in route.weather_forecasts:
        result["weather_forecasts"].append({
            "id": f.id,
            "route_id": f.route_id,
            "city_name": f.city_name,
            "date": f.date,
            "temperature_high": f.temperature_high,
            "temperature_low": f.temperature_low,
            "weather_condition": f.weather_condition,
            "icon": f.icon,
            "humidity": f.humidity,
            "wind_speed": f.wind_speed,
            "precipitation": f.precipitation,
        })

    return result


def _poi_to_dict(poi: POI) -> dict:
    return {
        "id": poi.id,
        "day_plan_id": poi.day_plan_id,
        "segment_id": poi.segment_id,
        "type": poi.type,
        "category": poi.category,
        "name": poi.name,
        "lat": poi.lat,
        "lng": poi.lng,
        "rating": poi.rating,
        "price_level": poi.price_level,
        "image_url": poi.image_url,
        "description": poi.description,
        "source_url": poi.source_url,
        "booking_url": poi.booking_url,
        "duration_minutes": poi.duration_minutes,
        "sort_order": poi.sort_order,
        "feature": poi.feature,
        "anecdote": poi.anecdote,
        "historical_figure": poi.historical_figure,
        "historical_event": poi.historical_event,
    }
