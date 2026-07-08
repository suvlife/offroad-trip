<script setup>
import { onMounted, computed } from 'vue'
import { useRouteStore } from '@/stores/route'

const props = defineProps({ shareId: String })
const store = useRouteStore()

onMounted(async () => {
  await store.fetchShareData(props.shareId)
})

const route = computed(() => store.currentRoute)
</script>

<template>
  <div class="min-h-screen safe-top safe-bottom">
    <div v-if="store.loading" class="flex flex-col items-center justify-center min-h-screen">
      <div class="w-10 h-10 border-3 border-nature-500 border-t-transparent rounded-full animate-spin mb-4"></div>
      <p class="text-sm text-gray-400">加载路线中...</p>
    </div>

    <div v-else-if="!route" class="flex flex-col items-center justify-center min-h-screen px-8">
      <span class="text-4xl mb-3">😕</span>
      <p class="text-gray-500 text-center">分享链接无效或已过期</p>
    </div>

    <div v-else class="pb-8">
      <!-- Hero -->
      <div class="gradient-nature text-white px-5 pt-12 pb-8 safe-top">
        <p class="text-xs text-white/70 mb-1">越野智行 · 路线分享</p>
        <h1 class="text-2xl font-bold mb-2">{{ route.title }}</h1>
        <p class="text-sm text-white/80">
          {{ route.departure }} -> {{ route.destination }}
          · {{ Math.round(route.total_distance) }}km
          · {{ route.days || route.day_plans?.length }}天
        </p>
        <div class="flex gap-2 mt-3">
          <span class="tag bg-white/20 text-white">{{ route.trip_type }}</span>
          <span class="tag bg-white/20 text-white">{{ route.vehicle_type }}</span>
          <span class="tag bg-white/20 text-white">越野难度 {{ route.terrain_difficulty }}/5</span>
        </div>
      </div>

      <!-- Overall tips -->
      <div v-if="route.overall_tips" class="px-5 mt-5">
        <div class="card">
          <p class="text-xs text-gray-400 font-medium mb-2">💡 整体游玩建议</p>
          <p class="text-sm text-gray-600 whitespace-pre-line">{{ route.overall_tips }}</p>
        </div>
      </div>

      <!-- Story cards -->
      <div v-if="route.story_cards?.length" class="px-5 mt-5">
        <p class="text-xs text-gray-400 font-medium mb-2">📖 历史人文</p>
        <div class="space-y-2">
          <div v-for="story in route.story_cards" :key="story.id" class="card">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-lg">🏛️</span>
              <h4 v-if="story.figure" class="font-semibold text-sm text-gray-800">{{ story.figure }}</h4>
              <h4 v-else-if="story.event" class="font-semibold text-sm text-gray-800">{{ story.event }}</h4>
            </div>
            <p v-if="story.anecdote" class="text-xs text-warm-500 font-medium mb-1">{{ story.anecdote }}</p>
            <p class="text-sm text-gray-600">{{ story.story_text }}</p>
          </div>
        </div>
      </div>

      <!-- Day summaries -->
      <div class="px-5 mt-5 space-y-3">
        <div v-for="day in route.day_plans" :key="day.id" class="card"
          :style="{ borderLeft: '4px solid #2D9D5F' }"
        >
          <div class="flex items-baseline justify-between mb-1">
            <h3 class="font-bold text-gray-800">Day {{ day.day_number }} · {{ day.theme }}</h3>
            <span class="text-xs text-gray-400">{{ Math.round(day.day_distance) }}km</span>
          </div>
          <p v-if="day.scenery_description" class="text-xs text-gray-500 mt-1">{{ day.scenery_description }}</p>
          <div class="flex gap-1 mt-2 flex-wrap">
            <span v-for="poi in day.pois?.slice(0, 4)" :key="poi.id" class="tag tag-nature">{{ poi.name }}</span>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-5 mt-8 text-center">
        <a href="/" class="inline-block btn-outline">规划我的越野路线</a>
      </div>
    </div>
  </div>
</template>
