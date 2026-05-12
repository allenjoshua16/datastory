"""Visualization Generation Agent."""
from __future__ import annotations
import json, uuid
from core.schemas import ChartSpec, DatasetMetadata
from core.llm import chat, _clean_json

_PROMPT = """You are a data visualization expert. Recommend 3-5 charts for this dataset.

STRICT RULES:
- Use ONLY column names from the exact list provided
- Column names may have leading/trailing spaces — copy them exactly
- For categorical columns (like Product, Payment Method): use bar or pie charts with value_counts
- For numeric columns (like Price): use histogram or box charts
- For date columns (like Date): use line chart grouped by month
- Do NOT recommend scatter plots unless there are 2 numeric columns
- Do NOT recommend heatmaps unless there are multiple numeric columns

Return ONLY a valid JSON array. No markdown. Each object must have:
- chart_type: one of bar|line|pie|histogram|box|area
- title: concise chart title
- x_column: exact column name or null
- y_column: exact column name or null  
- color_column: exact column name or null
- rationale: one sentence

Domain: {domain}
Rows: {rows}
EXACT column names: {column_names}
Column details (dtype and samples): {columns}"""


async def run(meta: DatasetMetadata) -> list[ChartSpec]:
    column_names = [c.name for c in meta.columns]
    col_summary = [
        {"name": c.name, "dtype": c.dtype, "unique": c.unique_count,
         "sample": c.sample_values[:3], "is_numeric": c.mean is not None}
        for c in meta.columns
    ]
    prompt = _PROMPT.format(
        domain=meta.inferred_domain,
        rows=meta.row_count,
        column_names=column_names,
        columns=json.dumps(col_summary),
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
