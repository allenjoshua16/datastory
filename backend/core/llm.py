"""Unified LLM client — supports Groq and Gemini with auto-retry on rate limits."""
from __future__ import annotations
import logging
import time
from core.config import get_settings

logger = logging.getLogger(__name__)


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = "\n".join(text.split("\n")[:-1])
    return text.strip()


def chat(prompt: str, json_mode: bool = False, retries: int = 5, base_wait: int = 20) -> str:
    settings = get_settings()
    provider = settings.ai_provider.lower()

    last_error = None
    for attempt in range(retries):
        try:
            if provider == "groq":
                return _groq_chat(prompt, json_mode, settings)
            else:
                return _gemini_chat(prompt, json_mode, settings)

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            is_rate_limit = (
                "429" in str(e)
                or "rate" in err_str
                or "quota" in err_str
                or "too many" in err_str
                or "exhausted" in err_str
                or "ratelimit" in err_str
            )
            if is_rate_limit and attempt < retries - 1:
                wait = base_wait * (attempt + 1)
                logger.warning(f"Rate limit hit (attempt {attempt+1}/{retries}), waiting {wait}s...")
                time.sleep(wait)
                continue

            # Non-rate-limit error — raise immediately
            raise

    raise RuntimeError(f"All {retries} retry attempts exhausted. Last error: {last_error}")


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
