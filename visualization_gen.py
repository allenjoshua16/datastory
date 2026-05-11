"""Visualization Generation Agent.

Takes DatasetMetadata and asks GPT-4 to recommend meaningful chart specs.
Returns a list of ChartSpec objects (without code yet — that's Code Gen's job).
"""
from __future__ import annotations
import json
import uuid
from openai import AsyncOpenAI
from core.schemas import ChartSpec, DatasetMetadata
from core.config import get_settings

_SYSTEM = """You are a data visualization expert. Given dataset metadata, 
recommend 3-5 meaningful, distinct chart specifications.

Return ONLY valid JSON — a list of objects with these exact keys:
- chart_type: one of bar|line|scatter|pie|histogram|heatmap|box|area|funnel|treemap
- title: concise chart title
- x_column: column name for x-axis (or null)
- y_column: column name for y-axis (or null)  
- color_column: column for color grouping (or null)
- rationale: one sentence explaining the insight this chart reveals

No markdown, no explanation outside the JSON array."""


def _build_user_prompt(meta: DatasetMetadata) -> str:
    col_summary = [
        {"name": c.name, "dtype": c.dtype, "unique": c.unique_count,
         "sample": c.sample_values[:3]}
        for c in meta.columns
    ]
    return (
        f"Domain: {meta.inferred_domain}\n"
        f"Rows: {meta.row_count}, Columns: {meta.column_count}\n"
        f"Columns: {json.dumps(col_summary)}\n"
        f"Anomalies: {meta.anomalies}\n"
        "Recommend 3-5 charts."
    )


async def run(meta: DatasetMetadata) -> list[ChartSpec]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_user_prompt(meta)},
        ],
        max_tokens=1200,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)

    # GPT sometimes wraps in a key
    if isinstance(parsed, dict):
        parsed = next(iter(parsed.values()))

    specs = []
    for item in parsed:
        specs.append(ChartSpec(
            chart_id=str(uuid.uuid4())[:8],
            chart_type=item.get("chart_type", "bar"),
            title=item.get("title", "Chart"),
            x_column=item.get("x_column"),
            y_column=item.get("y_column"),
            color_column=item.get("color_column"),
            rationale=item.get("rationale", ""),
        ))
    return specs
