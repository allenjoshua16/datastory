"""Visualization Generation Agent."""
from __future__ import annotations
import json, uuid
from core.schemas import ChartSpec, DatasetMetadata
from core.llm import chat, _clean_json

_PROMPT = """You are a data visualization expert. Given dataset metadata,
recommend 3-5 meaningful chart specifications.

Return ONLY a valid JSON array of objects with these exact keys:
- chart_type: one of bar|line|scatter|pie|histogram|heatmap|box|area
- title: concise chart title
- x_column: column name for x-axis (or null)
- y_column: column name for y-axis (or null)
- color_column: column for color grouping (or null)
- rationale: one sentence explaining the insight

No markdown, no explanation. Only the JSON array.

Dataset info:
Domain: {domain}
Rows: {rows}, Columns: {cols}
Column details: {columns}
Anomalies: {anomalies}"""


async def run(meta: DatasetMetadata) -> list[ChartSpec]:
    col_summary = [
        {"name": c.name, "dtype": c.dtype, "unique": c.unique_count, "sample": c.sample_values[:3]}
        for c in meta.columns
    ]
    prompt = _PROMPT.format(
        domain=meta.inferred_domain, rows=meta.row_count, cols=meta.column_count,
        columns=json.dumps(col_summary), anomalies=meta.anomalies
    )
    raw = chat(prompt, json_mode=True)
    parsed = json.loads(_clean_json(raw))
    if isinstance(parsed, dict):
        parsed = next(iter(parsed.values()))

    return [ChartSpec(
        chart_id=str(uuid.uuid4())[:8],
        chart_type=item.get("chart_type", "bar"),
        title=item.get("title", "Chart"),
        x_column=item.get("x_column"),
        y_column=item.get("y_column"),
        color_column=item.get("color_column"),
        rationale=item.get("rationale", ""),
    ) for item in parsed]
