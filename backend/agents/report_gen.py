"""Report Generation Agent."""
from __future__ import annotations
import os
from jinja2 import Environment, FileSystemLoader
from core.schemas import DatasetMetadata, ChartSpec, RankedStory, PreprocessingReport

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def run(
    meta: DatasetMetadata,
    charts: list[ChartSpec],
    stories: list[RankedStory],
    preprocessing_report: PreprocessingReport | None = None,
) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)
    template = env.get_template("report.html.j2")
    return template.render(
        meta=meta, charts=charts, stories=stories,
        preprocessing_report=preprocessing_report,
    )
