"""Story Generation Agent.

Applies rhetorical structure theory (context → dispute → solution) to generate
narrative ideas. Returns a list of StoryIdea objects.
"""
from __future__ import annotations
import json
from openai import AsyncOpenAI
from core.schemas import ChartSpec, DatasetMetadata, StoryIdea
from core.config import get_settings

_SYSTEM = """You are a data storytelling expert who writes compelling business narratives.

Given dataset analysis and visualization specs, generate 3 story ideas using 
rhetorical structure theory:
- context: what's the background situation
- dispute: the surprising or counter-intuitive finding  
- solution: the concrete recommendation

Return ONLY valid JSON — a list of objects with these keys:
- title: punchy story title (max 8 words)
- hook: one-sentence grabber that creates curiosity
- context: 1-2 sentences of background
- dispute: 1-2 sentences on the unexpected finding
- solution: 1-2 sentences with an actionable recommendation
- relevant_chart_ids: list of chart_ids from the provided specs

No markdown, no extra text outside the JSON array."""


def _build_prompt(meta: DatasetMetadata, charts: list[ChartSpec]) -> str:
    chart_summary = [
        {"chart_id": c.chart_id, "title": c.title, "rationale": c.rationale}
        for c in charts
    ]
    anomaly_text = "\n".join(meta.anomalies) if meta.anomalies else "None detected"
    numeric_cols = [c for c in meta.columns if c.mean is not None]
    stats_summary = [
        {"col": c.name, "mean": c.mean, "min": c.min, "max": c.max}
        for c in numeric_cols[:8]
    ]
    return (
        f"Domain: {meta.inferred_domain}, {meta.row_count} rows\n"
        f"Key stats: {json.dumps(stats_summary)}\n"
        f"Anomalies: {anomaly_text}\n"
        f"Available charts: {json.dumps(chart_summary)}\n"
        "Generate 3 story ideas."
    )


async def run(meta: DatasetMetadata, charts: list[ChartSpec]) -> list[StoryIdea]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_prompt(meta, charts)},
        ],
        max_tokens=1800,
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed = next(iter(parsed.values()))

    return [StoryIdea(**item) for item in parsed]
