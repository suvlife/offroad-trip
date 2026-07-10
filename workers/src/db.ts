/**
 * D1 persistence layer. Ports backend/app/routers/{generate.py:_save_route_to_db,
 * routes.py} to raw D1 SQL. UUIDs via crypto.randomUUID(); JSON columns are
 * stringified on write and parsed on read.
 */

import type { RouteData } from "./types";

const uuid = () => crypto.randomUUID();
const shareId = () => {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
};

/** Persist a generated route; returns the new id. Injects id/share_id into routeData. */
export async function saveRoute(db: D1Database, routeData: RouteData): Promise<string> {
  const routeId = uuid();
  const sid = shareId();
  const stmts: D1PreparedStatement[] = [];

  stmts.push(
    db
      .prepare(
        `INSERT INTO routes (id, share_id, title, departure, destination, total_distance,
          total_duration, trip_type, theme, vehicle_type, terrain_difficulty, nature_score,
          adults, children, budget, status, overall_tips, cost_breakdown)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`
      )
      .bind(
        routeId,
        sid,
        routeData.title ?? "",
        routeData.departure ?? "",
        routeData.destination ?? "",
        routeData.total_distance ?? 0,
        routeData.total_duration ?? 0,
        routeData.trip_type ?? "越野自驾",
        routeData.theme ?? "回归自然",
        routeData.vehicle_type ?? "SUV",
        routeData.terrain_difficulty ?? 2,
        routeData.nature_score ?? 4,
        routeData.adults ?? 2,
        routeData.children ?? 0,
        routeData.budget ?? 0,
        "draft",
        routeData.overall_tips ?? "",
        JSON.stringify(routeData.cost_breakdown ?? {})
      )
  );

  for (const day of routeData.day_plans ?? []) {
    const dayId = uuid();
    stmts.push(
      db
        .prepare(
          `INSERT INTO day_plans (id, route_id, day_number, date, theme, day_distance,
            day_duration, day_cost, weather_advisory, scenery_description, terrain_note)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)`
        )
        .bind(
          dayId,
          routeId,
          day.day_number ?? 1,
          day.date ?? "",
          day.theme ?? "",
          day.day_distance ?? 0,
          day.day_duration ?? 0,
          0,
          day.weather_advisory ?? "",
          day.scenery_description ?? "",
          day.terrain_note ?? ""
        )
    );

    for (const seg of day.segments ?? []) {
      stmts.push(
        db
          .prepare(
            `INSERT INTO route_segments (id, day_plan_id, from_name, to_name, distance,
              duration, toll_cost, fuel_cost, polyline, sort_order)
             VALUES (?,?,?,?,?,?,?,?,?,?)`
          )
          .bind(
            uuid(),
            dayId,
            seg.from_name ?? "",
            seg.to_name ?? "",
            seg.distance ?? 0,
            seg.duration ?? 0,
            seg.toll_cost ?? 0,
            seg.fuel_cost ?? 0,
            JSON.stringify(seg.polyline ?? []),
            seg.sort_order ?? 0
          )
      );
    }

    for (const poi of day.pois ?? []) {
      stmts.push(
        db
          .prepare(
            `INSERT INTO pois (id, day_plan_id, segment_id, type, category, name, lat, lng,
              image_url, description, duration_minutes, sort_order, feature, anecdote,
              historical_figure, historical_event)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`
          )
          .bind(
            uuid(),
            dayId,
            null,
            poi.type ?? "scenic",
            poi.category ?? "scenic",
            poi.name ?? "",
            poi.lat ?? 0,
            poi.lng ?? 0,
            poi.image_url ?? "",
            poi.description ?? "",
            poi.duration_minutes ?? 0,
            poi.sort_order ?? 0,
            poi.feature ?? "",
            poi.anecdote ?? "",
            poi.historical_figure ?? "",
            poi.historical_event ?? ""
          )
      );
    }

    for (const meal of day.meals ?? []) {
      stmts.push(
        db
          .prepare(
            `INSERT INTO meals (id, day_plan_id, type, restaurant_name, cuisine_type,
              cost_per_person, image_url, recommendation, is_local_specialty, story)
             VALUES (?,?,?,?,?,?,?,?,?,?)`
          )
          .bind(
            uuid(),
            dayId,
            meal.type ?? "lunch",
            meal.restaurant_name ?? "",
            meal.cuisine_type ?? "",
            meal.cost_per_person ?? 0,
            meal.image_url ?? "",
            meal.recommendation ?? "",
            meal.is_local_specialty ? 1 : 0,
            meal.story ?? ""
          )
      );
    }

    for (const hotel of day.hotels ?? []) {
      stmts.push(
        db
          .prepare(
            `INSERT INTO hotels (id, day_plan_id, name, lat, lng, price_per_night, rating, address)
             VALUES (?,?,?,?,?,?,?,?)`
          )
          .bind(
            uuid(),
            dayId,
            hotel.name ?? "",
            hotel.lat ?? 0,
            hotel.lng ?? 0,
            hotel.price_per_night ?? 0,
            hotel.rating ?? 0,
            hotel.address ?? ""
          )
      );
    }
  }

  for (const s of routeData.story_cards ?? []) {
    stmts.push(
      db
        .prepare(
          `INSERT INTO story_cards (id, route_id, related_city, day_number, figure, event, anecdote, story_text)
           VALUES (?,?,?,?,?,?,?,?)`
        )
        .bind(
          uuid(),
          routeId,
          s.related_city ?? "",
          s.day_number ?? 0,
          s.figure ?? "",
          s.event ?? "",
          s.anecdote ?? "",
          s.story_text ?? ""
        )
    );
  }

  for (const dl of routeData.douyin_links ?? []) {
    stmts.push(
      db
        .prepare(
          `INSERT INTO douyin_links (id, route_id, related_type, related_id, keyword, search_url, qr_code_data, label)
           VALUES (?,?,?,?,?,?,?,?)`
        )
        .bind(
          uuid(),
          routeId,
          dl.related_type ?? "poi",
          dl.related_id ?? "",
          dl.keyword ?? "",
          dl.search_url ?? "",
          dl.qr_code_data ?? "",
          dl.label ?? ""
        )
    );
  }

  const weatherMap = routeData._weather_map ?? {};
  for (const [city, forecasts] of Object.entries(weatherMap)) {
    for (const f of forecasts) {
      stmts.push(
        db
          .prepare(
            `INSERT INTO weather_forecasts (id, route_id, city_name, date, temperature_high,
              temperature_low, weather_condition, icon, humidity, wind_speed, precipitation)
             VALUES (?,?,?,?,?,?,?,?,?,?,?)`
          )
          .bind(
            uuid(),
            routeId,
            city,
            f.date ?? "",
            f.temperature_high ?? 0,
            f.temperature_low ?? 0,
            f.weather_condition ?? "",
            f.icon ?? "",
            f.humidity ?? 0,
            f.wind_speed ?? 0,
            f.precipitation ?? 0
          )
      );
    }
  }

  await db.batch(stmts);
  routeData.id = routeId;
  routeData.share_id = sid;
  return routeId;
}

