"""Report Generation Agent.

Assembles the final HTML report from stories and rendered charts using Jinja2.
"""
from __future__ import annotations
import os
from jinja2 import Environment, FileSystemLoader
from core.schemas import DatasetMetadata, ChartSpec, RankedStory

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def run(
    meta: DatasetMetadata,
    charts: list[ChartSpec],
    stories: list[RankedStory],
) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)
    template = env.get_template("report.html.j2")
    return template.render(meta=meta, charts=charts, stories=stories)
