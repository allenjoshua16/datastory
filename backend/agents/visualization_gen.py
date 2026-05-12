"""Visualization Generation Agent."""
from __future__ import annotations
import json, uuid
from core.schemas import ChartSpec, DatasetMetadata
from core.llm import chat, _clean_json

_PROMPT = """You are a data visualization expert. Given dataset metadata,
recommend 3-5 meaningful chart specifications.

IMPORTANT: Use ONLY column names from the exact list provided below.

Return ONLY a valid JSON array of objects with these exact keys:
- chart_type: one of bar|line|scatter|pie|histogram|box|area
- title: concise chart title
- x_column: must be an exact column name from the list below (or null)
- y_column: must be an exact column name from the list below (or null)
- color_column: must be an exact column name from the list below (or null)
- rationale: one sentence explaining the insight

No markdown. Only the JSON array.

Domain: {domain}
Rows: {rows}
EXACT column names (use only these): {column_names}
Column details: {columns}
Anomalies: {anomalies}"""


async def run(meta: DatasetMetadata) -> list[ChartSpec]:
    column_names = [c.name for c in meta.columns]
    col_summary = [
        {"name": c.name, "dtype": c.dtype, "unique": c.unique_count, "sample": c.sample_values[:3]}
        for c in meta.columns
    ]
    prompt = _PROMPT.format(
        domain=meta.inferred_domain,
        rows=meta.row_count,
        column_names=column_names,
        columns=json.dumps(col_summary),
        anomalies=meta.anomalies,
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
        available_columns=column_names,
    ) for item in parsed]
