"""Douyin (TikTok) search link service.

Douyin has no public search API, so we generate search keywords + deep links.
Users tap to jump to Douyin app/web search.
"""

import logging
import urllib.parse
from typing import Dict, List

logger = logging.getLogger(__name__)

# Douyin search URLs
DOUYIN_WEB_SEARCH = "https://www.douyin.com/search/"
DOUYIN_DEEP_LINK = "snssdk1128://search/result?keyword="  # app deep link


def generate_douyin_link(
    keyword: str,
    label: str = "看抖音视频",
    related_type: str = "poi",
    related_id: str = "",
) -> Dict:
    """Generate a Douyin search link for a keyword.

    Args:
        keyword: the search term (e.g. "承德避暑山庄" or "东北铁锅炖")
        label: display label for the button
        related_type: poi / meal / story / city
        related_id: ID of the related entity

    Returns: {"keyword", "search_url", "qr_code_data", "label", "related_type", "related_id"}
    """
    encoded = urllib.parse.quote(keyword)
    search_url = f"{DOUYIN_WEB_SEARCH}{encoded}"
    qr_data = f"{DOUYIN_DEEP_LINK}{encoded}"

    return {
        "keyword": keyword,
        "search_url": search_url,
        "qr_code_data": qr_data,
        "label": label,
        "related_type": related_type,
        "related_id": related_id,
    }


def generate_douyin_links_for_poi(poi_name: str, poi_city: str = "", poi_id: str = "") -> List[Dict]:
    """Generate multiple Douyin search links for a POI.

    Creates links for: the scenic spot itself, food nearby, travel tips.
    """
    links = []

    # Main: the scenic spot
    links.append(generate_douyin_link(
        keyword=poi_name,
        label=f"看{poi_name}视频",
        related_type="poi",
        related_id=poi_id,
    ))

    # Travel tips / guide
    links.append(generate_douyin_link(
        keyword=f"{poi_name}攻略",
        label="游玩攻略",
        related_type="poi",
        related_id=poi_id,
    ))

    # Nearby food if city is known
    if poi_city:
        links.append(generate_douyin_link(
            keyword=f"{poi_city}美食",
            label=f"{poi_city}美食",
            related_type="city",
            related_id=poi_id,
        ))

    return links


def generate_douyin_links_for_meal(
    dish_name: str,
    restaurant_name: str = "",
    city: str = "",
    meal_id: str = "",
) -> List[Dict]:
    """Generate Douyin search links for a meal/food."""
    links = []

    # The dish
    links.append(generate_douyin_link(
        keyword=dish_name,
        label=f"看{dish_name}视频",
        related_type="meal",
        related_id=meal_id,
    ))

    # The restaurant
    if restaurant_name:
        links.append(generate_douyin_link(
            keyword=restaurant_name,
            label="餐厅探店",
            related_type="meal",
            related_id=meal_id,
        ))

    # City food
    if city:
        links.append(generate_douyin_link(
            keyword=f"{city}特色美食",
            label=f"{city}特色菜",
            related_type="city",
            related_id=meal_id,
        ))

    return links


def generate_douyin_links_for_story(
    figure: str = "",
    event: str = "",
    city: str = "",
    story_id: str = "",
) -> List[Dict]:
    """Generate Douyin search links for a history story card."""
    links = []

    if figure:
        links.append(generate_douyin_link(
            keyword=figure,
            label=f"了解{figure}",
            related_type="story",
            related_id=story_id,
        ))

    if event:
        links.append(generate_douyin_link(
            keyword=event,
            label=f"看{event}视频",
            related_type="story",
            related_id=story_id,
        ))

    return links
