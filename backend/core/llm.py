"""Unified LLM client — Groq + Gemini with aggressive retry and fallback."""
from __future__ import annotations
import json
import logging
import time
from core.config import get_settings

logger = logging.getLogger(__name__)


def _clean_json(text: str) -> str:
    text = text.strip()
    for fence in ["```json", "```JSON", "```"]:
        if text.startswith(fence):
            text = text[len(fence):]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def chat(prompt: str, json_mode: bool = False, retries: int = 6, base_wait: int = 15) -> str:
    settings = get_settings()
    providers = [settings.ai_provider.lower()]
    # Auto-fallback to other provider
    if "groq" in providers:
        providers.append("gemini")
    else:
        providers.append("groq")

    last_error = None
    for provider in providers:
        for attempt in range(retries):
            try:
                if provider == "groq" and settings.groq_api_key:
                    return _groq_chat(prompt, json_mode, settings)
                elif provider == "gemini" and settings.gemini_api_key:
                    return _gemini_chat(prompt, json_mode, settings)
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_rate_limit = any(x in err_str for x in [
                    "429", "rate", "quota", "too many", "exhausted",
                    "ratelimit", "resource_exhausted", "tokens per"
                ])
                is_bad_model = any(x in err_str for x in [
                    "decommissioned", "not found", "not supported", "invalid model"
                ])
                if is_bad_model:
                    logger.error(f"Bad model for {provider}: {e}")
                    break  # Try next provider
                if is_rate_limit and attempt < retries - 1:
                    wait = base_wait * (attempt + 1)
                    logger.warning(f"[{provider}] Rate limit attempt {attempt+1}/{retries}, waiting {wait}s")
                    time.sleep(wait)
                    continue
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                break
        else:
            continue
        if last_error and not any(x in str(last_error).lower() for x in ["decommissioned", "not found"]):
            continue

    raise RuntimeError(f"All LLM providers failed. Last: {last_error}")


def _groq_chat(prompt: str, json_mode: bool, settings) -> str:
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    kwargs = {
        "model": settings.groq_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


def _gemini_chat(prompt: str, json_mode: bool, settings) -> str:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    gen_config = {"response_mime_type": "application/json"} if json_mode else {}
    model = genai.GenerativeModel(settings.gemini_model, generation_config=gen_config)
    response = model.generate_content(prompt)
    return response.text.strip()
