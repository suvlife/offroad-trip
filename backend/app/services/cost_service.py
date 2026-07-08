"""Cost calculation engine.

Migrated from selfdrivetrip, adapted for off-road vehicles.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Vehicle fuel consumption (L/100km)
FUEL_CONSUMPTION = {
    "轿车": 7.0,
    "中型轿车": 7.5,
    "SUV": 9.0,
    "越野车": 12.0,
    "新能源": 15.0,  # kWh/100km equivalent
    "混动": 6.0,
}

# Fuel price (yuan/L) - rough average, should be configurable
FUEL_PRICE = 8.0  # 92# gasoline
ELECTRICITY_PRICE = 1.0  # yuan/kWh

# Highway toll rate (yuan/km)
TOLL_RATE = 0.45

# Average costs
HOTEL_PER_NIGHT = 350  # yuan
MEAL_PER_PERSON = 80  # yuan per meal
SCENIC_TICKET = 80  # yuan per scenic spot


def calculate_segment_cost(
    distance_km: float,
    vehicle_type: str = "SUV",
    has_toll: bool = True,
    toll_from_api: float = 0,
) -> Dict[str, float]:
    """Calculate the driving cost for a single segment.

    Returns: {"fuel_cost": float, "toll_cost": float, "total": float}
    """
    consumption = FUEL_CONSUMPTION.get(vehicle_type, FUEL_CONSUMPTION["SUV"])

    # Fuel cost
    if vehicle_type in ("新能源",):
        fuel_cost = distance_km * consumption / 100 * ELECTRICITY_PRICE
    else:
        fuel_cost = distance_km * consumption / 100 * FUEL_PRICE

    # Toll cost - use API value if available, otherwise estimate
    if toll_from_api > 0:
        toll_cost = toll_from_api
    elif has_toll:
        toll_cost = distance_km * TOLL_RATE
    else:
        toll_cost = 0

    return {
        "fuel_cost": round(fuel_cost, 1),
        "toll_cost": round(toll_cost, 1),
        "total": round(fuel_cost + toll_cost, 1),
    }


def calculate_route_cost(
    total_distance: float,
    days: int,
    adults: int,
    children: int,
    vehicle_type: str = "SUV",
    scenic_count: int = 0,
    hotel_count: int = 0,
    has_toll: bool = True,
) -> Dict[str, Any]:
    """Calculate the total cost breakdown for a route.

    Returns: {"fuel": float, "toll": float, "hotel": float, "meal": float,
              "ticket": float, "total": float, "breakdown": dict}
    """
    people = adults + children

    # Driving cost
    driving = calculate_segment_cost(total_distance, vehicle_type, has_toll)

    # Hotel cost
    hotel_nights = hotel_count or max(days - 1, 0)
    hotel_cost = hotel_nights * HOTEL_PER_NIGHT

    # Meal cost (3 meals per day per person, children half)
    meal_cost = days * 3 * (adults + children * 0.5) * MEAL_PER_PERSON

    # Scenic tickets
    ticket_cost = scenic_count * people * SCENIC_TICKET

    total = driving["fuel_cost"] + driving["toll_cost"] + hotel_cost + meal_cost + ticket_cost

    return {
        "fuel": driving["fuel_cost"],
        "toll": driving["toll_cost"],
        "hotel": round(hotel_cost, 1),
        "meal": round(meal_cost, 1),
        "ticket": round(ticket_cost, 1),
        "total": round(total, 1),
        "breakdown": {
            "油费": f"¥{driving['fuel_cost']:.0f}",
            "过路费": f"¥{driving['toll_cost']:.0f}",
            "住宿": f"¥{hotel_cost:.0f}",
            "餐饮": f"¥{meal_cost:.0f}",
            "门票": f"¥{ticket_cost:.0f}",
            "总计": f"¥{total:.0f}",
        },
    }
