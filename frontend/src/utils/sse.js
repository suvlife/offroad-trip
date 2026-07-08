/**
 * SSE client for the agent pipeline.
 * Uses fetch + ReadableStream to handle POST with SSE (EventSource only supports GET).
 *
 * Handles large final JSON payloads that may be split across multiple network chunks.
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
    let finalRoute = null
    let finalError = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Process complete SSE events (separated by \n\n)
      // We need to handle the case where a large JSON payload is split
      // across multiple chunks - only process events that are complete.
      while (true) {
        const idx = buffer.indexOf('\n\n')
        if (idx === -1) break // no complete event yet, wait for more data

        const eventStr = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2) // skip past \n\n

        if (!eventStr.trim().startsWith('data:')) continue

        // Extract data after "data: " prefix
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
              finalError = data.error
            } else {
              finalRoute = data.route
            }
          }
        } catch (e) {
          // JSON parse failed - this event might be incomplete
          // (large payload split across chunks)
          // Put it back in the buffer and wait for more data
          console.warn('SSE event parse failed, buffering for more data...', dataStr.substring(0, 100))
          buffer = eventStr + '\n\n' + buffer
          break
        }
      }
    }

    // Process any remaining data in buffer after stream ends
    buffer = buffer.trim()
    if (buffer.startsWith('data:')) {
      const dataStr = buffer.replace(/^data:\s*/m, '').trim()
      try {
        const data = JSON.parse(dataStr)
        if (data.route !== undefined || data.error) {
          if (data.error && !data.route) {
            finalError = data.error
          } else {
            finalRoute = data.route
          }
        }
      } catch (e) {
        console.error('Failed to parse final SSE event:', e)
        console.error('Raw data (first 200 chars):', dataStr.substring(0, 200))
        console.error('Raw data (last 200 chars):', dataStr.substring(dataStr.length - 200))
      }
    }

    // Fire final callback
    if (finalError) {
      onError(finalError)
    } else if (finalRoute) {
      onComplete(finalRoute)
    } else {
      onError('未收到路线数据')
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
