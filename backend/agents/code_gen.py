"""Code Generation Agent."""
from __future__ import annotations
from core.schemas import ChartSpec
from core.llm import chat

_PROMPT = """You are an expert Python data visualization developer.
Generate a complete executable Python script using Plotly that:
1. Reads data from variable `filepath` (already defined as a string path)
2. Loads it with pandas: use pd.read_csv(filepath) for CSV or pd.read_excel(filepath) for Excel
3. Creates the specified chart using plotly.express
4. Saves HTML to `output_path` using: fig.write_html(output_path, include_plotlyjs='cdn')
5. Handles missing values with dropna() before plotting
6. Uses only the exact column names provided — do not invent column names
7. Does NOT call fig.show()
8. Wraps everything in a try/except and prints errors

Return ONLY Python code, no markdown fences, no explanation.

Chart type: {chart_type}
Title: {title}
X column: {x_column}
Y column: {y_column}
Color column: {color_column}
Rationale: {rationale}
{error_section}"""


async def run(spec: ChartSpec, error: str | None = None) -> str:
    error_section = f"\nPrevious attempt failed with this error — fix it:\n{error}" if error else ""
    prompt = _PROMPT.format(
        chart_type=spec.chart_type,
        title=spec.title,
        x_column=spec.x_column or "None",
        y_column=spec.y_column or "None",
        color_column=spec.color_column or "None",
        rationale=spec.rationale,
        error_section=error_section,
    )
    code = chat(prompt, json_mode=False)
    # Strip markdown fences
    lines = code.strip().split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
