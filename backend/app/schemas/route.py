"""Pydantic models for request/response serialization.

Field naming is unified between frontend and backend (camelCase -> snake_case
mapping done via aliases). This fixes the selfdrivetrip field mismatch issue.
"""

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ─── POI ────────────────────────────────────────────────────────────────────


class POIBase(BaseModel):
    type: str = "scenic"
    category: str = "scenic"
    name: str = ""
    lat: float = 0.0
    lng: float = 0.0
    rating: float = 0.0
    price_level: str = ""
    image_url: str = ""
    description: str = ""
    source_url: str = ""
    booking_url: str = ""
    duration_minutes: int = 0
    sort_order: int = 0
    # Extended
    feature: str = ""
    anecdote: str = ""
    historical_figure: str = ""
    historical_event: str = ""


class POICreate(POIBase):
    segment_id: Optional[str] = None


class POIOut(POIBase):
    id: str
    day_plan_id: str
    segment_id: Optional[str] = None
    douyin_links: List["DouyinLinkOut"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ─── RouteSegment ───────────────────────────────────────────────────────────


class RouteSegmentBase(BaseModel):
    from_name: str = ""
    to_name: str = ""
    distance: float = 0.0
    duration: float = 0.0
    toll_cost: float = 0.0
    fuel_cost: float = 0.0
    polyline: List[List[float]] = Field(default_factory=list)
    sort_order: int = 0


class RouteSegmentCreate(RouteSegmentBase):
    pass


class RouteSegmentOut(RouteSegmentBase):
    id: str
    day_plan_id: str
    pois: List[POIOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ─── Meal ───────────────────────────────────────────────────────────────────


class MealBase(BaseModel):
    type: str = "lunch"
    restaurant_name: str = ""
    cuisine_type: str = ""
    cost_per_person: float = 0.0
    image_url: str = ""
    rating: float = 0.0
    recommendation: str = ""
    # Extended
    is_local_specialty: bool = False
    story: str = ""
    image_urls: List[str] = Field(default_factory=list)


class MealCreate(MealBase):
    pass


class MealOut(MealBase):
    id: str
    day_plan_id: str
    douyin_links: List["DouyinLinkOut"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ─── Hotel ──────────────────────────────────────────────────────────────────


class HotelBase(BaseModel):
    name: str = ""
    lat: float = 0.0
    lng: float = 0.0
    price_per_night: float = 0.0
    rating: float = 0.0
    image_url: str = ""
    booking_url: str = ""
    address: str = ""
    phone: str = ""


class HotelCreate(HotelBase):
    pass


class HotelOut(HotelBase):
    id: str
    day_plan_id: str

    model_config = ConfigDict(from_attributes=True)


# ─── DayPlan ────────────────────────────────────────────────────────────────


class DayPlanBase(BaseModel):
    day_number: int = 1
    date: str = ""
    theme: str = ""
    day_distance: float = 0.0
    day_duration: float = 0.0
    day_cost: float = 0.0
    # Extended
    weather_advisory: str = ""
    scenery_description: str = ""
    terrain_note: str = ""


class DayPlanCreate(DayPlanBase):
    segments: List[RouteSegmentCreate] = Field(default_factory=list)
    pois: List[POICreate] = Field(default_factory=list)
    meals: List[MealCreate] = Field(default_factory=list)
    hotels: List[HotelCreate] = Field(default_factory=list)


class DayPlanOut(DayPlanBase):
    id: str
    route_id: str
    segments: List[RouteSegmentOut] = Field(default_factory=list)
    pois: List[POIOut] = Field(default_factory=list)
    meals: List[MealOut] = Field(default_factory=list)
    hotels: List[HotelOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ─── WeatherForecast ────────────────────────────────────────────────────────


class WeatherForecastOut(BaseModel):
    id: str
    route_id: str
    city_name: str
    date: str
    temperature_high: float
    temperature_low: float
    weather_condition: str
    icon: str
    humidity: float
    wind_speed: float
    precipitation: float = 0.0

    model_config = ConfigDict(from_attributes=True)


# ─── StoryCard ──────────────────────────────────────────────────────────────


class StoryCardBase(BaseModel):
    related_city: str = ""
    day_number: int = 0
    figure: str = ""
    event: str = ""
    anecdote: str = ""
    story_text: str = ""
    image_url: str = ""


class StoryCardCreate(StoryCardBase):
    pass


class StoryCardOut(StoryCardBase):
    id: str
    route_id: str
    douyin_links: List["DouyinLinkOut"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ─── DouyinLink ─────────────────────────────────────────────────────────────


class DouyinLinkBase(BaseModel):
    related_type: str = "poi"  # poi / meal / story / city
    related_id: str = ""
    keyword: str = ""
    search_url: str = ""
    qr_code_data: str = ""
    label: str = ""


class DouyinLinkCreate(DouyinLinkBase):
    pass


class DouyinLinkOut(DouyinLinkBase):
    id: str
    route_id: str

    model_config = ConfigDict(from_attributes=True)


# ─── Route ──────────────────────────────────────────────────────────────────


class RouteBase(BaseModel):
    title: str = ""
    departure: str = ""
    destination: str = ""
    total_distance: float = 0.0
    total_duration: float = 0.0
    trip_type: str = "越野自驾"
    theme: str = "回归自然"
    vehicle_type: str = "SUV"
    terrain_difficulty: int = 2
    nature_score: int = 4
    adults: int = 2
    children: int = 0
    budget: float = 0.0
    status: str = "draft"
    overall_tips: str = ""


class RouteCreate(RouteBase):
    day_plans: List[DayPlanCreate] = Field(default_factory=list)
    story_cards: List[StoryCardCreate] = Field(default_factory=list)


class RouteListItem(BaseModel):
    id: str
    share_id: str
    title: str
    departure: str
    destination: str
    total_distance: float
    total_duration: float
    trip_type: str
    theme: str
    vehicle_type: str
    terrain_difficulty: int
    nature_score: int
    adults: int
    children: int
    budget: float
    status: str
    created_at: datetime
    view_count: int

    model_config = ConfigDict(from_attributes=True)


class RouteOut(RouteBase):
    id: str
    share_id: str
    created_at: datetime
    view_count: int
    day_plans: List[DayPlanOut] = Field(default_factory=list)
    weather_forecasts: List[WeatherForecastOut] = Field(default_factory=list)
    story_cards: List[StoryCardOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ─── Generation ─────────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    """Request to generate a route plan.

    Field names unified - frontend sends these exact names.
    """
    departure: str = Field(..., min_length=2, max_length=50)
    destination: str = Field(..., min_length=2, max_length=50)
    start_date: str = ""  # e.g. "2026-07-08"
    days: int = Field(default=3, ge=1, le=30)
    trip_type: str = "越野自驾"
    adults: int = Field(default=2, ge=1, le=20)
    children: int = Field(default=0, ge=0, le=10)
    vehicle_type: str = "SUV"
    budget: float = Field(default=8000.0, ge=0, le=1000000)
    theme: str = "回归自然"
    preferences: List[str] = Field(default_factory=list)  # 自然风光/人文历史/美食/越野探险
    session_id: str = ""

    @field_validator("departure", "destination")
    @classmethod
    def sanitize_city(cls, v: str) -> str:
        import re
        v = re.sub(r"[^\u4e00-\u9fa5a-zA-Z\s]", "", v.strip())
        if not v:
            raise ValueError("城市名不能为空")
        return v


class GenerateResponse(BaseModel):
    success: bool
    message: str = ""
    route: Optional[RouteOut] = None


# ─── SSE Events ─────────────────────────────────────────────────────────────


class SSEStageEvent(BaseModel):
    """SSE event for agent pipeline progress."""
    stage: str  # geocode / weather / planning / routing / enrichment / assembly
    status: str  # running / done / error
    message: str = ""
    progress: int = 0  # 0-100


class SSECompleteEvent(BaseModel):
    """SSE event with the final route data."""
    route: Optional[RouteOut] = None
    error: str = ""


# ─── SavedSearch ────────────────────────────────────────────────────────────


class SavedSearchCreate(BaseModel):
    session_id: str = ""
    departure_city: str
    destination_city: str
    start_date: str = ""
    days: int = 3
    trip_type: str = "越野自驾"
    adults: int = 2
    children: int = 0
    vehicle_type: str = "SUV"
    budget: float = 0.0
    theme: str = ""


class SavedSearchOut(BaseModel):
    id: str
    session_id: str
    departure_city: str
    destination_city: str
    start_date: str
    days: int
    trip_type: str
    adults: int
    children: int
    vehicle_type: str
    budget: float
    theme: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Generic ────────────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "OffroadTrip"
    version: str = "1.0.0"


# Resolve forward references
POIOut.model_rebuild()
MealOut.model_rebuild()
StoryCardOut.model_rebuild()
RouteOut.model_rebuild()
