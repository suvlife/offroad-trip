/**
 * Douyin (TikTok) search-link service. No public API — we generate search
 * keywords + deep links. Ported from backend/app/services/douyin_service.py.
 */

import type { DouyinLink } from "../types";

const WEB_SEARCH = "https://www.douyin.com/search/";
const DEEP_LINK = "snssdk1128://search/result?keyword=";

export function generateDouyinLink(
  keyword: string,
  label = "看抖音视频",
  relatedType = "poi",
  relatedId = ""
): DouyinLink {
  const encoded = encodeURIComponent(keyword);
  return {
    keyword,
    search_url: `${WEB_SEARCH}${encoded}`,
    qr_code_data: `${DEEP_LINK}${encoded}`,
    label,
    related_type: relatedType,
    related_id: relatedId,
  };
}

export function linksForPoi(poiName: string, poiCity = "", poiId = ""): DouyinLink[] {
  const links: DouyinLink[] = [
    generateDouyinLink(poiName, `看${poiName}视频`, "poi", poiId),
    generateDouyinLink(`${poiName}攻略`, "游玩攻略", "poi", poiId),
  ];
  if (poiCity) links.push(generateDouyinLink(`${poiCity}美食`, `${poiCity}美食`, "city", poiId));
  return links;
}

export function linksForMeal(dishName: string, cuisineType = "", city = "", mealId = ""): DouyinLink[] {
  const links: DouyinLink[] = [generateDouyinLink(dishName, `看${dishName}视频`, "meal", mealId)];
  if (cuisineType) links.push(generateDouyinLink(cuisineType, "菜系探店", "meal", mealId));
  if (city) links.push(generateDouyinLink(`${city}特色美食`, `${city}特色菜`, "city", mealId));
  return links;
}

export function linksForStory(figure = "", event = "", city = "", storyId = ""): DouyinLink[] {
  const links: DouyinLink[] = [];
  if (figure) links.push(generateDouyinLink(figure, `了解${figure}`, "story", storyId));
  if (event) links.push(generateDouyinLink(event, `看${event}视频`, "story", storyId));
  return links;
}
