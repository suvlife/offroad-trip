/**
 * Geocoding + city fallback coordinates.
 * Free / no-key: OpenStreetMap Nominatim, with a built-in city table fallback
 * and Workers KV caching (replaces the Python in-process cache).
 *
 * Coordinate system: WGS-84 (OSM native). The whole stack is WGS-84 now that
 * Tencent (GCJ-02) is dropped — points and OSM tiles align with no offset.
 */

import type { Env, GeoPoint } from "../types";

// Built-in city coordinates (WGS-84) — offline fallback when Nominatim fails
// or is rate-limited. Ported/expanded from qqmap_service.CITY_COORDS_FALLBACK.
export const CITY_COORDS: Record<string, [number, number]> = {
  北京: [39.9042, 116.4074], 上海: [31.2304, 121.4737], 广州: [23.1291, 113.2644],
  深圳: [22.5431, 114.0579], 成都: [30.5728, 104.0668], 重庆: [29.563, 106.5516],
  杭州: [30.2741, 120.1551], 南京: [32.0603, 118.7969], 武汉: [30.5928, 114.3055],
  西安: [34.3416, 108.9398], 长沙: [28.2282, 112.9388], 天津: [39.3434, 117.3616],
  苏州: [31.2989, 120.5853], 郑州: [34.7466, 113.6253], 沈阳: [41.8057, 123.4315],
  长春: [43.8171, 125.3235], 哈尔滨: [45.8038, 126.535], 大连: [38.914, 121.6147],
  呼和浩特: [40.8426, 111.7497], 乌鲁木齐: [43.8256, 87.6168], 兰州: [36.0611, 103.8343],
  银川: [38.4872, 106.2309], 西宁: [36.6171, 101.7782], 拉萨: [29.65, 91.1409],
  昆明: [25.0389, 102.7183], 贵阳: [26.647, 106.6302], 南宁: [22.817, 108.3669],
  海口: [20.0444, 110.1989], 太原: [37.8706, 112.5489], 石家庄: [38.0428, 114.5149],
  济南: [36.6512, 117.1201], 青岛: [36.0671, 120.3826], 合肥: [31.8206, 117.2272],
  南昌: [28.682, 115.8579], 福州: [26.0745, 119.2965], 厦门: [24.4798, 118.0894],
  承德: [40.951, 117.9626], 漠河: [52.9749, 122.5349], 齐齐哈尔: [47.354, 123.9183],
  加格达奇: [50.424, 124.114], 通辽: [43.6527, 122.2437], 赤峰: [42.257, 118.8892],
  延吉: [42.8917, 129.5097], 丹东: [40.1295, 124.3936], 额济纳旗: [41.9545, 101.0558],
  稻城: [28.4314, 100.3316], 康定: [30.0486, 101.9625], 伊犁: [43.9191, 81.3245],
  额尔古纳: [50.241, 120.183], 室韦: [51.347, 119.752], 呼伦贝尔: [49.2112, 119.7661],
  满洲里: [49.5965, 117.4306],
};

const NOMINATIM = "https://nominatim.openstreetmap.org/search";
const CACHE_TTL = 60 * 60 * 24 * 30; // 30 days

export async function geocode(env: Env, address: string, biasCity = ""): Promise<GeoPoint | null> {
  if (!address) return null;

  // Bias bare POI/landmark names with their city so Nominatim doesn't match an
  // identically-named place elsewhere in China (e.g. "双塔山风景区" exists near
  // multiple cities) — this previously corrupted segment distances by 1000s of km.
  const query = biasCity && !address.includes(biasCity) ? `${biasCity}${address}` : address;

  const cacheKey = `geo:${query}`;
  const cached = await env.GEO_CACHE.get(cacheKey, "json").catch(() => null);
  if (cached) return cached as GeoPoint;

  let result = await geocodeImpl(env, query);
  // If the biased query found nothing, retry with the bare name before giving up.
  if (!result && query !== address) result = await geocodeImpl(env, address);
  if (result) {
    await env.GEO_CACHE.put(cacheKey, JSON.stringify(result), { expirationTtl: CACHE_TTL }).catch(() => {});
  }
  return result;
}

async function geocodeImpl(env: Env, address: string): Promise<GeoPoint | null> {
  // Try Nominatim (free, no key). Requires a descriptive User-Agent.
  try {
    const url = `${NOMINATIM}?q=${encodeURIComponent(address)}&format=json&limit=1&countrycodes=cn`;
    const resp = await fetch(url, {
      headers: { "User-Agent": env.NOMINATIM_UA || "offroad-trip/1.0", "Accept-Language": "zh-CN" },
    });
    if (resp.ok) {
      const data = (await resp.json()) as any[];
      if (data.length > 0) {
        return {
          lat: parseFloat(data[0].lat),
          lng: parseFloat(data[0].lon),
          city: address,
          province: "",
        };
      }
    }
  } catch (e) {
    console.warn(`Nominatim failed for '${address}': ${e}`);
  }

  // Fallback: built-in table (exact, then partial match)
  if (CITY_COORDS[address]) {
    const [lat, lng] = CITY_COORDS[address];
    return { lat, lng, city: address, province: "" };
  }
  for (const [name, [lat, lng]] of Object.entries(CITY_COORDS)) {
    if (address.includes(name) || name.includes(address)) {
      return { lat, lng, city: address, province: "" };
    }
  }

  console.error(`Could not geocode '${address}' - no fallback`);
  return null;
}
