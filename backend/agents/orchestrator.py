"""Orchestrator — bulletproof pipeline with per-stage error recovery."""
from __future__ import annotations
import asyncio
import logging
import os
import traceback

from core import job_store
from core.schemas import AudienceMode, PipelineJob, DatasetMetadata, RankedStory, ChartSpec
from agents import (
    data_analysis, visualization_gen, story_gen,
    story_exec, code_exec, report_gen,
)

logger = logging.getLogger(__name__)
CHART_OUTPUT_DIR = "./chart_outputs"
AGENT_PAUSE = 5


async def run_pipeline(job: PipelineJob, filepath: str, audience: AudienceMode = "executive"):
    os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

    def _update(status, progress, message):
        logger.info(f"[{job.job_id}] {status} ({progress}%) — {message}")
        job_store.update_job(job.job_id, status=status, progress=progress, status_message=message)

    # Stage 1 — Data Analysis
    meta = None
    try:
        _update("analyzing", 10, "Analyzing dataset structure…")
        meta = await data_analysis.run(filepath)
        job_store.update_job(job.job_id, metadata=meta)
        logger.info(f"Analysis done: {meta.row_count} rows, domain={meta.inferred_domain}")
    except Exception as e:
        logger.error(f"Data analysis failed: {traceback.format_exc()}")
        job_store.update_job(job.job_id, status="error", progress=0,
                             status_message="Failed to read dataset.", error=str(e))
        return
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 2 — Visualization Generation
    chart_specs = []
    try:
        _update("visualizing", 28, "Selecting chart types…")
        chart_specs = await visualization_gen.run(meta)
        logger.info(f"Visualization gen: {len(chart_specs)} specs")
    except Exception as e:
        logger.error(f"Visualization gen failed: {e}")
        # Non-fatal — continue with empty charts
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 3 — Chart Rendering (deterministic, rarely fails)
    rendered_charts = []
    try:
        _update("executing", 40, f"Rendering {len(chart_specs)} charts…")
        for i, spec in enumerate(chart_specs):
            try:
                _update("executing", 40 + int((i / max(len(chart_specs), 1)) * 20),
                        f"Chart {i+1}/{len(chart_specs)}: {spec.title}")
                rendered = await code_exec.run(spec, filepath, CHART_OUTPUT_DIR)
                rendered_charts.append(rendered)
            except Exception as e:
                logger.error(f"Chart '{spec.title}' failed: {e}")
                spec.rendered_html = "<div style='padding:1rem;color:#aaa'>Chart unavailable</div>"
                rendered_charts.append(spec)
        job_store.update_job(job.job_id, chart_specs=rendered_charts)
    except Exception as e:
        logger.error(f"Chart rendering stage failed: {e}")
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 4 — Story Generation
    ideas = []
    try:
        _update("generating", 65, "Generating story ideas…")
        ideas = await story_gen.run(meta, rendered_charts)
        logger.info(f"Story gen: {len(ideas)} ideas")
    except Exception as e:
        logger.error(f"Story gen failed: {e}")
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 5 — Story Execution
    stories = []
    try:
        _update("generating", 78, f"Writing {audience} narratives…")
        if ideas:
            stories = await story_exec.run(ideas, audience=audience)
        logger.info(f"Story exec: {len(stories)} stories")
        job_store.update_job(job.job_id, stories=stories)
    except Exception as e:
        logger.error(f"Story exec failed: {e}")
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 6 — Report Assembly (never fails)
    try:
        _update("reporting", 92, "Assembling report…")
        report_html = report_gen.run(meta, rendered_charts, stories)
        job_store.update_job(job.job_id, report_html=report_html)
    except Exception as e:
        logger.error(f"Report gen failed: {e}")
        job_store.update_job(job.job_id, report_html="<p>Report generation failed.</p>")

    _update("done", 100, "Report ready.")
    logger.info(f"Pipeline complete: {job.job_id}")
