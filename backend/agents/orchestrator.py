"""Orchestrator — runs all agents in sequence with detailed logging."""
from __future__ import annotations
import asyncio
import logging
import os
import traceback

from core import job_store
from core.schemas import AudienceMode, PipelineJob
from agents import (
    data_analysis, visualization_gen, story_gen,
    story_exec, code_exec, report_gen,
)

logger = logging.getLogger(__name__)
CHART_OUTPUT_DIR = "./chart_outputs"


async def run_pipeline(job: PipelineJob, filepath: str, audience: AudienceMode = "executive"):
    os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

    def _update(status, progress, message):
        logger.info(f"[{job.job_id}] {status} ({progress}%) — {message}")
        job_store.update_job(job.job_id, status=status, progress=progress, status_message=message)

    try:
        _update("analyzing", 10, "Analyzing dataset structure and statistics…")
        logger.info(f"Running data_analysis on {filepath}")
        meta = await data_analysis.run(filepath)
        logger.info(f"data_analysis done: {meta.row_count} rows, domain={meta.inferred_domain}")
        job_store.update_job(job.job_id, metadata=meta)

        _update("visualizing", 30, "Selecting meaningful chart types…")
        logger.info("Running visualization_gen")
        chart_specs = await visualization_gen.run(meta)
        logger.info(f"visualization_gen done: {len(chart_specs)} charts")

        _update("executing", 45, "Generating and rendering charts…")
        rendered_charts = []
        for i, spec in enumerate(chart_specs):
            _update("executing", 45 + int((i / len(chart_specs)) * 20),
                    f"Rendering chart {i+1}/{len(chart_specs)}: {spec.title}")
            logger.info(f"Running code_exec for chart: {spec.title}")
            rendered = await code_exec.run(spec, filepath, CHART_OUTPUT_DIR)
            rendered_charts.append(rendered)
        job_store.update_job(job.job_id, chart_specs=rendered_charts)

        _update("generating", 70, "Crafting narrative ideas…")
        logger.info("Running story_gen")
        ideas = await story_gen.run(meta, rendered_charts)
        logger.info(f"story_gen done: {len(ideas)} ideas")

        _update("generating", 80, f"Writing {audience} narratives…")
        logger.info("Running story_exec")
        stories = await story_exec.run(ideas, audience=audience)
        logger.info(f"story_exec done: {len(stories)} stories")
        job_store.update_job(job.job_id, stories=stories)

        _update("reporting", 92, "Assembling final report…")
        logger.info("Running report_gen")
        report_html = report_gen.run(meta, rendered_charts, stories)
        job_store.update_job(job.job_id, report_html=report_html)

        _update("done", 100, "Report ready.")
        logger.info(f"Pipeline complete for job {job.job_id}")

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"Pipeline failed for job {job.job_id}:\n{tb}")
        job_store.update_job(job.job_id, status="error", progress=0,
                             status_message="Pipeline failed.", error=str(exc))
        raise
