"""Code Generation Agent."""
from __future__ import annotations
from core.schemas import ChartSpec
from core.llm import chat

_PROMPT = """You are an expert Python data visualization developer.
Generate a complete executable Python script using Plotly that:
1. Reads data from variable `filepath` (already defined)
2. Creates the specified chart
3. Saves HTML to `output_path` using: fig.write_html(output_path)
4. Handles missing values with dropna()
5. Does NOT call fig.show()
Return ONLY Python code, no markdown fences, no explanation.

Chart type: {chart_type}
Title: {title}
X column: {x_column}
Y column: {y_column}
Color column: {color_column}
{error_section}"""


async def run(spec: ChartSpec, error: str | None = None) -> str:
    error_section = f"\nPrevious attempt failed with:\n{error}\nFix the code." if error else ""
    prompt = _PROMPT.format(
        chart_type=spec.chart_type, title=spec.title,
        x_column=spec.x_column, y_column=spec.y_column,
        color_column=spec.color_column, error_section=error_section
    )
    code = chat(prompt, json_mode=False)
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = "\n".join(code.split("\n")[:-1])
    return code.strip()
