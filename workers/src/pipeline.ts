/**
 * The 6-stage planning pipeline, ported from backend/app/agents/*.py with all
 * five bug fixes from the Python reference baked in:
 *   #1 id/share_id injected at persist time (see db.saveRoute)
 *   #2 content enrichment grouped per-DAY (each POI enriched exactly once)
 *   #3 POIs geocoded so map markers land on real coordinates
 *   #4 per-day weather advisory keyed on the day's destination city
 *   #5 geocode() cached (via KV in geo.ts)
 *
 * Each stage is a pure async function taking (env, ...) so the Workflow can wrap
 * them in durable steps, and a local dev path can call them inline.
 */

import type { Env, GenerateRequest, RouteData, DayPlan, WeatherData, CostBreakdown } from "./types";
import { callLlm, parseJsonResponse } from "./services/llm";
import * as geo from "./services/geo";
import { planDrivingRoute } from "./services/routing";
import * as weather from "./services/weather";
import { searchPhoto } from "./services/images";
import * as douyin from "./services/douyin";
import { calculateSegmentCost, calculateRouteCost } from "./services/cost";
import {
  PLANNER_SYSTEM,
  buildPlannerPrompt,
  SCENIC_SYSTEM,
  buildScenicPrompt,
  FOOD_SYSTEM,
  buildFoodPrompt,
  HISTORY_SYSTEM,
  buildHistoryPrompt,
} from "./prompts";

export interface NormalizedReq extends Required<GenerateRequest> {}

export function normalizeReq(req: GenerateRequest): NormalizedReq {
  return {
    departure: req.departure,
    destination: req.destination,
    start_date: req.start_date ?? "",
    days: req.days ?? 3,
    trip_type: req.trip_type ?? "越野自驾",
    vehicle_type: req.vehicle_type ?? "SUV",
    adults: req.adults ?? 2,
    children: req.children ?? 0,
    budget: req.budget ?? 8000,
    theme: req.theme ?? "回归自然",
    preferences: req.preferences ?? [],
    session_id: req.session_id ?? "",
  };
}

/** Stage 1: geocode departure/destination. */
export async function stageGeocode(env: Env, req: NormalizedReq) {
  const dep = await geo.geocode(env, req.departure);
  const dest = await geo.geocode(env, req.destination);
  if (!dep || !dest) throw new Error("无法定位城市，请检查地名");
  const geoInfo =
    `出发地 ${req.departure}: ${dep.lat},${dep.lng} (${dep.province ?? ""})\n` +
    `目的地 ${req.destination}: ${dest.lat},${dest.lng} (${dest.province ?? ""})`;
  return { dep, dest, geoInfo };
}

/** Stage 2: weather for departure + destination. */
export async function stageWeather(env: Env, req: NormalizedReq): Promise<Record<string, WeatherData>> {
  return weather.fetchWeatherForCities([req.departure, req.destination], req.days);
}

/** Stage 3: LLM produces the route skeleton. */
export async function stagePlanning(
  env: Env,
  req: NormalizedReq,
  weatherMap: Record<string, WeatherData>,
  geoInfo: string
): Promise<RouteData> {
  const prompt = buildPlannerPrompt({
    departure: req.departure,
    destination: req.destination,
    start_date: req.start_date,
    days: req.days,
    trip_type: req.trip_type,
    vehicle_type: req.vehicle_type,
    adults: req.adults,
    children: req.children,
    budget: req.budget,
    theme: req.theme,
    preferences: req.preferences,
    weather_info: weather.formatWeatherForPlanner(weatherMap),
    geo_info: geoInfo,
  });

  const content = await callLlm(env, prompt, {
    systemPrompt: PLANNER_SYSTEM,
    jsonMode: true,
    maxTokens: 16384,
    temperature: 0.3,
  });
  const result = parseJsonResponse<RouteData>(content) as RouteData;

  // Defaults (port of planner_agent.plan_route setdefault block).
  result.title ??= `${req.departure}至${req.destination}越野自驾`;
  result.theme ??= req.theme || "回归自然";
  result.departure ??= req.departure;
  result.destination ??= req.destination;
  result.vehicle_type ??= req.vehicle_type;
  result.trip_type ??= req.trip_type;
  result.adults ??= req.adults;
  result.children ??= req.children;
  result.budget ??= req.budget;
  result.status ??= "draft";
  result.terrain_difficulty ??= 2;
  result.nature_score ??= 4;
  result.overall_tips ??= "";
  result.day_plans ??= [];

  // Bug #4: per-day weather advisory keyed on each day's destination city.
  const planCities: string[] = [];
  for (const day of result.day_plans) {
    const city = dayCity(day);
    if (city && !weatherMap[city] && !planCities.includes(city)) planCities.push(city);
  }
  if (planCities.length) {
    Object.assign(weatherMap, await weather.fetchWeatherForCities(planCities, req.days));
  }
  for (const day of result.day_plans) {
    day.weather_advisory = weather.advisoryForCity(weatherMap, dayCity(day));
  }
  return result;
}

