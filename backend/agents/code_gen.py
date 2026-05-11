"""Code Generation Agent — uses Gemini."""
from __future__ import annotations
import google.generativeai as genai
from core.schemas import ChartSpec
from core.config import get_settings

_SYSTEM = """You are an expert Python data visualization developer.
Generate a complete, executable Python script using Plotly that:
1. Reads data from the variable `filepath` (already defined)
2. Creates the specified chart
3. Saves HTML to `output_path` using: fig.write_html(output_path)
4. Uses a clean modern style, handles missing values with dropna()
5. Does NOT call fig.show()
Return ONLY the Python code, no markdown fences, no explanation."""


async def run(spec: ChartSpec, error: str | None = None) -> str:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    prompt = (
        f"{_SYSTEM}\n\n"
        f"Chart type: {spec.chart_type}\nTitle: {spec.title}\n"
        f"X column: {spec.x_column}\nY column: {spec.y_column}\n"
        f"Color column: {spec.color_column}\nRationale: {spec.rationale}\n"
    )
    if error:
        prompt += f"\nPrevious attempt failed with:\n{error}\nFix the code."

    response = model.generate_content(prompt)
    code = response.text.strip()
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = "\n".join(code.split("\n")[:-1])
    return code
