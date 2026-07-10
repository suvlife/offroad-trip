/**
 * ProgressCoordinator Durable Object.
 *
 * Bridges the async Workflow (which pushes progress events) and the client's SSE
 * stream (which subscribes). One DO instance per workflow run (keyed by instanceId).
 *
 * - Workflow POSTs events to /emit; they are buffered and fanned out to any open
 *   SSE readers.
 * - Client opens GET /sse and receives buffered + live events until the "done"
 *   (progress=100) or "error" event, then the stream closes.
 */

import type { ProgressEvent } from "./types";

export class ProgressCoordinator {
  private state: DurableObjectState;
  private buffer: ProgressEvent[] = [];
  private writers = new Set<WritableStreamDefaultWriter>();
  private finished = false;
  private encoder = new TextEncoder();

  constructor(state: DurableObjectState) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname.endsWith("/emit") && request.method === "POST") {
      const event = (await request.json()) as ProgressEvent;
      this.buffer.push(event);
      const chunk = this.encoder.encode(`data: ${JSON.stringify(event)}\n\n`);
      for (const w of this.writers) {
        w.write(chunk).catch(() => this.writers.delete(w));
      }
      if (event.progress >= 100 || event.status === "error") {
        this.finished = true;
        for (const w of this.writers) w.close().catch(() => {});
        this.writers.clear();
      }
      return new Response("ok");
    }

    if (url.pathname.endsWith("/sse")) {
      const { readable, writable } = new TransformStream();
      const writer = writable.getWriter();

      // Replay buffered events so a late subscriber catches up.
      for (const event of this.buffer) {
        writer.write(this.encoder.encode(`data: ${JSON.stringify(event)}\n\n`)).catch(() => {});
      }

      if (this.finished) {
        writer.close().catch(() => {});
      } else {
        this.writers.add(writer);
      }

      return new Response(readable, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
          "X-Accel-Buffering": "no",
        },
      });
    }

    return new Response("not found", { status: 404 });
  }
}