/** Stage 4: routing (real polylines + costs) + POI geocoding (bug #3). */
export async function stageRouting(env: Env, req: NormalizedReq, routeData: RouteData): Promise<RouteData> {
  let totalDistance = 0;
  let totalDuration = 0;

  for (const day of routeData.day_plans ?? []) {
    let dayDistance = 0;
    let dayDuration = 0;
    const city = dayCity(day);

    for (const seg of day.segments ?? []) {
      // Bias geocoding with the day's city so bare landmark names (e.g. "双塔山
      // 风景区") don't match an identically-named place elsewhere in China.
      const fromGeo = await geo.geocode(env, seg.from_name, city);
      const toGeo = await geo.geocode(env, seg.to_name, city);
      if (fromGeo && toGeo) {
        const info = await planDrivingRoute(fromGeo, toGeo);
        if (info && isPlausibleSegment(info.distance, req.days)) {
          seg.distance = info.distance;
          seg.duration = info.duration;
          seg.toll_cost = info.toll;
          seg.polyline = info.polyline;
          seg.fuel_cost = calculateSegmentCost(info.distance, req.vehicle_type, true, info.toll).fuel_cost;
          dayDistance += info.distance;
          dayDuration += info.duration;
        } else if (info) {
          console.warn(
            `Discarding implausible segment ${seg.from_name}->${seg.to_name}: ${info.distance}km (likely a geocode mismatch)`
          );
        }
      }
    }

    day.day_distance = round1(dayDistance);
    day.day_duration = round1(dayDuration);
    totalDistance += dayDistance;
    totalDuration += dayDuration;

    // Bug #3: geocode POIs so markers land on real coords (endpoint city fallback).
    for (const poi of day.pois ?? []) {
      if (poi.lat && poi.lng) continue;
      let g = poi.name ? await geo.geocode(env, poi.name, city) : null;
      if (!g && city) g = await geo.geocode(env, city);
      if (g) {
        poi.lat = g.lat;
        poi.lng = g.lng;
      }
    }
  }

  routeData.total_distance = round1(totalDistance);
  routeData.total_duration = round1(totalDuration);
  return routeData;
}

/** Stage 5: content enrichment — grouped per-DAY so each POI is enriched once (bug #2). */
export async function stageEnrichment(env: Env, routeData: RouteData): Promise<RouteData> {
  type Task = { kind: "scenic" | "food" | "history"; day: DayPlan; run: () => Promise<unknown> };
  const tasks: Task[] = [];

  for (const day of routeData.day_plans ?? []) {
    const city = dayCity(day) || day.theme || routeData.destination || "";
    const pois = day.pois ?? [];
    const meals = day.meals ?? [];
    const scenicNames = pois.map((p) => p.name).filter(Boolean);

    tasks.push({ kind: "scenic", day, run: () => enrichScenic(env, city, pois) });
    tasks.push({ kind: "food", day, run: () => enrichFood(env, city, meals) });
    tasks.push({ kind: "history", day, run: () => enrichHistory(env, city, scenicNames) });
  }

  const results = await Promise.allSettled(tasks.map((t) => t.run()));
  const allStories: RouteData["story_cards"] = [];
  results.forEach((res, i) => {
    const t = tasks[i];
    if (t.kind === "history" && res.status === "fulfilled" && Array.isArray(res.value)) {
      for (const story of res.value as any[]) {
        story.day_number ??= t.day.day_number ?? 0;
        allStories!.push(story);
      }
    }
  });
  routeData.story_cards = allStories;
  return routeData;
}

/** Stage 6: assembly — images, douyin links, total cost. */
export async function stageAssembly(env: Env, req: NormalizedReq, routeData: RouteData, weatherMap: Record<string, WeatherData>): Promise<RouteData> {
  for (const day of routeData.day_plans ?? []) {
    const city = dayCity(day);
    for (const poi of day.pois ?? []) {
      if (poi.name && !poi.image_url) poi.image_url = searchPhoto(poi.name, poi.name);
    }
    for (const meal of day.meals ?? []) {
      if (meal.restaurant_name && !meal.image_url) meal.image_url = searchPhoto(meal.restaurant_name);
    }

    // Douyin links
    for (const poi of day.pois ?? []) {
      if (poi.name) (routeData.douyin_links ??= []).push(...douyin.linksForPoi(poi.name, city, poi.id ?? ""));
    }
    for (const meal of day.meals ?? []) {
      if (meal.restaurant_name)
        (routeData.douyin_links ??= []).push(...douyin.linksForMeal(meal.restaurant_name, meal.cuisine_type ?? "", city));
    }
  }
  for (const story of routeData.story_cards ?? []) {
    if (story.figure || story.event)
      (routeData.douyin_links ??= []).push(
        ...douyin.linksForStory(story.figure ?? "", story.event ?? "", story.related_city ?? "")
      );
  }

  const scenicCount = (routeData.day_plans ?? []).reduce(
    (acc, day) => acc + (day.pois ?? []).filter((p) => ["scenic", "nature"].includes(p.category ?? "")).length,
    0
  );
  routeData.cost_breakdown = calculateRouteCost({
    totalDistance: routeData.total_distance ?? 0,
    days: req.days,
    adults: req.adults,
    children: req.children,
    vehicleType: req.vehicle_type,
    scenicCount,
  });

  routeData._weather_map = Object.fromEntries(
    Object.entries(weatherMap).map(([city, data]) => [city, data.forecasts ?? []])
  );
  return routeData;
}

