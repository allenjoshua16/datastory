"""Unified LLM client — supports Groq and Gemini with auto-retry on rate limits."""
from __future__ import annotations
import json
import logging
import time
from core.config import get_settings

logger = logging.getLogger(__name__)


def _clean_json(text: str) -> str:
    """Strip markdown fences from JSON responses."""
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = "\n".join(text.split("\n")[:-1])
    return text.strip()


def chat(prompt: str, json_mode: bool = False, retries: int = 4, wait: int = 15) -> str:
    """
    Send a prompt to the configured LLM provider.
    Automatically retries on rate limit errors with exponential backoff.
    """
    settings = get_settings()
    provider = settings.ai_provider.lower()

    for attempt in range(retries):
        try:
            if provider == "groq":
                return _groq_chat(prompt, json_mode, settings)
            else:
                return _gemini_chat(prompt, json_mode, settings)

        except Exception as e:
            err = str(e).lower()
            is_rate_limit = "429" in str(e) or "quota" in err or "rate" in err or "exhausted" in err
            if is_rate_limit and attempt < retries - 1:
                sleep_time = wait * (attempt + 1)
                logger.warning(f"Rate limit hit (attempt {attempt+1}), retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            raise

    raise RuntimeError("All retry attempts exhausted.")


def _groq_chat(prompt: str, json_mode: bool, settings) -> str:
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    kwargs = {"model": settings.groq_model,
              "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 2048}
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
