/**
 * OffroadTripWorkflow — the 6-stage pipeline as durable Workflow steps.
 *
 * Each step.do(...) is independently retried and gets its own CPU budget, which
 * is why a several-minute LLM pipeline fits Cloudflare Workers' per-invocation
 * limits. Progress is pushed to the ProgressCoordinator DO (keyed by instanceId)
 * so the client's SSE stream can follow along.
 *
 * Timeout/retry discipline: LLM-calling steps (planning, enrichment) set an
 * EXPLICIT step timeout + retry limit sized around llm.ts's measured per-attempt
 * cost, instead of relying on the Workflow default (10min timeout, effectively
 * unbounded retries). Without that, a single slow LLM call gets killed by the
 * default step timeout mid-attempt, the step retries, hits the same timeout
 * again, and repeats — which is exactly what caused planning to appear stuck at
 * 30% for hours in production (see git history for the incident).
 */

import { WorkflowEntrypoint, type WorkflowEvent, type WorkflowStep } from "cloudflare:workers";
import type { Env, GenerateRequest, RouteData, ProgressEvent, WeatherData } from "./types";
import {
  normalizeReq,
  stageGeocode,
  stageWeather,
  stagePlanning,
  stageRouting,
  stageEnrichment,
  stageAssembly,
} from "./pipeline";
import { saveRoute } from "./db";

interface Params {
  req: GenerateRequest;
  instanceId: string;
}

export class OffroadTripWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep): Promise<RouteData> {
    const { req: rawReq, instanceId } = event.payload;
    const req = normalizeReq(rawReq);
    const emit = (e: ProgressEvent) => this.emitProgress(instanceId, e);

    try {
      // Stage 1: geocode
      await emit({ stage: "geocode", status: "running", message: "正在定位出发地和目的地...", progress: 5 });
      const { geoInfo } = await step.do("geocode", () => stageGeocode(this.env, req));
      await emit({ stage: "geocode", status: "done", message: `定位完成：${req.departure} → ${req.destination}`, progress: 10 });

      // Stage 2: weather
      await emit({ stage: "weather", status: "running", message: "正在获取沿途天气...", progress: 15 });
      const weatherMap = (await step.do("weather", () => stageWeather(this.env, req))) as Record<string, WeatherData>;
      await emit({ stage: "weather", status: "done", message: "天气获取完成", progress: 25 });

      // Stage 3: planning (LLM). llm.ts makes exactly one attempt per gateway key
      // (90s hard timeout each, 2 keys = 180s worst case) with no internal retry
      // loop, then falls back to Workers AI if both keys fail — retrying lives
      // here, at the Workflow step level, so worst-case latency is additive
      // (attempts × step timeout) instead of multiplicative (internal retries ×
      // step retries), which is what previously let one slow call get killed by
      // the Workflow's default step timeout mid-retry and then hang for hours on
      // the next retry repeating the same over-budget operation. 4min gives
      // headroom above the 180s two-key worst case for the Workers AI fallback.
      await emit({ stage: "planning", status: "running", message: "AI正在规划越野路线...", progress: 30 });
      let routeData = (await step.do(
        "planning",
        { timeout: "4 minutes", retries: { limit: 2, delay: "10 seconds", backoff: "exponential" } },
        () => stagePlanning(this.env, req, weatherMap, geoInfo)
      )) as RouteData;
      await emit({ stage: "planning", status: "done", message: `路线规划完成：${routeData.title ?? ""}`, progress: 50 });

      // Stage 4: routing + POI geocode
      await emit({ stage: "routing", status: "running", message: "正在获取详细路况和导航...", progress: 55 });
      routeData = (await step.do("routing", () => stageRouting(this.env, req, routeData))) as RouteData;
      await emit({
        stage: "routing",
        status: "done",
        message: `路况获取完成，总里程${Math.round(routeData.total_distance ?? 0)}km`,
        progress: 70,
      });

      // Stage 5: enrichment (LLM, per-day, parallel — see stageEnrichment's
      // Promise.allSettled). A few extra minutes of headroom for many days.
      await emit({ stage: "enrichment", status: "running", message: "正在丰富景点、美食、历史故事...", progress: 75 });
      routeData = (await step.do(
        "enrichment",
        { timeout: "6 minutes", retries: { limit: 1, delay: "10 seconds" } },
        () => stageEnrichment(this.env, routeData)
      )) as RouteData;
      await emit({ stage: "enrichment", status: "done", message: "内容丰富完成", progress: 90 });

      // Stage 6: assembly
      await emit({ stage: "assembly", status: "running", message: "正在组装图片和视频链接...", progress: 92 });
      routeData = (await step.do("assembly", () => stageAssembly(this.env, req, routeData, weatherMap))) as RouteData;

      // Persist (bug #1 fix). saveRoute mutates routeData with id/share_id, but on
      // a Workflow *resume* the local routeData is rebuilt from earlier step
      // returns — so we return the ids from the step and re-apply them explicitly.
      const ids = (await step.do("persist", async () => {
        await saveRoute(this.env.DB, routeData);
        return { id: routeData.id!, share_id: routeData.share_id! };
      })) as { id: string; share_id: string };
      routeData.id = ids.id;
      routeData.share_id = ids.share_id;

      await emit({ stage: "assembly", status: "done", message: "组装完成", progress: 100, route: routeData });
      return routeData;
    } catch (e) {
      await emit({ stage: "error", status: "error", message: String(e), progress: 100, error: String(e), route: null });
      throw e;
    }
  }

  private async emitProgress(instanceId: string, event: ProgressEvent): Promise<void> {
    const id = this.env.PROGRESS.idFromName(instanceId);
    const stub = this.env.PROGRESS.get(id);
    await stub.fetch("https://do/emit", {
      method: "POST",
      body: JSON.stringify(event),
    });
  }
}
