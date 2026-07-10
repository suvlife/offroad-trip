/**
 * LLM service. Two providers, tried in order:
 *   1. External OpenAI-compatible gateway (火山方舟 Agent Plan, ark-code-latest) —
 *      used when SILK_GATEWAY_URL + a SILK_GATEWAY_KEY secret are set. Two keys
 *      are supported (SILK_GATEWAY_KEY / SILK_GATEWAY_KEY_2) — if the primary key
 *      fails (rate limit, quota, transient error), the second is tried before
 *      falling back further. This is a reasoning model: it "thinks" into
 *      reasoning_content before writing the real answer into content, so
 *      max_tokens must be generous (16384) or content comes back empty.
 *   2. Cloudflare Workers AI (env.AI) — the free, no-key fallback if neither
 *      gateway key is configured or both fail.
 *
 * Retries live ONLY at the Workflow step level (workflow.ts's step.do config) —
 * this module makes exactly one HTTP attempt per key with a hard timeout. Layering
 * retries here on top of the Workflow's own step retries multiplies worst-case
 * latency (retries × keys × Workflow attempts) past the step timeout, which is
 * exactly what caused planning to hang for hours: a slow call got killed by the
 * Workflow timeout mid-retry, then retried the whole over-budget operation again.
 *
 * Ported from backend/app/services/llm_service.py.
 */

import type { Env } from "../types";

interface LlmOptions {
  systemPrompt?: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  jsonMode?: boolean;
}

type ChatMessage = { role: "system" | "user" | "assistant"; content: string };

// Measured: a full planner-sized prompt against ark-code-latest completes in
// ~50s. 90s gives headroom without letting one attempt eat the whole step budget.
const GATEWAY_TIMEOUT_MS = 90_000;

export async function callLlm(env: Env, prompt: string, opts: LlmOptions = {}): Promise<string> {
  const { systemPrompt = "", temperature = 0.8, maxTokens = 16384, jsonMode = false } = opts;
  const messages: ChatMessage[] = [];
  if (systemPrompt) messages.push({ role: "system", content: systemPrompt });
  messages.push({ role: "user", content: prompt });

  const keys = [env.SILK_GATEWAY_KEY, env.SILK_GATEWAY_KEY_2].filter(Boolean) as string[];
  if (env.SILK_GATEWAY_URL && keys.length > 0) {
    let lastErr: unknown = null;
    for (const [i, key] of keys.entries()) {
      try {
        return await callGateway(env, key, messages, { temperature, maxTokens, jsonMode, model: opts.model });
      } catch (e) {
        lastErr = e;
        console.warn(`Gateway key #${i + 1} failed: ${e}`);
      }
    }
    console.error(`All gateway keys failed (${lastErr}); falling back to Workers AI`);
  }
  // Fallback: Cloudflare Workers AI (free, no key).
  if (env.AI) {
    return callWorkersAI(env, messages, { temperature, maxTokens, jsonMode });
  }
  console.warn("No LLM configured (no gateway secret and no AI binding) - returning empty");
  return "";
}

// ── Provider 1: external OpenAI-compatible gateway (火山方舟 Agent Plan) ────

/** Exactly one HTTP attempt with a hard timeout — no internal retry (see module doc). */
async function callGateway(
  env: Env,
  apiKey: string,
  messages: ChatMessage[],
  o: { temperature: number; maxTokens: number; jsonMode: boolean; model?: string }
): Promise<string> {
  const baseUrl = (env.SILK_GATEWAY_URL || "").replace(/\/+$/, "");
  const model = o.model || env.LLM_MODEL || "ark-code-latest";

  const payload: Record<string, unknown> = {
    model,
    messages,
    temperature: o.temperature,
    max_tokens: o.maxTokens,
    stream: false,
  };
  if (o.jsonMode) payload.response_format = { type: "json_object" };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), GATEWAY_TIMEOUT_MS);
  let resp: Response;
  try {
    resp = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch (e) {
    throw new Error(`Gateway request failed: ${e}`);
  } finally {
    clearTimeout(timer);
  }

  if (!resp.ok) {
    const text = await resp.text();
    console.error(`Gateway ${resp.status}: ${text.slice(0, 500)}`);
    throw new Error(`Gateway ${resp.status}`);
  }

  const data = (await resp.json()) as any;
  const choice = data.choices?.[0] ?? {};
  const content: string = choice.message?.content || "";
  console.log(`Gateway OK model=${model} content=${content.length} finish=${choice.finish_reason}`);
  return content.trim();
}

// ── Provider 2: Cloudflare Workers AI (free) ────────────────────────────────

/** Exactly one attempt — no internal retry (see module doc). */
async function callWorkersAI(
  env: Env,
  messages: ChatMessage[],
  o: { temperature: number; maxTokens: number; jsonMode: boolean }
): Promise<string> {
  const model = env.WORKERS_AI_MODEL || "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
  // Workers AI caps output tokens well below the gateway; keep it in range.
  const maxTokens = Math.min(o.maxTokens, 8192);

  const input: Record<string, unknown> = { messages, max_tokens: maxTokens, temperature: o.temperature };
  if (o.jsonMode) input.response_format = { type: "json_object" };

  const resp = (await env.AI.run(model as keyof AiModels, input as any)) as any;
  const content: string = resp?.response ?? "";
  console.log(`Workers AI OK model=${model} content=${content.length}`);
  return content.trim();
}

/** Parse JSON from an LLM response — strips markdown fences, then falls back to
 *  extracting the outermost {...} block (small models sometimes add prose). */
export function parseJsonResponse<T = Record<string, unknown>>(content: string): T | Record<string, never> {
  if (!content) return {};
  let text = content.trim();

  if (text.startsWith("```")) {
    const firstNewline = text.indexOf("\n");
    const lastFence = text.lastIndexOf("```");
    if (firstNewline !== -1 && lastFence !== -1 && lastFence > firstNewline) {
      text = text.slice(firstNewline + 1, lastFence).trim();
    } else {
      text = text.replace(/```json/g, "").replace(/```/g, "").trim();
    }
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    // Fallback: grab the first '{' .. last '}' span.
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start !== -1 && end > start) {
      try {
        return JSON.parse(text.slice(start, end + 1)) as T;
      } catch {}
    }
    console.error(`Failed to parse LLM JSON: ${text.slice(0, 500)}`);
    return {};
  }
}
