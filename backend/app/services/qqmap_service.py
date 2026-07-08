"""Tencent Maps (腾讯位置服务) WebService client.

API docs: https://lbs.qq.com/service/webService/webServiceGuide/webServiceOverview
Coordinate system: GCJ-02, format: lat,lng (latitude first)
Polyline compression: forward-difference / 1e6

Used for:
  - Geocoding (address -> coordinates)
  - Driving direction (route planning with up to 30 waypoints)
  - POI search (scenic spots, restaurants, hotels, gas stations)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://apis.map.qq.com"


def _key() -> str:
    """Get the Tencent Maps API key, warn if missing."""
    key = settings.QQ_MAP_KEY
    if not key:
        logger.warning("QQ_MAP_KEY not configured - Tencent Maps API will return mock data")
    return key


def decode_polyline(coors: List[float]) -> List[Tuple[float, float]]:
    """Decode Tencent Maps compressed polyline.

    The polyline array uses forward-difference compression:
      [lat1, lng1, dlat2, dlng2, dlat3, dlng3, ...]
    First point is absolute, subsequent points are relative offsets * 1e6.

    Returns: list of (lat, lng) tuples
    """
    if not coors or len(coors) < 2:
        return []

    coors = list(coors)  # don't mutate input
    for i in range(2, len(coors)):
        coors[i] = coors[i - 2] + coors[i] / 1000000.0

    return [(coors[i], coors[i + 1]) for i in range(0, len(coors), 2)]


def to_polyline_pairs(coors: List[float]) -> List[List[float]]:
    """Decode and return as [[lat, lng], ...] for JSON storage."""
    return [[lat, lng] for lat, lng in decode_polyline(coors)]


async def geocode(address: str) -> Optional[Dict[str, Any]]:
    """Geocode an address to coordinates.

    Returns: {"lat": float, "lng": float, "city": str, "province": str, "adcode": str}
    or None on failure.
    """
    key = _key()
    if not key:
        return None  # signal failure so callers can handle gracefully

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BASE_URL}/ws/geocoder/v1/",
                params={"address": address, "key": key},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != 0:
            logger.error(f"Tencent geocode error: {data.get('message')}")
            return None

        result = data["result"]
        loc = result["location"]
        components = result.get("address_components", {})
        ad_info = result.get("ad_info", {})

        return {
            "lat": loc["lat"],
            "lng": loc["lng"],
            "city": components.get("city", "") or address,
            "province": components.get("province", ""),
            "adcode": ad_info.get("adcode", ""),
        }
    except Exception as e:
        logger.error(f"Geocode failed for '{address}': {e}")
        return None


async def reverse_geocode(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Reverse geocode coordinates to address."""
    key = _key()
    if not key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BASE_URL}/ws/geocoder/v1/",
                params={"location": f"{lat},{lng}", "key": key},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != 0:
            return None

        result = data["result"]
        return {
            "address": result.get("address", ""),
            "city": result.get("address_component", {}).get("city", ""),
            "province": result.get("address_component", {}).get("province", ""),
        }
    except Exception as e:
        logger.error(f"Reverse geocode failed: {e}")
        return None


async def plan_driving_route(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
    waypoints: Optional[List[Tuple[float, float]]] = None,
    policy: str = "LEAST_TIME",
    avoid_highway: bool = False,
) -> Optional[Dict[str, Any]]:
    """Plan a driving route between two points.

    Args:
        from_lat, from_lng: start coordinates
        to_lat, to_lng: end coordinates
        waypoints: optional list of (lat, lng) tuples (max 30)
        policy: LEAST_TIME / LEAST_FEE / HIGHWAY_FIRST / AVOID_HIGHWAY etc.
        avoid_highway: if True, add AVOID_HIGHWAY to policy

    Returns: {"distance": km, "duration": hours, "toll": yuan, "polyline": [[lat,lng],...]}
    or None on failure.
    """
    key = _key()
    if not key:
        # Mock: rough estimate
        import math
        dist = math.hypot(to_lat - from_lat, to_lng - from_lng) * 111  # ~km
        return {
            "distance": round(dist, 1),
            "duration": round(dist / 80, 1),  # assume 80km/h
            "toll": round(dist * 0.5),
            "polyline": [[from_lat, from_lng], [to_lat, to_lng]],
        }

    policy_str = policy
    if avoid_highway:
        policy_str = f"{policy},AVOID_HIGHWAY"

    params = {
        "from": f"{from_lat},{from_lng}",
        "to": f"{to_lat},{to_lng}",
        "key": key,
        "policy": policy_str,
    }

    if waypoints:
        # Format: lat1,lng1;lat2,lng2;...
        wp_str = ";".join(f"{lat},{lng}" for lat, lng in waypoints)
        params["waypoints"] = wp_str

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}/ws/direction/v1/driving/",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != 0:
            logger.error(f"Tencent direction error: {data.get('message')}")
            return None

        routes = data["result"]["routes"]
        if not routes:
            return None

        route = routes[0]  # take the best route
        polyline = to_polyline_pairs(route.get("polyline", []))

        return {
            "distance": round(route["distance"] / 1000, 1),  # m -> km
            "duration": round(route["duration"] / 3600, 1),  # s -> hours
            "toll": route.get("toll", 0),
            "polyline": polyline,
        }
    except Exception as e:
        logger.error(f"Driving route planning failed: {e}")
        return None


async def search_pois(
    keyword: str,
    city: str = "",
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius: int = 10000,
    page_size: int = 10,
    category: str = "",
) -> List[Dict[str, Any]]:
    """Search for POIs (points of interest).

    Uses nearby search if lat/lng provided, otherwise city region search.

    Returns: list of {"id", "title", "address", "tel", "category", "lat", "lng", "distance"}
    """
    key = _key()
    if not key:
        return []

    # Build boundary
    if lat is not None and lng is not None:
        boundary = f"nearby({lat},{lng},{radius})"
    elif city:
        boundary = f"region({city})"
    else:
        boundary = f"region(全国)"

    params = {
        "key": key,
        "keyword": keyword,
        "boundary": boundary,
        "page_size": min(page_size, 20),
        "output": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BASE_URL}/ws/place/v1/search",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != 0:
            logger.error(f"POI search error: {data.get('message')}")
            return []

        results = []
        for item in data.get("data", []):
            loc = item.get("location", {})
            results.append({
                "id": item.get("id", ""),
                "name": item.get("title", ""),
                "address": item.get("address", ""),
                "tel": item.get("tel", ""),
                "category": item.get("category", ""),
                "lat": loc.get("lat", 0.0),
                "lng": loc.get("lng", 0.0),
                "distance": item.get("_distance", 0),
            })
        return results
    except Exception as e:
        logger.error(f"POI search failed for '{keyword}': {e}")
        return []


async def search_city_pois(
    keyword: str,
    city: str,
    poi_type: str = "scenic",
    page_size: int = 10,
) -> List[Dict[str, Any]]:
    """Search for POIs of a specific type within a city.

    poi_type: scenic / restaurant / hotel / gas_station
    """
    keyword_map = {
        "scenic": "景点 景区 公园",
        "restaurant": "美食 餐厅 特色菜",
        "hotel": "酒店 住宿",
        "gas_station": "加油站",
        "viewpoint": "观景台 瞭望台",
    }
    search_keyword = keyword_map.get(poi_type, keyword)
    return await search_pois(search_keyword, city=city, page_size=page_size)
