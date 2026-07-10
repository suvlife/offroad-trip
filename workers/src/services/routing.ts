/**
 * Driving route planning — free / no-key.
 * Uses the public OSRM demo server for real road geometry, distance, duration.
 * Falls back to a great-circle estimate when OSRM is unavailable.
 *
 * NOTE: OSRM's public server (router.project-osrm.org) is best-effort and rate
 * limited — fine for a demo, not production SLA. Swap in a self-hosted OSRM or
 * a keyed provider later if needed. Toll is not provided by OSRM, so we estimate.
 */

import type { GeoPoint } from "../types";

const OSRM = "https://router.project-osrm.org/route/v1/driving";
const TOLL_RATE = 0.45; // yuan/km, rough estimate

export interface RouteInfo {
  distance: number; // km
  duration: number; // hours
  toll: number; // yuan (estimated)
  polyline: [number, number][]; // [[lat,lng],...]
}

export async function planDrivingRoute(from: GeoPoint, to: GeoPoint): Promise<RouteInfo | null> {
  // OSRM expects lng,lat order.
  const coords = `${from.lng},${from.lat};${to.lng},${to.lat}`;
  const url = `${OSRM}/${coords}?overview=full&geometries=geojson`;

  try {
    const resp = await fetch(url);
    if (resp.ok) {
      const data = (await resp.json()) as any;
      const route = data.routes?.[0];
      if (route) {
        const distanceKm = route.distance / 1000;
        // GeoJSON coordinates are [lng,lat]; convert to [lat,lng].
        const polyline: [number, number][] = (route.geometry?.coordinates ?? []).map(
          ([lng, lat]: [number, number]) => [lat, lng]
        );
        return {
          distance: round1(distanceKm),
          duration: round1(route.duration / 3600),
          toll: Math.round(distanceKm * TOLL_RATE),
          polyline: downsample(polyline, 500),
        };
      }
    }
  } catch (e) {
    console.warn(`OSRM failed: ${e}`);
  }

  // Fallback: great-circle estimate + straight-line polyline
  const dist = haversine(from.lat, from.lng, to.lat, to.lng);
  return {
    distance: round1(dist),
    duration: round1(dist / 80), // assume 80 km/h
    toll: Math.round(dist * TOLL_RATE),
    polyline: [
      [from.lat, from.lng],
      [to.lat, to.lng],
    ],
  };
}

function haversine(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Keep payload small: cap polyline points (evenly sampled) to avoid huge SSE/D1 blobs.
function downsample(points: [number, number][], maxPoints: number): [number, number][] {
  if (points.length <= maxPoints) return points;
  const step = Math.ceil(points.length / maxPoints);
  const out: [number, number][] = [];
  for (let i = 0; i < points.length; i += step) out.push(points[i]);
  if (out[out.length - 1] !== points[points.length - 1]) out.push(points[points.length - 1]);
  return out;
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}
