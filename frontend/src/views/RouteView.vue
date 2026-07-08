<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useRouteStore } from '@/stores/route'
import { createMap, drawPolyline, addPOIMarkers, fitBounds, DAY_COLORS, hasMapKey } from '@/utils/qqmap'

const router = useRouter()
const store = useRouteStore()

const mapContainer = ref(null)
const mapInstance = ref(null)
const TMapInstance = ref(null)
const mapError = ref(false)
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

async function initMap() {
  if (!hasMapKey()) {
    mapError.value = true
    return
  }

  try {
    // Collect all points for initial bounds
    const allPoints = []
    for (const day of days.value) {
      for (const seg of day.segments || []) {
        if (seg.polyline) {
          allPoints.push(...seg.polyline)
        }
      }
    }

    if (allPoints.length === 0) {
      mapError.value = true
      return
    }

    const center = allPoints[Math.floor(allPoints.length / 2)]
    const { map, TMap } = await createMap(mapContainer.value, {
      center,
      zoom: 6,
      pitch: 45,
      satellite: false,
    })

    mapInstance.value = map
    TMapInstance.value = TMap

    // Draw polylines for each day
    days.value.forEach((day, dayIndex) => {
      for (const seg of day.segments || []) {
        if (seg.polyline && seg.polyline.length > 1) {
          drawPolyline(map, TMap, seg.polyline, DAY_COLORS[dayIndex % DAY_COLORS.length], 5)
        }
      }

      // Add POI markers
      const pois = (day.pois || []).map(p => ({
        ...p,
        category: p.category || p.type || 'default',
      }))
      if (pois.length > 0) {
        addPOIMarkers(map, TMap, pois)
      }
    })

    // Fit bounds to show entire route
    fitBounds(map, TMap, allPoints)
  } catch (e) {
    console.error('Map init failed:', e)
    mapError.value = true
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
        <span class="text-4xl mb-3">🗺️</span>
        <p class="text-sm text-gray-500 text-center mb-2">地图可视化需要配置腾讯地图 Key</p>
        <p class="text-xs text-gray-400 text-center">请在 .env 中设置 VITE_QQ_MAP_JS_KEY</p>
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
      </div>
    </div>
  </div>
</template>
