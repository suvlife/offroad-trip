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

  const timeoutMs = parseInt(env.LLM_TIMEOUT_MS || "300000", 10);
  const maxRetries = 3;
  let lastError: unknown = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      let resp: Response;
      try {
        resp = await fetch(`${baseUrl}/chat/completions`, {
          method: "POST",
          headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });
      } finally {
        clearTimeout(timer);
      }

      if (!resp.ok) {
        const text = await resp.text();
        console.error(`Gateway ${resp.status}: ${text.slice(0, 500)}`);
        if (resp.status >= 400 && resp.status < 500) throw new Error(`Gateway ${resp.status}`);
        throw new Error(`Gateway ${resp.status}`);
      }

      const data = (await resp.json()) as any;
      const choice = data.choices?.[0] ?? {};
      const content: string = choice.message?.content || "";
      console.log(`Gateway OK model=${model} content=${content.length} finish=${choice.finish_reason}`);
      return content.trim();
    } catch (e) {
      lastError = e;
      console.warn(`Gateway error (attempt ${attempt + 1}/${maxRetries}): ${e}`);
      if (attempt < maxRetries - 1) await new Promise((r) => setTimeout(r, 2 ** attempt * 1000));
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Gateway call failed");
}

// ── Provider 2: Cloudflare Workers AI (free) ────────────────────────────────

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

  const maxRetries = 2;
  let lastError: unknown = null;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const resp = (await env.AI.run(model as keyof AiModels, input as any)) as any;
      const content: string = resp?.response ?? "";
      console.log(`Workers AI OK model=${model} content=${content.length}`);
      return content.trim();
    } catch (e) {
      lastError = e;
      console.warn(`Workers AI error (attempt ${attempt + 1}/${maxRetries}): ${e}`);
      if (attempt < maxRetries - 1) await new Promise((r) => setTimeout(r, 1000));
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Workers AI call failed");
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
