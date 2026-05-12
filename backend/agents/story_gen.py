"""Story Generation Agent."""
from __future__ import annotations
import json
from core.schemas import ChartSpec, DatasetMetadata, StoryIdea
from core.llm import chat, _clean_json

_PROMPT = """You are a data storytelling expert. Generate 3 story ideas using rhetorical structure theory.

Return ONLY a valid JSON array of objects with these keys:
- title: punchy story title (max 8 words)
- hook: one-sentence grabber
- context: 1-2 sentences of background
- dispute: 1-2 sentences on the unexpected finding
- solution: 1-2 sentences with actionable recommendation
- relevant_chart_ids: list of chart_ids from provided specs

No markdown. Only the JSON array.

Domain: {domain}, {rows} rows
Key stats: {stats}
Anomalies: {anomalies}
Available charts: {charts}"""


async def run(meta: DatasetMetadata, charts: list[ChartSpec]) -> list[StoryIdea]:
    chart_summary = [{"chart_id": c.chart_id, "title": c.title, "rationale": c.rationale} for c in charts]
    numeric_cols = [c for c in meta.columns if c.mean is not None]
    stats_summary = [{"col": c.name, "mean": c.mean, "min": c.min, "max": c.max} for c in numeric_cols[:8]]
    anomaly_text = "; ".join(meta.anomalies) if meta.anomalies else "None"

    prompt = _PROMPT.format(
        domain=meta.inferred_domain, rows=meta.row_count,
        stats=json.dumps(stats_summary), anomalies=anomaly_text,
        charts=json.dumps(chart_summary)
    )
    raw = chat(prompt, json_mode=True)
    parsed = json.loads(_clean_json(raw))
    if isinstance(parsed, dict):
        parsed = next(iter(parsed.values()))
    return [StoryIdea(**item) for item in parsed]
