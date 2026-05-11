"""Story Generation Agent — uses Gemini."""
from __future__ import annotations
import json
import google.generativeai as genai
from core.schemas import ChartSpec, DatasetMetadata, StoryIdea
from core.config import get_settings

_SYSTEM = """You are a data storytelling expert who writes compelling business narratives.

Given dataset analysis and visualization specs, generate 3 story ideas using
rhetorical structure theory:
- context: what's the background situation
- dispute: the surprising or counter-intuitive finding
- solution: the concrete recommendation

Return ONLY a JSON array of objects with these keys:
- title: punchy story title (max 8 words)
- hook: one-sentence grabber that creates curiosity
- context: 1-2 sentences of background
- dispute: 1-2 sentences on the unexpected finding
- solution: 1-2 sentences with an actionable recommendation
- relevant_chart_ids: list of chart_ids from the provided specs"""


def _build_prompt(meta: DatasetMetadata, charts: list[ChartSpec]) -> str:
    chart_summary = [{"chart_id": c.chart_id, "title": c.title, "rationale": c.rationale} for c in charts]
    anomaly_text = "\n".join(meta.anomalies) if meta.anomalies else "None detected"
    numeric_cols = [c for c in meta.columns if c.mean is not None]
    stats_summary = [{"col": c.name, "mean": c.mean, "min": c.min, "max": c.max} for c in numeric_cols[:8]]
    return (
        f"{_SYSTEM}\n\n"
        f"Domain: {meta.inferred_domain}, {meta.row_count} rows\n"
        f"Key stats: {json.dumps(stats_summary)}\n"
        f"Anomalies: {anomaly_text}\n"
        f"Available charts: {json.dumps(chart_summary)}\n"
        "Generate 3 story ideas. Return only a JSON array."
    )


async def run(meta: DatasetMetadata, charts: list[ChartSpec]) -> list[StoryIdea]:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        settings.gemini_model,
        generation_config={"response_mime_type": "application/json"}
    )

    response = model.generate_content(_build_prompt(meta, charts))
    parsed = json.loads(response.text.strip())
    if isinstance(parsed, dict):
        parsed = next(iter(parsed.values()))

    return [StoryIdea(**item) for item in parsed]