/** List routes (newest first). */
export async function listRoutes(db: D1Database, page = 1, pageSize = 10) {
  const offset = (page - 1) * pageSize;
  const { results } = await db
    .prepare(
      `SELECT id, share_id, title, departure, destination, total_distance, total_duration,
        trip_type, theme, vehicle_type, terrain_difficulty, nature_score, status, view_count, created_at
       FROM routes ORDER BY created_at DESC LIMIT ? OFFSET ?`
    )
    .bind(pageSize, offset)
    .all();
  return results;
}

/** Load a full route by a WHERE clause (id or share_id). */
export async function loadRoute(db: D1Database, by: "id" | "share_id", value: string): Promise<RouteData | null> {
  const route = await db.prepare(`SELECT * FROM routes WHERE ${by} = ?`).bind(value).first<any>();
  if (!route) return null;

  const rid = route.id;
  const [days, segments, pois, meals, hotels, stories, weather] = await Promise.all([
    db.prepare(`SELECT * FROM day_plans WHERE route_id = ? ORDER BY day_number`).bind(rid).all(),
    db.prepare(`SELECT s.* FROM route_segments s JOIN day_plans d ON s.day_plan_id = d.id WHERE d.route_id = ? ORDER BY s.sort_order`).bind(rid).all(),
    db.prepare(`SELECT p.* FROM pois p JOIN day_plans d ON p.day_plan_id = d.id WHERE d.route_id = ? ORDER BY p.sort_order`).bind(rid).all(),
    db.prepare(`SELECT m.* FROM meals m JOIN day_plans d ON m.day_plan_id = d.id WHERE d.route_id = ?`).bind(rid).all(),
    db.prepare(`SELECT h.* FROM hotels h JOIN day_plans d ON h.day_plan_id = d.id WHERE d.route_id = ?`).bind(rid).all(),
    db.prepare(`SELECT * FROM story_cards WHERE route_id = ?`).bind(rid).all(),
    db.prepare(`SELECT * FROM weather_forecasts WHERE route_id = ?`).bind(rid).all(),
  ]);

  const byDay = <T extends { day_plan_id: string }>(rows: T[]) => {
    const m: Record<string, T[]> = {};
    for (const r of rows) (m[r.day_plan_id] ??= []).push(r);
    return m;
  };
  const segByDay = byDay(segments.results as any[]);
  const poiByDay = byDay(pois.results as any[]);
  const mealByDay = byDay(meals.results as any[]);
  const hotelByDay = byDay(hotels.results as any[]);

  const day_plans = (days.results as any[]).map((d) => ({
    ...d,
    segments: (segByDay[d.id] ?? []).map((s) => ({ ...s, polyline: safeJson(s.polyline, []) })),
    pois: poiByDay[d.id] ?? [],
    meals: (mealByDay[d.id] ?? []).map((m) => ({ ...m, is_local_specialty: !!m.is_local_specialty })),
    hotels: hotelByDay[d.id] ?? [],
  }));

  return {
    ...route,
    cost_breakdown: safeJson(route.cost_breakdown, {}),
    day_plans,
    story_cards: stories.results,
    weather_forecasts: weather.results,
  } as unknown as RouteData;
}

export async function incrementView(db: D1Database, id: string) {
  await db.prepare(`UPDATE routes SET view_count = view_count + 1 WHERE id = ?`).bind(id).run();
}

export async function publishRoute(db: D1Database, id: string): Promise<string | null> {
  const route = await db.prepare(`SELECT share_id FROM routes WHERE id = ?`).bind(id).first<any>();
  if (!route) return null;
  await db.prepare(`UPDATE routes SET status = 'published' WHERE id = ?`).bind(id).run();
  return route.share_id;
}

export async function deleteRoute(db: D1Database, id: string): Promise<boolean> {
  const res = await db.prepare(`DELETE FROM routes WHERE id = ?`).bind(id).run();
  return (res.meta.changes ?? 0) > 0;
}

function safeJson<T>(s: unknown, fallback: T): T {
  if (typeof s !== "string") return (s as T) ?? fallback;
  try {
    return JSON.parse(s) as T;
  } catch {
    return fallback;
  }
}
