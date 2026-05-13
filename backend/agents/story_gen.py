"""Story Generation Agent — bulletproof parsing."""
from __future__ import annotations
import json
import logging
from core.schemas import ChartSpec, DatasetMetadata, StoryIdea
from core.llm import chat, _clean_json

logger = logging.getLogger(__name__)

_PROMPT = """You are a data storytelling expert. Generate exactly 3 story ideas.

Return ONLY a valid JSON array of exactly 3 objects. Each object must have ALL these keys:
- "title": string, max 8 words
- "hook": string, one sentence
- "context": string, 1-2 sentences
- "dispute": string, 1-2 sentences about unexpected finding
- "solution": string, 1-2 sentences with recommendation
- "relevant_chart_ids": array of strings (can be empty array [])

No markdown. No explanation. Only the JSON array.

Dataset: {domain} domain, {rows} rows
Key stats: {stats}
Anomalies: {anomalies}
Charts available: {charts}"""


def _safe_parse_ideas(raw: str) -> list[StoryIdea]:
    """Parse story ideas with multiple fallback strategies."""
    try:
        cleaned = _clean_json(raw)
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            for key in ["stories", "ideas", "narratives", "results"]:
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())[0] if parsed else []

        if not isinstance(parsed, list):
            raise ValueError(f"Expected list, got {type(parsed)}")

        ideas = []
        required = ["title", "hook", "context", "dispute", "solution"]
        for item in parsed:
            if not isinstance(item, dict):
                continue
            # Fill missing fields with defaults
            for field in required:
                if field not in item or not item[field]:
                    item[field] = f"[{field} not provided]"
            if "relevant_chart_ids" not in item:
                item["relevant_chart_ids"] = []
            try:
                ideas.append(StoryIdea(
                    title=str(item["title"]),
                    hook=str(item["hook"]),
                    context=str(item["context"]),
                    dispute=str(item["dispute"]),
                    solution=str(item["solution"]),
                    relevant_chart_ids=[str(x) for x in item.get("relevant_chart_ids", [])],
                ))
            except Exception as e:
                logger.warning(f"Skipping malformed story item: {e}")
        return ideas

    except Exception as e:
        logger.error(f"Story parsing failed: {e}\nRaw: {raw[:500]}")
        return []


async def run(meta: DatasetMetadata, charts: list[ChartSpec]) -> list[StoryIdea]:
    chart_summary = [
        {"chart_id": c.chart_id, "title": c.title, "rationale": c.rationale}
        for c in charts
    ]
    numeric_cols = [c for c in meta.columns if c.mean is not None]
    stats_summary = [
        {"col": c.name, "mean": c.mean, "min": c.min, "max": c.max}
        for c in numeric_cols[:6]
    ]

    prompt = _PROMPT.format(
        domain=meta.inferred_domain,
        rows=meta.row_count,
        stats=json.dumps(stats_summary, default=str),
        anomalies="; ".join(meta.anomalies) if meta.anomalies else "None detected",
        charts=json.dumps(chart_summary, default=str),
    )

    try:
        raw = chat(prompt, json_mode=True)
        ideas = _safe_parse_ideas(raw)
        if ideas:
            return ideas
    except Exception as e:
        logger.error(f"Story generation failed: {e}")

    # Fallback: generate minimal stories from metadata
    logger.warning("Using fallback story generation")
    return [StoryIdea(
        title=f"Key insights from {meta.inferred_domain} data",
        hook=f"Your {meta.row_count}-row dataset reveals important patterns.",
        context=f"Analysis of {meta.column_count} variables in the {meta.inferred_domain} domain.",
        dispute="Some metrics show unexpected distributions worth investigating.",
        solution="Review the visualizations below and focus on the highlighted anomalies.",
        relevant_chart_ids=[c.chart_id for c in charts[:2]],
    )]
