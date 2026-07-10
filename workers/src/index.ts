/**
 * Worker entry — a single Worker serves both the Vue frontend (Static Assets)
 * and the /api routes (Hono). Same origin, so no CORS.
 *
 * Flow:
 *   POST /api/generate        -> start a Workflow, return { instanceId }
 *   GET  /api/stream/:id      -> SSE progress stream (via ProgressCoordinator DO)
 *   GET  /api/routes          -> list
 *   GET  /api/routes/:id      -> detail (+ view count)
 *   POST /api/routes/:id/share-> publish, return share_id
 *   DELETE /api/routes/:id    -> delete
 *   GET  /api/share/:shareId  -> public read-only
 *   GET  /api/weather?city=&days=
 *   (anything else)           -> static assets (SPA fallback to index.html)
 */

import { Hono } from "hono";
import type { Env, GenerateRequest } from "./types";
import * as db from "./db";
import { getWeather } from "./services/weather";

export { OffroadTripWorkflow } from "./workflow";
export { ProgressCoordinator } from "./progress-do";

const app = new Hono<{ Bindings: Env }>();

app.get("/api/health", (c) => c.json({ status: "ok", app: "OffroadTrip" }));

// Start generation → create Workflow instance, return its id for SSE subscription.
app.post("/api/generate", async (c) => {
  const req = (await c.req.json()) as GenerateRequest;
  if (!req.departure || !req.destination) {
    return c.json({ error: "请填写出发地和目的地" }, 400);
  }
  const instanceId = crypto.randomUUID();
  await c.env.TRIP_WORKFLOW.create({ id: instanceId, params: { req, instanceId } });
  return c.json({ instanceId });
});

// SSE progress stream, proxied to the per-run Durable Object.
app.get("/api/stream/:id", async (c) => {
  const instanceId = c.req.param("id");
  const doId = c.env.PROGRESS.idFromName(instanceId);
  const stub = c.env.PROGRESS.get(doId);
  return stub.fetch("https://do/sse");
});

app.get("/api/routes", async (c) => {
  const page = parseInt(c.req.query("page") ?? "1", 10);
  const pageSize = parseInt(c.req.query("page_size") ?? "10", 10);
  return c.json(await db.listRoutes(c.env.DB, page, pageSize));
});

app.get("/api/routes/:id", async (c) => {
  const id = c.req.param("id");
  const route = await db.loadRoute(c.env.DB, "id", id);
  if (!route) return c.json({ detail: "路线不存在" }, 404);
  await db.incrementView(c.env.DB, id);
  return c.json(route);
});

app.post("/api/routes/:id/share", async (c) => {
  const shareId = await db.publishRoute(c.env.DB, c.req.param("id"));
  if (!shareId) return c.json({ detail: "路线不存在" }, 404);
  return c.json({ share_id: shareId, url: `/share/${shareId}` });
});

app.delete("/api/routes/:id", async (c) => {
  const ok = await db.deleteRoute(c.env.DB, c.req.param("id"));
  if (!ok) return c.json({ detail: "路线不存在" }, 404);
  return c.json({ success: true });
});

app.get("/api/share/:shareId", async (c) => {
  const route = await db.loadRoute(c.env.DB, "share_id", c.req.param("shareId"));
  if (!route) return c.json({ detail: "分享链接无效" }, 404);
  return c.json(route);
});

app.get("/api/weather", async (c) => {
  const city = c.req.query("city");
  if (!city) return c.json({ detail: "缺少 city 参数" }, 400);
  const days = parseInt(c.req.query("days") ?? "7", 10);
  return c.json(await getWeather(city, days));
});

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      return app.fetch(request, env, ctx);
    }
    // Everything else → static assets (SPA fallback handled by wrangler assets config).
    return env.ASSETS.fetch(request);
  },
};
