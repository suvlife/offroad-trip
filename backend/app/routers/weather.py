"""Weather router - standalone weather query."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import weather_service

router = APIRouter()


@router.get("/weather")
async def get_weather(city: str, days: int = 7):
    """Get weather forecast for a city."""
    return await weather_service.get_weather(city, days)


@router.get("/cities")
async def search_cities(q: str):
    """City search (autocomplete) via Tencent Maps geocoding."""
    from app.services import qqmap_service

    result = await qqmap_service.geocode(q)
    if result:
        return [{"name": result["city"], "lat": result["lat"], "lng": result["lng"]}]
    return []