// ── enrichment helpers (port of content_agents.py) ──────────────────────────

async function enrichScenic(env: Env, city: string, pois: RouteData["day_plans"][number]["pois"]): Promise<void> {
  if (!pois.length) return;
  const scenicList = pois.filter((p) => p.name).map((p) => `- ${p.name}: ${p.description ?? ""}`).join("\n");
  if (!scenicList.trim()) return;
  try {
    const content = await callLlm(env, buildScenicPrompt(city, scenicList), { systemPrompt: SCENIC_SYSTEM, jsonMode: true });
    const result = parseJsonResponse<{ pois?: any[] }>(content);
    const map = new Map((result.pois ?? []).filter((p) => p.name).map((p) => [p.name, p]));
    for (const poi of pois) {
      const m = map.get(poi.name);
      if (m) {
        poi.feature = m.feature ?? poi.feature ?? "";
        poi.anecdote = m.anecdote ?? poi.anecdote ?? "";
        poi.historical_figure = m.historical_figure ?? "";
        poi.historical_event = m.historical_event ?? "";
        if (m.description) poi.description = m.description;
        if (m.duration_minutes) poi.duration_minutes = m.duration_minutes;
      }
    }
  } catch (e) {
    console.error(`Scenic enrichment failed for ${city}: ${e}`);
  }
}

async function enrichFood(env: Env, city: string, meals: RouteData["day_plans"][number]["meals"]): Promise<void> {
  if (!meals.length) return;
  const foodList = meals.filter((m) => m.restaurant_name).map((m) => `- ${m.restaurant_name} (${m.cuisine_type ?? ""})`).join("\n");
  if (!foodList.trim()) return;
  try {
    const content = await callLlm(env, buildFoodPrompt(city, foodList), { systemPrompt: FOOD_SYSTEM, jsonMode: true });
    const result = parseJsonResponse<{ meals?: any[] }>(content);
    const map = new Map((result.meals ?? []).filter((m) => m.restaurant_name).map((m) => [m.restaurant_name, m]));
    for (const meal of meals) {
      const m = map.get(meal.restaurant_name);
      if (m) {
        meal.story = m.story ?? "";
        meal.is_local_specialty = !!m.is_local_specialty;
        if (m.recommendation) meal.recommendation = m.recommendation;
        if (m.cost_per_person) meal.cost_per_person = m.cost_per_person;
      }
    }
  } catch (e) {
    console.error(`Food enrichment failed for ${city}: ${e}`);
  }
}

async function enrichHistory(env: Env, city: string, scenicNames: string[]): Promise<any[]> {
  const names = scenicNames.length ? scenicNames.join("、") : city;
  try {
    const content = await callLlm(env, buildHistoryPrompt(city, names), { systemPrompt: HISTORY_SYSTEM, jsonMode: true });
    const result = parseJsonResponse<{ stories?: any[] }>(content);
    const stories = result.stories ?? [];
    for (const s of stories) {
      s.related_city ??= city;
      s.figure ??= "";
      s.event ??= "";
      s.anecdote ??= "";
      s.story_text ??= "";
    }
    return stories;
  } catch (e) {
    console.error(`History enrichment failed for ${city}: ${e}`);
    return [];
  }
}

// ── shared helpers ───────────────────────────────────────────────────────────

/** The day's anchor city = last segment's to_name (fallback: first from_name). */
export function dayCity(day: DayPlan): string {
  const segs = day.segments ?? [];
  if (segs.length) return segs[segs.length - 1].to_name || segs[0].from_name || "";
  return "";
}

/**
 * Reject segments whose driven distance is absurd for a single day's leg — the
 * telltale sign of a geocode mismatch (a bare POI name resolving to a
 * same-named place elsewhere in China, e.g. "双塔山风景区" 2000+km away).
 * A real single day-plan segment essentially never exceeds ~600km.
 */
function isPlausibleSegment(distanceKm: number, _days: number): boolean {
  return distanceKm > 0 && distanceKm <= 600;
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}
