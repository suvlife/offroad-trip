"""Tests for content enrichment agent grouping (regression for duplicate-city bug).

Previously enrich_all_cities grouped POIs by every segment endpoint, so a POI on
a multi-segment day (A->B->C) was enriched once per endpoint city — wasteful LLM
calls and concurrent mutation of the same dict. These tests pin the fix: each
POI/meal is enriched exactly once, and history stories carry a day_number.
"""

import asyncio
from collections import Counter

import pytest

from app.agents import content_agents


@pytest.fixture
def multi_segment_route():
    """A single day with 3 segments (A->B->C->D) and 2 POIs / 1 meal."""
    return {
        "destination": "D城",
        "day_plans": [
            {
                "day_number": 1,
                "theme": "山野穿越",
                "segments": [
                    {"from_name": "A城", "to_name": "B城", "sort_order": 0},
                    {"from_name": "B城", "to_name": "C城", "sort_order": 1},
                    {"from_name": "C城", "to_name": "D城", "sort_order": 2},
                ],
                "pois": [
                    {"name": "景点1", "description": "d1"},
                    {"name": "景点2", "description": "d2"},
                ],
                "meals": [
                    {"restaurant_name": "餐厅1", "cuisine_type": "东北菜"},
                ],
            }
        ],
    }


def test_each_poi_enriched_exactly_once(monkeypatch, multi_segment_route):
    """On a 3-segment day, each POI list must be passed to enrich_scenic once."""
    scenic_calls = []
    food_calls = []
    history_calls = []

    async def fake_scenic(city, pois):
        scenic_calls.append((city, tuple(p["name"] for p in pois)))
        return pois

    async def fake_food(city, meals):
        food_calls.append((city, tuple(m["restaurant_name"] for m in meals)))
        return meals

    async def fake_history(city, scenic_names):
        history_calls.append((city, tuple(scenic_names)))
        return [{"figure": "某人", "story_text": "..."}]

    monkeypatch.setattr(content_agents, "enrich_scenic", fake_scenic)
    monkeypatch.setattr(content_agents, "enrich_food", fake_food)
    monkeypatch.setattr(content_agents, "enrich_history", fake_history)

    result = asyncio.run(content_agents.enrich_all_cities(multi_segment_route))

    # Exactly one scenic / food / history call for the single day (not 3-4).
    assert len(scenic_calls) == 1
    assert len(food_calls) == 1
    assert len(history_calls) == 1

    # POIs enriched exactly once each — no name appears more than once total.
    all_enriched_names = Counter(
        name for _, names in scenic_calls for name in names
    )
    assert all_enriched_names == Counter({"景点1": 1, "景点2": 1})

    # City context is the day's destination (last segment's to_name).
    assert scenic_calls[0][0] == "D城"

    # History stories get the day_number stamped.
    assert result["story_cards"]
    assert all(s.get("day_number") == 1 for s in result["story_cards"])


def test_day_with_no_segments_falls_back_to_theme(monkeypatch):
    """A day without segments should still enrich, using theme/destination."""
    seen_cities = []

    async def fake_scenic(city, pois):
        seen_cities.append(city)
        return pois

    async def fake_food(city, meals):
        return meals

    async def fake_history(city, scenic_names):
        return []

    monkeypatch.setattr(content_agents, "enrich_scenic", fake_scenic)
    monkeypatch.setattr(content_agents, "enrich_food", fake_food)
    monkeypatch.setattr(content_agents, "enrich_history", fake_history)

    route = {
        "destination": "终点城",
        "day_plans": [
            {"day_number": 1, "theme": "主题城", "segments": [],
             "pois": [{"name": "p1"}], "meals": []}
        ],
    }
    asyncio.run(content_agents.enrich_all_cities(route))
    # Falls back to theme when no segment city is available.
    assert seen_cities == ["主题城"]
