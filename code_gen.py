"""Code Generation Agent.

Takes a ChartSpec and the dataset filepath, produces executable Plotly Python code.
The Code Execution Agent will actually run it — errors are fed back here to retry.
"""
from __future__ import annotations
from openai import AsyncOpenAI
from core.schemas import ChartSpec
from core.config import get_settings

_SYSTEM = """You are an expert Python data visualization developer.

Generate a complete, executable Python script using Plotly Express or Plotly Graph Objects that:
1. Reads data from the filepath variable already defined as `filepath`
2. Creates the specified chart
3. Saves an HTML file to the path in `output_path` variable using: fig.write_html(output_path)
4. Uses a clean, modern style with no gridlines where appropriate
5. Handles missing values gracefully with dropna()
6. Does NOT show the figure (no fig.show())

The script must be self-contained. Use pandas to load the file.
Return ONLY the Python code, no markdown fences, no explanation."""


def _build_prompt(spec: ChartSpec, error: str | None = None) -> str:
    prompt = (
        f"Chart type: {spec.chart_type}\n"
        f"Title: {spec.title}\n"
        f"X column: {spec.x_column}\n"
        f"Y column: {spec.y_column}\n"
        f"Color column: {spec.color_column}\n"
        f"Rationale: {spec.rationale}\n"
    )
    if error:
        prompt += f"\nPrevious attempt failed with error:\n{error}\nFix the code."
    return prompt


async def run(spec: ChartSpec, error: str | None = None) -> str:
    """Return Python code string for the given chart spec."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_prompt(spec, error)},
        ],
        max_tokens=1000,
        temperature=0.2,
    )
    code = response.choices[0].message.content.strip()
    # Strip any accidental markdown fences
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = "\n".join(code.split("\n")[:-1])
    return code
