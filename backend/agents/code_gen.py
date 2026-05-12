"""Code Generation Agent."""
from __future__ import annotations
from core.schemas import ChartSpec
from core.llm import chat

_PROMPT = """You are an expert Python data visualization developer.
Generate a complete executable Python script using Plotly Express that:
1. Reads data from variable `filepath` (already defined)
2. Auto-detects file type: use pd.read_excel(filepath) if filepath ends with .xlsx or .xls, else pd.read_csv(filepath)
3. Creates the specified chart
4. Saves to `output_path` with: fig.write_html(output_path, include_plotlyjs='cdn')
5. Uses ONLY the exact column names listed below
6. Calls dropna(subset=[used_columns]) before plotting
7. Does NOT call fig.show()
8. Has a try/except that prints the full traceback on error

EXACT column names available in the dataset:
{available_columns}

Chart to build:
- Type: {chart_type}
- Title: {title}
- X axis: {x_column}
- Y axis: {y_column}
- Color by: {color_column}
- Purpose: {rationale}

{error_section}
Return ONLY Python code. No markdown, no backticks, no explanation."""


async def run(spec: ChartSpec, error: str | None = None) -> str:
    available = spec.available_columns if hasattr(spec, 'available_columns') and spec.available_columns else "unknown - use x_column and y_column as provided"
    error_section = f"PREVIOUS ERROR (fix this):\n{error}" if error else ""

    prompt = _PROMPT.format(
        available_columns=available,
        chart_type=spec.chart_type,
        title=spec.title,
        x_column=spec.x_column or "None",
        y_column=spec.y_column or "None",
        color_column=spec.color_column or "None",
        rationale=spec.rationale,
        error_section=error_section,
    )
    code = chat(prompt, json_mode=False)
    lines = code.strip().split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
