<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useRouteStore } from '@/stores/route'
import { createMap, drawPolyline, addPOIMarkers, fitBounds, DAY_COLORS, hasMapKey } from '@/utils/qqmap'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: false, breaks: true })

function renderMarkdown(text) {
  if (!text) return ''
  return md.render(text)
}

const router = useRouter()
const store = useRouteStore()

const mapContainer = ref(null)
const mapInstance = ref(null)
const TMapInstance = ref(null)
const mapError = ref(false)
const mapErrorType = ref('') // 'no_key' | 'no_data' | 'init_failed'
const viewMode = ref('map') // 'map' or 'list'
const selectedDay = ref(0)
const sheetExpanded = ref(false)

const route = computed(() => store.currentRoute)
const days = computed(() => route.value?.day_plans || [])

onMounted(async () => {
  // If we just generated a route, it's in the store
  if (!route.value) {
    // Try fetching from server if we have an ID
    const id = router.currentRoute.value.params.id
    if (id && id !== 'latest') {
      await store.fetchRouteDetail(id)
    }
  }

  if (route.value) {
    await nextTick()
    initMap()
  }
})

// Fallback city coordinates (GCJ-02) for when API polyline is unavailable
const CITY_COORDS = {
  '北京': [39.9042, 116.4074], '上海': [31.2304, 121.4737], '广州': [23.1291, 113.2644],
  '深圳': [22.5431, 114.0579], '成都': [30.5728, 104.0668], '重庆': [29.5630, 106.5516],
  '杭州': [30.2741, 120.1551], '南京': [32.0603, 118.7969], '武汉': [30.5928, 114.3055],
  '西安': [34.3416, 108.9398], '沈阳': [41.8057, 123.4315], '长春': [43.8171, 125.3235],
  '哈尔滨': [45.8038, 126.5350], '大连': [38.9140, 121.6147], '承德': [40.9510, 117.9626],
  '漠河': [52.9749, 122.5349], '齐齐哈尔': [47.3540, 123.9183], '呼和浩特': [40.8426, 111.7497],
  '乌鲁木齐': [43.8256, 87.6168], '兰州': [36.0611, 103.8343], '拉萨': [29.6500, 91.1409],
  '昆明': [25.0389, 102.7183], '天津': [39.3434, 117.3616], '青岛': [36.0671, 120.3826],
  '太原': [37.8706, 112.5489], '济南': [36.6512, 117.1201], '郑州': [34.7466, 113.6253],
}

function cityToCoord(name) {
  if (!name) return null
  if (CITY_COORDS[name]) return CITY_COORDS[name]
  for (const [city, coord] of Object.entries(CITY_COORDS)) {
    if (name.includes(city) || city.includes(name)) return coord
  }
  return null
}

async function initMap() {
  if (!hasMapKey()) {
    mapError.value = true
    mapErrorType.value = 'no_key'
    return
  }

  try {
    // Collect all points: prefer polyline, fall back to POI coords, then city coords
    const allPoints = []
    for (const day of days.value) {
      for (const seg of day.segments || []) {
        if (seg.polyline && seg.polyline.length > 0) {
          allPoints.push(...seg.polyline)
        }
      }
      // Also collect POI coordinates
      for (const poi of day.pois || []) {
        if (poi.lat && poi.lng) {
          allPoints.push([poi.lat, poi.lng])
        }
      }
    }

    // If no polyline/POI coords, use departure/destination city coords as fallback
    if (allPoints.length === 0) {
      const dep = route.value?.departure
      const dest = route.value?.destination
      const depCoord = cityToCoord(dep)
      const destCoord = cityToCoord(dest)
      if (depCoord) allPoints.push(depCoord)
      if (destCoord) allPoints.push(destCoord)
    }

    if (allPoints.length === 0) {
      mapError.value = true
      mapErrorType.value = 'no_data'
      return
    }

    const center = allPoints[Math.floor(allPoints.length / 2)]
    const { map, TMap } = await createMap(mapContainer.value, {
      center,
      zoom: 5,
      pitch: 45,
      satellite: false,
    })

    mapInstance.value = map
    TMapInstance.value = TMap

    // Draw polylines for each day (only if available)
    days.value.forEach((day, dayIndex) => {
      for (const seg of day.segments || []) {
        if (seg.polyline && seg.polyline.length > 1) {
          drawPolyline(map, TMap, seg.polyline, DAY_COLORS[dayIndex % DAY_COLORS.length], 5)
        }
      }

      // Add POI markers (use POI coords or city fallback coords)
      const pois = (day.pois || []).map(p => {
        let lat = p.lat
        let lng = p.lng
        // If POI has no coords, try to infer from segment city names
        if ((!lat || !lng) && day.segments?.length > 0) {
          const cityName = day.segments[0].to_name || day.segments[0].from_name
          const coord = cityToCoord(cityName)
          if (coord) { lat = coord[0]; lng = coord[1] }
        }
        return {
          ...p,
          lat: lat || 0,
          lng: lng || 0,
          category: p.category || p.type || 'default',
        }
      }).filter(p => p.lat && p.lng)

      if (pois.length > 0) {
        addPOIMarkers(map, TMap, pois)
      }
    })

    // Fit bounds to show entire route
    fitBounds(map, TMap, allPoints)
  } catch (e) {
    console.error('Map init failed:', e)
    mapError.value = true
    mapErrorType.value = 'init_failed'
  }
}

