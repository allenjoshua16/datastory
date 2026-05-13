"""Visualization Generation Agent — bulletproof parsing."""
from __future__ import annotations
import json
import logging
import uuid
from core.schemas import ChartSpec, DatasetMetadata
from core.llm import chat, _clean_json

logger = logging.getLogger(__name__)

_PROMPT = """You are a data visualization expert. Recommend 3-5 charts for this dataset.

Return ONLY a valid JSON array. Each object must have ALL these keys:
- "chart_type": one of: bar, line, pie, histogram, box, scatter, area
- "title": string
- "x_column": exact column name from list below OR null
- "y_column": exact column name from list below OR null
- "color_column": exact column name from list below OR null
- "rationale": one sentence

Rules:
- ONLY use column names from this exact list: {column_names}
- For text/category columns: use bar or pie with value_counts
- For numeric columns: use histogram or box
- For date columns: use line chart
- No markdown. Only the JSON array.

Domain: {domain} | Rows: {rows}
Column details: {columns}"""


def _safe_parse_specs(raw: str, column_names: list[str]) -> list[dict]:
    """Parse chart specs with fallback."""
    try:
        cleaned = _clean_json(raw)
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            for key in ["charts", "visualizations", "specs", "recommendations"]:
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())[0] if parsed else []
        if isinstance(parsed, list):
            return parsed
    except Exception as e:
        logger.warning(f"Chart spec parsing failed: {e}")
    return []


def _make_fallback_specs(meta: DatasetMetadata, column_names: list[str]) -> list[dict]:
    """Generate sensible default charts when LLM fails."""
    specs = []
    cat_cols = [c for c in meta.columns if c.dtype == "object" and c.unique_count < 50]
    num_cols = [c for c in meta.columns if c.mean is not None]
    date_cols = [c for c in meta.columns if any(x in c.name.lower() for x in ["date", "time", "month", "year"])]

    if cat_cols:
        specs.append({"chart_type": "bar", "title": f"{cat_cols[0].name} Distribution",
                      "x_column": cat_cols[0].name, "y_column": None, "color_column": None,
                      "rationale": f"Shows frequency of each {cat_cols[0].name}"})
    if len(cat_cols) > 1:
        specs.append({"chart_type": "pie", "title": f"{cat_cols[1].name} Breakdown",
                      "x_column": cat_cols[1].name, "y_column": None, "color_column": None,
                      "rationale": f"Proportion of each {cat_cols[1].name}"})
    if num_cols:
        specs.append({"chart_type": "histogram", "title": f"{num_cols[0].name} Distribution",
                      "x_column": num_cols[0].name, "y_column": None, "color_column": None,
                      "rationale": f"Distribution of {num_cols[0].name} values"})
    if date_cols and num_cols:
        specs.append({"chart_type": "line", "title": f"{num_cols[0].name} Over Time",
                      "x_column": date_cols[0].name, "y_column": num_cols[0].name,
                      "color_column": None, "rationale": "Trend over time"})
    if cat_cols and num_cols:
        specs.append({"chart_type": "bar", "title": f"{num_cols[0].name} by {cat_cols[0].name}",
                      "x_column": cat_cols[0].name, "y_column": num_cols[0].name,
                      "color_column": None, "rationale": f"Compare {num_cols[0].name} across categories"})
    return specs[:5]


async def run(meta: DatasetMetadata) -> list[ChartSpec]:
    column_names = [c.name for c in meta.columns]
    col_summary = [
        {"name": c.name, "dtype": c.dtype, "unique": c.unique_count,
         "is_numeric": c.mean is not None, "sample": c.sample_values[:2]}
        for c in meta.columns
    ]

    prompt = _PROMPT.format(
        domain=meta.inferred_domain, rows=meta.row_count,
        column_names=column_names, columns=json.dumps(col_summary, default=str),
    )

    raw_specs = []
    try:
        raw = chat(prompt, json_mode=True)
        raw_specs = _safe_parse_specs(raw, column_names)
    except Exception as e:
        logger.error(f"Visualization gen LLM failed: {e}")

    if not raw_specs:
        logger.warning("Using fallback chart specs")
        raw_specs = _make_fallback_specs(meta, column_names)

    charts = []
    for item in raw_specs:
        if not isinstance(item, dict):
            continue
        # Validate column names — set to None if not in dataset
        x = item.get("x_column")
        y = item.get("y_column")
        color = item.get("color_column")
        if x and x not in column_names:
            logger.warning(f"x_column '{x}' not in dataset, setting None")
            x = None
        if y and y not in column_names:
            logger.warning(f"y_column '{y}' not in dataset, setting None")
            y = None
        if color and color not in column_names:
            color = None

        charts.append(ChartSpec(
            chart_id=str(uuid.uuid4())[:8],
            chart_type=item.get("chart_type", "bar"),
            title=str(item.get("title", "Chart")),
            x_column=x,
            y_column=y,
            color_column=color,
            rationale=str(item.get("rationale", "")),
            available_columns=column_names,
        ))

    return charts
