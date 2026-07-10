/**
 * Map helpers backed by MapLibre GL JS + free, no-key OpenStreetMap raster tiles
 * (Carto Voyager). Replaces the Tencent Maps GL loader (which required a key).
 *
 * Keeps the same exported function names as the old util so the view layer needs
 * only an import-path change. Coordinates in this app are [lat, lng] (WGS-84);
 * MapLibre uses [lng, lat], so every point is flipped at the boundary here.
 */

import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// No API key needed with OSM tiles — kept for interface compatibility.
export function hasMapKey() {
  return true;
}

// Day colors for polylines (unchanged).
export const DAY_COLORS = [
  "#2D9D5F", "#3B9AE1", "#FF8C42", "#8B5CF6", "#EF4444", "#14B8A6", "#F59E0B",
];

export const POI_ICONS = {
  scenic: "🏔️", nature: "🌲", history: "🏛️", food: "🍽️",
  viewpoint: "📸", gas_station: "⛽", hotel: "🏨", waypoint: "📍", default: "📍",
};

export const POI_COLORS = {
  scenic: "#2D9D5F", nature: "#16a34a", history: "#8B5CF6", food: "#FF8C42",
  viewpoint: "#3B9AE1", gas_station: "#EF4444", hotel: "#6366f1",
  waypoint: "#94a3b8", default: "#94a3b8",
};

// Free, no-key raster style (OSM data via Carto Voyager).
const OSM_RASTER_STYLE = {
  version: 8,
  sources: {
    carto: {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
        "https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
        "https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors © CARTO",
    },
  },
  layers: [{ id: "carto", type: "raster", source: "carto" }],
};

let polylineSeq = 0;

/**
 * Create a MapLibre map. Resolves once the style has loaded so callers can add
 * sources/layers immediately. Returns { map, TMap: null } for interface parity.
 * @param {HTMLElement|string} container
 * @param {{center?: [number,number], zoom?: number, pitch?: number}} options
 */
export async function createMap(container, options = {}) {
  const { center = [39.9, 116.4], zoom = 6, pitch = 45 } = options;
  const map = new maplibregl.Map({
    container,
    style: OSM_RASTER_STYLE,
    center: [center[1], center[0]], // [lat,lng] -> [lng,lat]
    zoom,
    pitch,
    attributionControl: true,
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

  await new Promise((resolve) => {
    if (map.loaded()) resolve();
    else map.on("load", () => resolve());
  });
  return { map, TMap: null };
}

/**
 * Draw one day's route as a line layer.
 * @param {maplibregl.Map} map
 * @param {*} _TMap unused (interface parity)
 * @param {Array<[number,number]>} polyline [[lat,lng],...]
 */
export function drawPolyline(map, _TMap, polyline, color = "#2D9D5F", width = 6) {
  if (!polyline || polyline.length < 2) return null;
  const coords = polyline
    .filter((p) => Array.isArray(p) && p.length >= 2 && p[0] && p[1])
    .map(([lat, lng]) => [lng, lat]);
  if (coords.length < 2) return null;

  const id = `route-${polylineSeq++}`;
  map.addSource(id, {
    type: "geojson",
    data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: coords } },
  });
  map.addLayer({
    id,
    type: "line",
    source: id,
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": color, "line-width": width },
  });
  return id;
}

/**
 * Add POI markers (emoji pins colored by category).
 * @param {maplibregl.Map} map
 * @param {*} _TMap unused
 * @param {Array<{lat:number,lng:number,category?:string,name?:string,feature?:string}>} pois
 */
export function addPOIMarkers(map, _TMap, pois) {
  if (!pois || pois.length === 0) return null;
  const markers = [];
  for (const poi of pois) {
    if (!poi.lat || !poi.lng) continue;
    const cat = poi.category || "default";
    const color = POI_COLORS[cat] || POI_COLORS.default;
    const icon = POI_ICONS[cat] || POI_ICONS.default;

    const el = document.createElement("div");
    el.style.cssText =
      `width:32px;height:32px;border-radius:50%;background:${color};border:2px solid #fff;` +
      `display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 1px 4px rgba(0,0,0,.3);cursor:pointer;`;
    el.textContent = icon;

    const marker = new maplibregl.Marker({ element: el })
      .setLngLat([poi.lng, poi.lat])
      .addTo(map);
    if (poi.name) {
      marker.setPopup(
        new maplibregl.Popup({ offset: 20, closeButton: false }).setHTML(
          `<strong>${poi.name}</strong>${poi.feature ? `<br/><span style="font-size:12px;color:#555">${poi.feature}</span>` : ""}`
        )
      );
    }
    markers.push(marker);
  }
  return markers;
}

/**
 * Fit the viewport to all points.
 * @param {maplibregl.Map} map
 * @param {*} _TMap unused
 * @param {Array<[number,number]>} points [[lat,lng],...]
 */
export function fitBounds(map, _TMap, points) {
  if (!points || points.length === 0) return;
  const valid = points.filter((p) => Array.isArray(p) && p.length >= 2 && p[0] && p[1]);
  if (valid.length === 0) return;
  const bounds = new maplibregl.LngLatBounds();
  for (const [lat, lng] of valid) bounds.extend([lng, lat]);
  map.fitBounds(bounds, { padding: 60, maxZoom: 12, duration: 0 });
}