function selectDay(index) {
  selectedDay.value = index
  sheetExpanded.value = true
}

function toggleSheet() {
  sheetExpanded.value = !sheetExpanded.value
}

function goHome() {
  router.push('/')
}

function formatDistance(km) {
  if (!km) return '0km'
  return km > 100 ? `${Math.round(km)}km` : `${km}km`
}

function formatDuration(hours) {
  if (!hours) return '0h'
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  return m > 0 ? `${h}h${m}m` : `${h}h`
}
</script>

<template>
  <div class="h-screen flex flex-col overflow-hidden">
    <!-- Top bar -->
    <header class="safe-top bg-white/90 backdrop-blur-md border-b border-gray-100 z-20">
      <div class="flex items-center justify-between px-4 py-3">
        <button @click="goHome" class="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center">
          <span class="text-gray-600">←</span>
        </button>
        <div class="flex-1 mx-3 text-center">
          <h1 class="text-sm font-semibold text-gray-800 truncate">{{ route?.title || '路线详情' }}</h1>
          <p class="text-xs text-gray-400">
            {{ route?.departure }} → {{ route?.destination }}
            · {{ formatDistance(route?.total_distance) }}
            · {{ formatDuration(route?.total_duration) }}
          </p>
        </div>
        <button
          @click="viewMode = viewMode === 'map' ? 'list' : 'map'"
          class="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center"
        >
          <span>{{ viewMode === 'map' ? '📋' : '🗺️' }}</span>
        </button>
      </div>

      <!-- Day tabs -->
      <div class="flex gap-1.5 px-4 pb-2 overflow-x-auto no-scrollbar">
        <button
          v-for="(day, index) in days"
          :key="index"
          @click="selectDay(index)"
          :class="[
            'flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
            selectedDay === index
              ? 'text-white'
              : 'bg-gray-100 text-gray-500'
          ]"
          :style="selectedDay === index ? { backgroundColor: DAY_COLORS[index % DAY_COLORS.length] } : {}"
        >
          Day {{ day.day_number }}
        </button>
      </div>
    </header>

    <!-- Map view -->
    <div v-if="viewMode === 'map'" class="flex-1 relative">
      <div ref="mapContainer" class="absolute inset-0 map-container"></div>

      <!-- Map error / placeholder -->
      <div v-if="mapError" class="absolute inset-0 flex flex-col items-center justify-center bg-cream p-8">
        <template v-if="mapErrorType === 'no_key'">
          <span class="text-4xl mb-3">🗺️</span>
          <p class="text-sm text-gray-500 text-center mb-2">地图可视化需要配置腾讯地图 Key</p>
          <p class="text-xs text-gray-400 text-center">请在 .env 中设置 VITE_QQ_MAP_JS_KEY</p>
        </template>
        <template v-else-if="mapErrorType === 'no_data'">
          <span class="text-4xl mb-3">📍</span>
          <p class="text-sm text-gray-500 text-center mb-2">暂无地图坐标数据</p>
          <p class="text-xs text-gray-400 text-center">路线生成时地图API配额可能已用尽，请切换列表模式查看行程</p>
        </template>
        <template v-else>
          <span class="text-4xl mb-3">⚠️</span>
          <p class="text-sm text-gray-500 text-center mb-2">地图加载失败</p>
          <p class="text-xs text-gray-400 text-center">请检查网络连接后重试，或切换列表模式</p>
        </template>
      </div>
    </div>

    <!-- List view -->
    <div v-else class="flex-1 overflow-y-auto px-4 py-3">
      <div v-for="(day, index) in days" :key="index" class="mb-4">
        <div
          class="card mb-2"
          :style="{ borderLeft: `4px solid ${DAY_COLORS[index % DAY_COLORS.length]}` }"
        >
          <div class="flex items-center justify-between mb-1">
            <h3 class="font-bold text-gray-800">Day {{ day.day_number }}</h3>
            <span class="text-xs text-gray-400">{{ formatDistance(day.day_distance) }} · {{ formatDuration(day.day_duration) }}</span>
          </div>
          <p v-if="day.theme" class="text-sm text-nature-600 font-medium">{{ day.theme }}</p>
          <p v-if="day.scenery_description" class="text-xs text-gray-500 mt-1">{{ day.scenery_description }}</p>
        </div>
      </div>
    </div>

    <!-- Bottom sheet (day detail) -->
    <div
      :class="[
        'bg-white rounded-t-3xl shadow-2xl transition-all duration-300 z-30',
        sheetExpanded ? 'h-[75%]' : 'h-[20%]'
      ]"
      style="overflow-y: auto;"
    >
      <!-- Drag handle -->
      <div @click="toggleSheet" class="flex justify-center py-2 cursor-pointer">
        <div class="w-10 h-1 rounded-full bg-gray-300"></div>
      </div>

      <!-- Day content -->
      <div v-if="days[selectedDay]" class="px-4 pb-8 safe-bottom">
        <!-- Day header -->
        <div class="mb-4">
          <div class="flex items-baseline justify-between">
            <h2 class="text-lg font-bold text-gray-800">
              Day {{ days[selectedDay].day_number }}
            </h2>
            <span class="text-sm text-gray-400">
              {{ formatDistance(days[selectedDay].day_distance) }} · {{ formatDuration(days[selectedDay].day_duration) }}
            </span>
          </div>
          <p v-if="days[selectedDay].theme" class="text-nature-600 font-medium mt-0.5">
            {{ days[selectedDay].theme }}
          </p>
        </div>

        <!-- Weather advisory -->
        <div v-if="days[selectedDay].weather_advisory" class="bg-sky-50 rounded-xl p-3 mb-3">
          <p class="text-xs text-sky-600 font-medium mb-1">🌤️ 天气建议</p>
          <p class="text-xs text-gray-600 whitespace-pre-line">{{ days[selectedDay].weather_advisory }}</p>
        </div>

        <!-- Scenery description -->
        <div v-if="days[selectedDay].scenery_description" class="mb-3">
          <p class="text-xs text-gray-400 font-medium mb-1">🌲 沿路风景</p>
          <p class="text-sm text-gray-600">{{ days[selectedDay].scenery_description }}</p>
        </div>

        <!-- Terrain note -->
        <div v-if="days[selectedDay].terrain_note" class="bg-amber-50 rounded-xl p-3 mb-3">
          <p class="text-xs text-amber-600 font-medium mb-1">🛣️ 路况说明</p>
          <p class="text-xs text-gray-600">{{ days[selectedDay].terrain_note }}</p>
        </div>

        <!-- Route segments -->
        <div v-if="days[selectedDay].segments?.length" class="mb-4">
          <p class="text-xs text-gray-400 font-medium mb-2">📍 行程路线</p>
          <div class="flex items-center gap-1 text-xs text-gray-500 flex-wrap">
            <template v-for="(seg, si) in days[selectedDay].segments" :key="si">
              <span class="font-medium text-gray-700">{{ seg.from_name }}</span>
              <span class="text-nature-500 mx-1">→</span>
              <span v-if="si === days[selectedDay].segments.length - 1" class="font-medium text-gray-700">{{ seg.to_name }}</span>
              <span v-else class="font-medium text-gray-700">{{ seg.to_name }}</span>
              <span v-if="si < days[selectedDay].segments.length - 1" class="text-nature-500 mx-1">→</span>
            </template>
          </div>
        </div>

        <!-- POIs -->
        <div v-if="days[selectedDay].pois?.length" class="mb-4">
          <p class="text-xs text-gray-400 font-medium mb-2">🎯 特色景点</p>
          <div class="space-y-2">
            <div v-for="poi in days[selectedDay].pois" :key="poi.id" class="card p-3">
              <div class="flex gap-3">
                <img v-if="poi.image_url" :src="poi.image_url" class="w-16 h-16 rounded-lg object-cover flex-shrink-0" />
                <div v-else class="w-16 h-16 rounded-lg bg-nature-50 flex items-center justify-center flex-shrink-0">
                  <span class="text-2xl">🏔️</span>
                </div>
                <div class="flex-1 min-w-0">
                  <h4 class="font-semibold text-sm text-gray-800">{{ poi.name }}</h4>
                  <p v-if="poi.feature" class="text-xs text-nature-600 mt-0.5">{{ poi.feature }}</p>
                  <p v-if="poi.anecdote" class="text-xs text-gray-400 mt-1">{{ poi.anecdote }}</p>
                  <div class="flex items-center gap-2 mt-1">
                    <span v-if="poi.duration_minutes" class="text-xs text-gray-400">⏱ {{ poi.duration_minutes }}分钟</span>
                  </div>
                </div>
              </div>
              <!-- Douyin link -->
              <a
                v-if="poi.douyin_links?.length"
                :href="poi.douyin_links[0].search_url"
                target="_blank"
                class="mt-2 inline-flex items-center gap-1 text-xs text-warm-500 font-medium"
              >
                🎬 {{ poi.douyin_links[0].label }}
              </a>
            </div>
          </div>
        </div>

        <!-- Meals -->
        <div v-if="days[selectedDay].meals?.length" class="mb-4">
          <p class="text-xs text-gray-400 font-medium mb-2">🍽️ 地方美食</p>
          <div class="space-y-2">
            <div v-for="meal in days[selectedDay].meals" :key="meal.id" class="card p-3">
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center gap-2">
                    <span class="text-xs">{{ meal.type === 'breakfast' ? '🌅' : meal.type === 'lunch' ? '☀️' : '🌙' }}</span>
                    <h4 class="font-semibold text-sm text-gray-800">{{ meal.restaurant_name }}</h4>
                    <span v-if="meal.is_local_specialty" class="tag tag-warm text-xs">特色</span>
                  </div>
                  <p v-if="meal.cuisine_type" class="text-xs text-gray-400 mt-0.5">{{ meal.cuisine_type }}</p>
                  <p v-if="meal.story" class="text-xs text-gray-500 mt-1">{{ meal.story }}</p>
                </div>
                <span class="text-xs text-gray-400">¥{{ meal.cost_per_person }}/人</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Hotels -->
        <div v-if="days[selectedDay].hotels?.length" class="mb-4">
          <p class="text-xs text-gray-400 font-medium mb-2">🏨 推荐住宿</p>
          <div v-for="hotel in days[selectedDay].hotels" :key="hotel.id" class="card p-3 mb-2">
            <div class="flex items-start justify-between">
              <div>
                <h4 class="font-semibold text-sm text-gray-800">{{ hotel.name }}</h4>
                <p v-if="hotel.address" class="text-xs text-gray-400 mt-0.5">📍 {{ hotel.address }}</p>
              </div>
              <div class="text-right">
                <span class="text-sm font-bold text-warm-500">¥{{ hotel.price_per_night }}</span>
                <span class="text-xs text-gray-400">/晚</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Overall tips (markdown) -->
        <div v-if="route?.overall_tips" class="mb-4">
          <p class="text-xs text-gray-400 font-medium mb-2">💡 出行建议</p>
          <div class="card p-3 prose prose-xs max-w-none text-gray-600" v-html="renderMarkdown(route.overall_tips)"></div>
        </div>
      </div>
    </div>
  </div>
</template>
