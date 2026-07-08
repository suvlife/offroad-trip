/**
 * SSE client for the agent pipeline.
 * Uses fetch + ReadableStream to handle POST with SSE (EventSource only supports GET).
 */

export async function streamRouteGeneration(payload, callbacks = {}) {
  const {
    onStage = () => {},
    onComplete = () => {},
    onError = () => {},
  } = callbacks

  const url = import.meta.env.VITE_API_BASE_URL
    ? `${import.meta.env.VITE_API_BASE_URL}/api/generate`
    : '/api/generate'

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Process complete SSE events (separated by \n\n)
      const events = buffer.split('\n\n')
      buffer = events.pop() // keep incomplete chunk

      for (const eventStr of events) {
        if (!eventStr.trim().startsWith('data:')) continue

        const dataStr = eventStr.replace(/^data:\s*/m, '').trim()
        try {
          const data = JSON.parse(dataStr)

          // Stage progress event
          if (data.stage && data.status) {
            onStage(data)
          }

          // Final complete event (has route or error)
          if (data.route !== undefined || data.error) {
            if (data.error && !data.route) {
              onError(data.error)
            } else {
              onComplete(data.route)
            }
          }
        } catch (e) {
          console.warn('Failed to parse SSE data:', dataStr.substring(0, 100))
        }
      }
    }
  } catch (err) {
    onError(err.message || '连接失败，请重试')
  }
}

// Stage metadata for UI display
export const STAGES = [
  { id: 'geocode', label: '定位出发地', icon: '📍' },
  { id: 'weather', label: '获取沿途天气', icon: '🌤️' },
  { id: 'planning', label: 'AI规划越野路线', icon: '🗺️' },
  { id: 'routing', label: '获取详细路况', icon: '🛣️' },
  { id: 'enrichment', label: '丰富景点美食故事', icon: '✨' },
  { id: 'assembly', label: '组装图片和视频', icon: '📸' },
]
