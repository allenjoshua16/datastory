"""Orchestrator.

Coordinates all agents in sequence, updating the job store after each stage
so the WebSocket endpoint can stream live progress to the frontend.
"""
from __future__ import annotations
import asyncio
import os
import traceback

from core import job_store
from core.schemas import AudienceMode, PipelineJob
from agents import (
    data_analysis,
    visualization_gen,
    story_gen,
    story_exec,
    code_exec,
    report_gen,
)

CHART_OUTPUT_DIR = "./chart_outputs"


async def run_pipeline(job: PipelineJob, filepath: str, audience: AudienceMode = "executive"):
    os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

    def _update(status, progress, message):
        job_store.update_job(
            job.job_id,
            status=status,
            progress=progress,
            status_message=message,
        )

    try:
        # Stage 1 — Data Analysis
        _update("analyzing", 10, "Analyzing dataset structure and statistics…")
        meta = await data_analysis.run(filepath)
        job_store.update_job(job.job_id, metadata=meta)

        # Stage 2 — Visualization Generation
        _update("visualizing", 30, "Selecting meaningful chart types…")
        chart_specs = await visualization_gen.run(meta)

        # Stage 3 — Code Generation + Execution (with feedback loop)
        _update("executing", 45, "Generating and rendering charts…")
        rendered_charts = []
        for i, spec in enumerate(chart_specs):
            _update(
                "executing",
                45 + int((i / len(chart_specs)) * 20),
                f"Rendering chart {i+1}/{len(chart_specs)}: {spec.title}",
            )
            rendered = await code_exec.run(spec, filepath, CHART_OUTPUT_DIR)
            rendered_charts.append(rendered)
        job_store.update_job(job.job_id, chart_specs=rendered_charts)

        # Stage 4 — Story Generation
        _update("generating", 70, "Crafting narrative ideas…")
        ideas = await story_gen.run(meta, rendered_charts)

        # Stage 5 — Story Execution (ranking + writing)
        _update("generating", 80, f"Writing {audience} narratives…")
        stories = await story_exec.run(ideas, audience=audience)
        job_store.update_job(job.job_id, stories=stories)

        # Stage 6 — Report Assembly
        _update("reporting", 92, "Assembling final report…")
        report_html = report_gen.run(meta, rendered_charts, stories)
        job_store.update_job(job.job_id, report_html=report_html)

        _update("done", 100, "Report ready.")

    except Exception as exc:
        tb = traceback.format_exc()
        job_store.update_job(
            job.job_id,
            status="error",
            progress=0,
            status_message="Pipeline failed.",
            error=str(exc),
        )
        raise
