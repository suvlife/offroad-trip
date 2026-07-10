<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useRouteStore } from '@/stores/route'
import { api } from '@/api'
import { STAGES } from '@/utils/sse'

const router = useRouter()
const store = useRouteStore()

onMounted(async () => {
  // If no departure set, go back home
  if (!store.formState.departure || !store.formState.destination) {
    router.replace('/')
    return
  }

  const route = await store.generateRoute()

  if (route) {
    // Fetch the route list to get the actual ID (saved to DB after SSE completes)
    try {
      const response = await api.getRoutes({ page: 1, page_size: 1 })
      const routes = response.data
      if (routes?.length > 0) {
        // The most recent route should be the one we just generated
        const actualId = routes[0].id
        setTimeout(() => {
          router.replace({ name: 'route-detail', params: { id: actualId } })
        }, 800)
        return
      }
    } catch (e) {
      console.warn('Failed to fetch route list:', e)
    }
    // Fallback: navigate with latest (will try to load from store)
    setTimeout(() => {
      router.replace({ name: 'route-detail', params: { id: 'latest' } })
    }, 800)
  }
})

const currentStageIndex = computed(() => {
  if (!store.currentStage) return -1
  return STAGES.findIndex(s => s.id === store.currentStage)
})

const overallProgress = computed(() => store.stageProgress)
</script>

<template>
  <div class="min-h-screen gradient-hero safe-top flex flex-col">
    <!-- Header -->
    <header class="px-5 pt-8 pb-4">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-2xl">🏔️</span>
        <h1 class="text-xl font-bold text-nature-700">正在规划路线</h1>
      </div>
      <p class="text-sm text-gray-500">
        {{ store.formState.departure }} → {{ store.formState.destination }}
      </p>
    </header>

    <!-- Progress display -->
    <div class="flex-1 px-5 flex flex-col justify-center">
      <!-- Overall progress circle -->
      <div class="flex flex-col items-center mb-8">
        <div class="relative w-32 h-32 mb-4">
          <svg class="w-full h-full -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" stroke="#dcfce7" stroke-width="10" fill="none" />
            <circle
              cx="60" cy="60" r="52"
              stroke="#2D9D5F" stroke-width="10" fill="none"
              stroke-linecap="round"
              :stroke-dasharray="326.7"
              :stroke-dashoffset="326.7 - (326.7 * overallProgress / 100)"
              class="transition-all duration-500"
            />
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            <span class="text-3xl font-bold text-nature-600">{{ overallProgress }}%</span>
          </div>
        </div>
        <p class="text-sm text-gray-600 font-medium">{{ store.stageMessage || '准备中...' }}</p>
      </div>

      <!-- Stage list -->
      <div class="space-y-3">
        <div
          v-for="(stage, index) in STAGES"
          :key="stage.id"
          :class="[
            'flex items-center gap-3 p-3 rounded-xl transition-all',
            index < currentStageIndex ? 'bg-nature-50' :
            index === currentStageIndex ? 'bg-white shadow-sm ring-2 ring-nature-500/20' :
            'opacity-40'
          ]"
        >
          <!-- Status icon -->
          <div class="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
            :class="index < currentStageIndex ? 'bg-nature-500 text-white' :
                    index === currentStageIndex ? 'bg-nature-100 text-nature-600 animate-pulse-slow' :
                    'bg-gray-100 text-gray-400'"
          >
            <span v-if="index < currentStageIndex">✓</span>
            <span v-else>{{ stage.icon }}</span>
          </div>

          <!-- Label -->
          <div class="flex-1">
            <div class="text-sm font-medium"
              :class="index <= currentStageIndex ? 'text-gray-800' : 'text-gray-400'"
            >
              {{ stage.label }}
            </div>
          </div>

          <!-- Spinner for current -->
          <div v-if="index === currentStageIndex" class="w-5 h-5 border-2 border-nature-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      </div>

      <!-- Error -->
      <div v-if="store.error" class="mt-6 p-4 bg-red-50 rounded-xl text-center">
        <p class="text-red-600 text-sm font-medium mb-2">❌ {{ store.error }}</p>
        <button @click="router.replace('/')" class="text-sm text-nature-600 font-medium">
          返回重新规划
        </button>
      </div>
    </div>

    <!-- Cancel -->
    <div class="px-5 pb-8 safe-bottom">
      <button
        v-if="store.loading"
        @click="router.replace('/')"
        class="w-full text-center text-sm text-gray-400 py-2"
      >
        取消规划
      </button>
    </div>
  </div>
</template>
