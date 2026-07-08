import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 180000, // 3 min for AI generation
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      const message = data?.detail || data?.message || `请求失败 (${status})`
      return Promise.reject(new Error(message))
    }
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('请求超时，请重试'))
    }
    return Promise.reject(error)
  }
)

export const api = {
  // Generate route (returns EventSource for SSE)
  generateRouteUrl() {
    return `${API_BASE}/api/generate`
  },

  // List routes
  getRoutes(params) {
    return apiClient.get('/api/routes', { params })
  },

  // Get route detail
  getRoute(id) {
    return apiClient.get(`/api/routes/${id}`)
  },

  // Share a route
  shareRoute(id) {
    return apiClient.post(`/api/routes/${id}/share`)
  },

  // Get share data
  getShareData(shareId) {
    return apiClient.get(`/api/share/${shareId}`)
  },

  // City search (autocomplete)
  searchCities(query) {
    return apiClient.get('/api/cities', { params: { q: query } })
  },

  // Get weather
  getWeather(city, days = 7) {
    return apiClient.get('/api/weather', { params: { city, days } })
  },
}

export default api
