import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import { streamRouteGeneration } from '@/utils/sse'

export const useRouteStore = defineStore('route', () => {
  // ── Form state ──────────────────────────────────────
  const formState = ref({
    departure: '',
    destination: '',
    startDate: '',
    days: 7,
    tripType: '越野自驾',
    adults: 2,
    children: 0,
    vehicleType: 'SUV',
    budget: 10000,
    theme: '回归自然',
    preferences: ['自然风光', '地方美食', '人文历史'],
  })

  // ── Generation state ────────────────────────────────
  const currentRoute = ref(null)
  const loading = ref(false)
  const currentStage = ref(null)
  const stageProgress = ref(0)
  const stageMessage = ref('')
  const error = ref(null)

  // ── Public routes list ──────────────────────────────
  const publicRoutes = ref([])

  // ── Computed ────────────────────────────────────────
  const totalCost = computed(() => {
    if (!currentRoute.value?.cost_breakdown) return 0
    return currentRoute.value.cost_breakdown.total || 0
  })

  // ── Form persistence ────────────────────────────────
  function saveForm() {
    try {
      localStorage.setItem('offroadtrip_form', JSON.stringify(formState.value))
    } catch (e) {
      console.warn('Failed to save form:', e)
    }
  }

  function loadForm() {
    try {
      const saved = localStorage.getItem('offroadtrip_form')
      if (saved) {
        formState.value = { ...formState.value, ...JSON.parse(saved) }
      }
    } catch (e) {
      console.warn('Failed to load form:', e)
    }
  }

  function updateField(field, value) {
    formState.value[field] = value
    saveForm()
  }

  // ── Generate route via SSE ──────────────────────────
  async function generateRoute() {
    loading.value = true
    error.value = null
    currentRoute.value = null
    currentStage.value = null
    stageProgress.value = 0
    stageMessage.value = '正在启动...'

    const payload = {
      departure: formState.value.departure,
      destination: formState.value.destination,
      start_date: formState.value.startDate,
      days: formState.value.days,
      trip_type: formState.value.tripType,
      adults: formState.value.adults,
      children: formState.value.children,
      vehicle_type: formState.value.vehicleType,
      budget: formState.value.budget,
      theme: formState.value.theme,
      preferences: formState.value.preferences,
    }

    return new Promise((resolve) => {
      streamRouteGeneration(payload, {
        onStage: (data) => {
          currentStage.value = data.stage
          stageProgress.value = data.progress
          stageMessage.value = data.message
        },
        onComplete: (route) => {
          currentRoute.value = route
          loading.value = false
          resolve(route)
        },
        onError: (errMsg) => {
          error.value = errMsg
          loading.value = false
          resolve(null)
        },
      })
    })
  }

  // ── Fetch route detail ──────────────────────────────
  async function fetchRouteDetail(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.getRoute(id)
      currentRoute.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message || '获取路线详情失败'
      return null
    } finally {
      loading.value = false
    }
  }

  // ── Fetch share data ────────────────────────────────
  async function fetchShareData(shareId) {
    loading.value = true
    try {
      const response = await api.getShareData(shareId)
      currentRoute.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message || '获取分享数据失败'
      return null
    } finally {
      loading.value = false
    }
  }

  // ── Fetch public routes ─────────────────────────────
  async function fetchPublicRoutes() {
    try {
      const response = await api.getRoutes()
      publicRoutes.value = response.data
      return response.data
    } catch (err) {
      console.error('Failed to fetch routes:', err)
      return []
    }
  }

  return {
    formState,
    currentRoute,
    loading,
    currentStage,
    stageProgress,
    stageMessage,
    error,
    publicRoutes,
    totalCost,
    saveForm,
    loadForm,
    updateField,
    generateRoute,
    fetchRouteDetail,
    fetchShareData,
    fetchPublicRoutes,
  }
})
