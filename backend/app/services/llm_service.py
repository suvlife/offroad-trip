"""LLM service - connects to silk-gateway (OpenAI-compatible Cloudflare Workers gateway).

Supports DeepSeek / Doubao / Kimi via the gateway's unified endpoint.
Handles reasoning models (deepseek-v4-pro) that return reasoning_content + content.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def call_llm(
    prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: int = 16384,
    json_mode: bool = False,
) -> str:
    """Call the LLM via silk-gateway (OpenAI-compatible /chat/completions).

    Args:
        prompt: user message
        system_prompt: system message (domain expertise)
        model: model name (default from settings)
        temperature: sampling temperature
        max_tokens: max response tokens (reasoning models need more - they "think" first)
        json_mode: if True, request JSON object response format

    Returns: the LLM response text, or "" if not configured.
    """
    base_url = (settings.SILK_GATEWAY_URL or "").rstrip("/")
    api_key = settings.SILK_GATEWAY_KEY

    if not base_url or not api_key:
        logger.warning("SILK_GATEWAY_URL/KEY not configured - LLM calls will return empty")
        return ""

    model_name = model or settings.LLM_MODEL
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": temp,
        "max_tokens": max_tokens,
        "stream": False,  # explicitly disable streaming - we want a single JSON response
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=float(settings.LLM_TIMEOUT)) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            # Log non-200 responses for debugging
            if resp.status_code != 200:
                logger.error(
                    f"LLM API returned {resp.status_code}: {resp.text[:500]}"
                )
                resp.raise_for_status()

            data = resp.json()

        choice = data["choices"][0]
        message = choice.get("message", {})

        # Reasoning models (deepseek-v4-pro) have both reasoning_content and content.
        # The actual answer is in "content"; reasoning_content is the chain-of-thought.
        content = message.get("content", "") or ""

        # If content is empty but reasoning_content exists, the model may have used
        # all tokens on reasoning. Log a warning.
        if not content and message.get("reasoning_content"):
            reasoning = message.get("reasoning_content", "")
            logger.warning(
                f"LLM returned empty content but has reasoning_content "
                f"({len(reasoning)} chars). Consider increasing max_tokens. "
                f"Finish reason: {choice.get('finish_reason')}"
            )

        logger.info(
            f"LLM call OK: model={model_name}, "
            f"content={len(content)} chars, "
            f"finish={choice.get('finish_reason')}, "
            f"tokens={data.get('usage', {}).get('total_tokens', '?')}"
        )

        return content.strip()
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text[:300]}")
        raise
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise


def parse_json_response(content: str) -> dict:
    """Parse JSON from LLM response, handling markdown code fences.

    Falls back to {} if parsing fails.
    """
    if not content:
        return {}

    text = content.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        first_newline = text.find("\n")
        last_fence = text.rfind("```")
        if first_newline != -1 and last_fence != -1 and last_fence > first_newline:
            text = text[first_newline + 1 : last_fence].strip()
        else:
            text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse LLM JSON response: {text[:500]}")
        return {}
