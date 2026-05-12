"""Code Generation Agent."""
from __future__ import annotations
from core.schemas import ChartSpec
from core.llm import chat

_PROMPT = """You are an expert Python data visualization developer.
Generate a complete executable Python script using Plotly Express.

Rules:
1. Read data: use pd.read_excel(filepath) if filepath ends with .xlsx or .xls, else pd.read_csv(filepath)
2. Strip whitespace from column names: df.columns = df.columns.str.strip()
3. For date columns, parse them: pd.to_datetime(df[col], errors='coerce')
4. Use ONLY the exact column names listed below
5. For bar/line charts showing counts, use value_counts() or groupby()
6. For pie charts use value_counts()
7. Save with: fig.write_html(output_path, include_plotlyjs='cdn')
8. Do NOT call fig.show()
9. Wrap in try/except that prints full traceback

EXACT column names (copy exactly, including spaces):
{available_columns}

Chart to build:
- Type: {chart_type}
- Title: {title}
- X axis column: {x_column}
- Y axis column: {y_column}
- Color by: {color_column}
- Purpose: {rationale}

{error_section}

Return ONLY Python code. No markdown, no backticks."""


async def run(spec: ChartSpec, error: str | None = None) -> str:
    available = spec.available_columns if spec.available_columns else []
    error_section = f"PREVIOUS ERROR — fix this:\n{error}" if error else ""

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
