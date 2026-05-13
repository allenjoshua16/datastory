"""Orchestrator — runs all agents in sequence with pacing to avoid rate limits."""
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
AGENT_PAUSE = 3  # seconds between LLM agent calls to avoid rate limits


async def run_pipeline(job: PipelineJob, filepath: str, audience: AudienceMode = "executive"):
    os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

    def _update(status, progress, message):
        logger.info(f"[{job.job_id}] {status} ({progress}%) — {message}")
        job_store.update_job(job.job_id, status=status, progress=progress, status_message=message)

    try:
        # Stage 1 — Data Analysis
        _update("analyzing", 10, "Analyzing dataset…")
        meta = await data_analysis.run(filepath)
        logger.info(f"Domain: {meta.inferred_domain}, rows: {meta.row_count}")
        job_store.update_job(job.job_id, metadata=meta)
        await asyncio.sleep(AGENT_PAUSE)

        # Stage 2 — Visualization Generation
        _update("visualizing", 28, "Selecting chart types…")
        chart_specs = await visualization_gen.run(meta)
        logger.info(f"Generated {len(chart_specs)} chart specs")
        await asyncio.sleep(AGENT_PAUSE)

        # Stage 3 — Chart Rendering (deterministic — no rate limit risk)
        _update("executing", 40, "Rendering charts…")
        rendered_charts = []
        for i, spec in enumerate(chart_specs):
            _update("executing", 40 + int((i / len(chart_specs)) * 20),
                    f"Rendering chart {i+1}/{len(chart_specs)}: {spec.title}")
            rendered = await code_exec.run(spec, filepath, CHART_OUTPUT_DIR)
            rendered_charts.append(rendered)
        job_store.update_job(job.job_id, chart_specs=rendered_charts)
        await asyncio.sleep(AGENT_PAUSE)

        # Stage 4 — Story Generation
        _update("generating", 65, "Crafting narrative ideas…")
        ideas = await story_gen.run(meta, rendered_charts)
        logger.info(f"Generated {len(ideas)} story ideas")
        await asyncio.sleep(AGENT_PAUSE)

        # Stage 5 — Story Execution
        _update("generating", 78, f"Writing {audience} narratives…")
        stories = await story_exec.run(ideas, audience=audience)
        logger.info(f"Wrote {len(stories)} stories")
        job_store.update_job(job.job_id, stories=stories)
        await asyncio.sleep(AGENT_PAUSE)

        # Stage 6 — Report Assembly
        _update("reporting", 92, "Assembling report…")
        report_html = report_gen.run(meta, rendered_charts, stories)
        job_store.update_job(job.job_id, report_html=report_html)

        _update("done", 100, "Report ready.")
        logger.info(f"Pipeline complete: {job.job_id}")

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"Pipeline failed [{job.job_id}]:\n{tb}")
        job_store.update_job(
            job.job_id, status="error", progress=0,
            status_message="Pipeline failed.", error=str(exc),
        )
        raise
