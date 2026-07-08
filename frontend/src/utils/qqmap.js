/**
 * Tencent Maps JS API GL loader and helpers.
 *
 * Docs: https://lbs.qq.com/service/webService/webServiceGuide/webServiceOverview
 * GL version supports 3D perspective, satellite layer, custom markers.
 * Note: GL does NOT support terrain elevation - we use 3D pitch + satellite for off-road feel.
 */

const QQ_MAP_JS_KEY = import.meta.env.VITE_QQ_MAP_JS_KEY || ''

let mapLoadingPromise = null

export function hasMapKey() {
  return !!QQ_MAP_JS_KEY
}

export function loadTMap() {
  if (typeof window.TMap !== 'undefined') return Promise.resolve(window.TMap)
  if (mapLoadingPromise) return mapLoadingPromise

  if (!hasMapKey()) {
    return Promise.reject(new Error('VITE_QQ_MAP_JS_KEY not configured'))
  }

  mapLoadingPromise = new Promise((resolve, reject) => {
    const callbackName = '__qq_map_callback_' + Date.now()
    window[callbackName] = () => {
      delete window[callbackName]
      resolve(window.TMap)
    }

    const script = document.createElement('script')
    script.src = `https://map.qq.com/api/gljs?v=1.exp&key=${QQ_MAP_JS_KEY}&callback=${callbackName}`
    script.async = true
    script.onerror = () => {
      delete window[callbackName]
      mapLoadingPromise = null
      reject(new Error('腾讯地图加载失败'))
    }
    document.head.appendChild(script)
  })

  return mapLoadingPromise
}

// Day colors for polylines
export const DAY_COLORS = [
  '#2D9D5F', // Day 1 - nature green
  '#3B9AE1', // Day 2 - sky blue
  '#FF8C42', // Day 3 - warm orange
  '#8B5CF6', // Day 4 - purple
  '#EF4444', // Day 5 - red
  '#14B8A6', // Day 6 - teal
  '#F59E0B', // Day 7 - amber
]

// POI category icons and colors
export const POI_ICONS = {
  scenic: '🏔️',
  nature: '🌲',
  history: '🏛️',
  food: '🍽️',
  viewpoint: '📸',
  gas_station: '⛽',
  hotel: '🏨',
  waypoint: '📍',
  default: '📍',
}

export const POI_COLORS = {
  scenic: '#2D9D5F',
  nature: '#16a34a',
  history: '#8B5CF6',
  food: '#FF8C42',
  viewpoint: '#3B9AE1',
  gas_station: '#EF4444',
  hotel: '#6366f1',
  waypoint: '#94a3b8',
  default: '#94a3b8',
}

/**
 * Create a Tencent Map instance with 3D perspective.
 * @param {string} containerId - DOM element id
 * @param {Object} options - { center: [lat, lng], zoom, pitch, satellite }
 */
export async function createMap(containerId, options = {}) {
  const TMap = await loadTMap()
  const { center = [39.9, 116.4], zoom = 6, pitch = 45, satellite = false } = options

  const mapOptions = {
    center: new TMap.LatLng(center[0], center[1]),
    zoom,
    pitch,
    rotation: 0,
    viewMode: '3D',
  }

  // Use satellite base map if requested
  if (satellite) {
    mapOptions.baseMap = new TMap.SatelliteBaseMap({
      features: ['base', 'road'],
    })
  }

  const map = new TMap.Map(containerId, mapOptions)
  return { map, TMap }
}

/**
 * Draw a polyline on the map for a day's route.
 * @param {TMap.Map} map
 * @param {TMap} TMap
 * @param {Array} polyline - [[lat,lng], [lat,lng], ...]
 * @param {string} color - stroke color
 * @param {number} width - stroke width
 */
export function drawPolyline(map, TMap, polyline, color = '#2D9D5F', width = 6) {
  if (!polyline || polyline.length < 2) return null

  // Filter out invalid coordinate pairs (missing lat/lng)
  const validPath = polyline
    .filter(p => Array.isArray(p) && p.length >= 2 && p[0] && p[1])
    .map(([lat, lng]) => new TMap.LatLng(lat, lng))

  if (validPath.length < 2) return null

  const polylineLayer = new TMap.MultiPolyline({
    map,
    styles: {
      default: new TMap.PolylineStyle({
        color,
        width,
        borderWidth: 1,
        borderColor: '#ffffff',
        lineCap: 'round',
      }),
    },
    geometries: [
      {
        id: 'route',
        styleId: 'default',
        positions: validPath,
      },
    ],
  })

  return polylineLayer
}

/**
 * Add POI markers to the map.
 * @param {TMap.Map} map
 * @param {TMap} TMap
 * @param {Array} pois - [{ name, lat, lng, category, ... }]
 */
export function addPOIMarkers(map, TMap, pois) {
  if (!pois || pois.length === 0) return null

  const geometries = pois.map((poi, index) => {
    const color = POI_COLORS[poi.category] || POI_COLORS.default
    return {
      id: `poi_${index}`,
      styleId: poi.category || 'default',
      position: new TMap.LatLng(poi.lat, poi.lng),
      properties: poi,
    }
  })

  // Build styles for each category
  const styles = {}
  for (const cat of Object.keys(POI_COLORS)) {
    const icon = POI_ICONS[cat] || POI_ICONS.default
    const color = POI_COLORS[cat]
    styles[cat] = new TMap.MarkerStyle({
      width: 32,
      height: 32,
      anchor: { x: 16, y: 16 },
      color,
      src: createMarkerIcon(icon, color),
    })
  }

  const markerLayer = new TMap.MultiMarker({
    map,
    styles,
    geometries,
  })

  return markerLayer
}

/**
 * Create a data URI marker icon with emoji.
 * Uses encodeURIComponent instead of btoa to support Unicode emoji characters.
 */
function createMarkerIcon(emoji, bgColor) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
    <circle cx="16" cy="16" r="14" fill="${bgColor}" stroke="white" stroke-width="2"/>
    <text x="16" y="22" font-size="16" text-anchor="middle">${emoji}</text>
  </svg>`
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)
}

/**
 * Fit map bounds to show all points.
 */
export function fitBounds(map, TMap, points) {
  if (!points || points.length === 0) return

  const bounds = new TMap.LatLngBounds()
  for (const [lat, lng] of points) {
    bounds.extend(new TMap.LatLng(lat, lng))
  }
  map.fitBounds(bounds, { padding: 60 })
}
