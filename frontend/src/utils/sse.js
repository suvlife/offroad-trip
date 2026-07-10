/**
 * SSE client for the agent pipeline (Cloudflare Workers backend).
 *
 * Two-step flow:
 *   1. POST /api/generate  -> { instanceId }   (starts a Workflow)
 *   2. GET  /api/stream/:instanceId (SSE)       -> progress events + final route
 *
 * The final event carries the persisted route (with its DB `id`), so callers get
 * an id directly — no follow-up list fetch needed.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function streamRouteGeneration(payload, callbacks = {}) {
  const { onStage = () => {}, onComplete = () => {}, onError = () => {} } = callbacks;

  try {
    // Step 1: start the workflow
    const startResp = await fetch(`${API_BASE}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!startResp.ok) {
      let msg = `HTTP ${startResp.status}`;
      try {
        const j = await startResp.json();
        msg = j.error || j.detail || msg;
      } catch {}
      throw new Error(msg);
    }
    const { instanceId } = await startResp.json();
    if (!instanceId) throw new Error("未能启动规划任务");

    // Step 2: subscribe to progress via SSE
    const streamResp = await fetch(`${API_BASE}/api/stream/${instanceId}`, {
      headers: { Accept: "text/event-stream" },
    });
    if (!streamResp.ok) throw new Error(`HTTP ${streamResp.status}`);

    const reader = streamResp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalRoute = null;
    let finalError = null;

    const handleData = (dataStr) => {
      const data = JSON.parse(dataStr);
      if (data.stage && data.status) onStage(data);
      if (data.route !== undefined || data.error) {
        if (data.error && !data.route) finalError = data.error;
        else if (data.route) finalRoute = data.route;
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      while (true) {
        const idx = buffer.indexOf("\n\n");
        if (idx === -1) break;
        const eventStr = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        if (!eventStr.trim().startsWith("data:")) continue;
        const dataStr = eventStr.replace(/^data:\s*/m, "").trim();
        try {
          handleData(dataStr);
        } catch (e) {
          // Large final payload may be split across chunks — re-buffer and wait.
          buffer = eventStr + "\n\n" + buffer;
          break;
        }
      }
    }

    // Flush any trailing event
    const rest = buffer.trim();
    if (rest.startsWith("data:")) {
      try {
        handleData(rest.replace(/^data:\s*/m, "").trim());
      } catch {}
    }

    if (finalError) onError(finalError);
    else if (finalRoute) onComplete(finalRoute);
    else onError("未收到路线数据");
  } catch (err) {
    onError(err.message || "连接失败，请重试");
  }
}

// Stage metadata for UI display (unchanged).
export const STAGES = [
  { id: "geocode", label: "定位出发地", icon: "📍" },
  { id: "weather", label: "获取沿途天气", icon: "🌤️" },
  { id: "planning", label: "AI规划越野路线", icon: "🗺️" },
  { id: "routing", label: "获取详细路况", icon: "🛣️" },
  { id: "enrichment", label: "丰富景点美食故事", icon: "✨" },
  { id: "assembly", label: "组装图片和视频", icon: "📸" },
];
