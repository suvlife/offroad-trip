"""Image service - fetches real photos from Unsplash for scenic spots and food.

Falls back to placeholder images if Unsplash key is not configured.
"""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

UNSPLASH_BASE = "https://api.unsplash.com"
PLACEHOLDER = "https://picsum.photos/seed/{seed}/800/600"


async def search_photo(query: str, seed: str = "") -> str:
    """Search for a photo on Unsplash by keyword.

    Returns the image URL, or a placeholder if Unsplash is not configured / fails.
    """
    api_key = settings.UNSPLASH_ACCESS_KEY

    if not api_key:
        return PLACEHOLDER.format(seed=seed or query)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{UNSPLASH_BASE}/search/photos",
                params={
                    "query": query,
                    "per_page": 1,
                    "orientation": "landscape",
                },
                headers={"Authorization": f"Client-ID {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if results:
            return results[0]["urls"]["regular"]
    except Exception as e:
        logger.error(f"Unsplash search failed for '{query}': {e}")

    return PLACEHOLDER.format(seed=seed or query)


async def search_photos(query: str, count: int = 3) -> list[str]:
    """Search for multiple photos on Unsplash."""
    api_key = settings.UNSPLASH_ACCESS_KEY

    if not api_key:
        return [PLACEHOLDER.format(seed=f"{query}{i}") for i in range(count)]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{UNSPLASH_BASE}/search/photos",
                params={
                    "query": query,
                    "per_page": min(count, 10),
                    "orientation": "landscape",
                },
                headers={"Authorization": f"Client-ID {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        return [r["urls"]["regular"] for r in results[:count]] or [
            PLACEHOLDER.format(seed=f"{query}{i}") for i in range(count)
        ]
    except Exception as e:
        logger.error(f"Unsplash multi-search failed for '{query}': {e}")
        return [PLACEHOLDER.format(seed=f"{query}{i}") for i in range(count)]
