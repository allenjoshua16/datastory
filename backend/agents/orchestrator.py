"""Orchestrator — full pipeline with optional preprocessing."""
from __future__ import annotations
import asyncio
import logging
import os
import traceback

from core import job_store
from core.schemas import AudienceMode, PipelineJob, PreprocessingReport
from agents import (
    preprocess as preprocess_agent,
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

    analysis_filepath = filepath

    # Stage 0 — Optional Preprocessing
    if job.preprocess:
        try:
            _update("preprocessing", 5, "Preprocessing dataset…")
            clean_path, pp_report = await preprocess_agent.run(filepath, output_dir="./uploads")
            report_model = PreprocessingReport(**pp_report.to_dict())
            job_store.update_job(
                job.job_id,
                clean_filepath=clean_path,
                preprocessing_report=report_model,
                status_message="Preprocessing complete.",
            )
            analysis_filepath = clean_path
            logger.info(f"Preprocessing done: {pp_report.row_count_before}→{pp_report.row_count_after} rows")
        except Exception as e:
            logger.error(f"Preprocessing failed: {traceback.format_exc()}")
            _update("preprocessing", 5, f"Preprocessing failed, using original: {str(e)[:100]}")
            await asyncio.sleep(2)
        await asyncio.sleep(AGENT_PAUSE)

    # Stage 1 — Data Analysis
    meta = None
    try:
        _update("analyzing", 15, "Analyzing dataset structure…")
        meta = await data_analysis.run(analysis_filepath)
        job_store.update_job(job.job_id, metadata=meta)
        logger.info(f"Analysis: {meta.row_count} rows, domain={meta.inferred_domain}")
    except Exception as e:
        logger.error(f"Data analysis failed: {traceback.format_exc()}")
        job_store.update_job(job.job_id, status="error", progress=0,
                             status_message="Failed to read dataset.", error=str(e))
        return
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 2 — Visualization Generation
    chart_specs = []
    try:
        _update("visualizing", 30, "Selecting chart types…")
        chart_specs = await visualization_gen.run(meta)
    except Exception as e:
        logger.error(f"Visualization gen failed: {e}")
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 3 — Chart Rendering
    rendered_charts = []
    try:
        _update("executing", 42, f"Rendering {len(chart_specs)} charts…")
        for i, spec in enumerate(chart_specs):
            try:
                _update("executing", 42 + int((i / max(len(chart_specs), 1)) * 18),
                        f"Chart {i+1}/{len(chart_specs)}: {spec.title}")
                rendered = await code_exec.run(spec, analysis_filepath, CHART_OUTPUT_DIR)
                rendered_charts.append(rendered)
            except Exception as e:
                logger.error(f"Chart '{spec.title}' failed: {e}")
                spec.rendered_html = "<div style='padding:1rem;color:#aaa;text-align:center'>Chart unavailable</div>"
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
    except Exception as e:
        logger.error(f"Story gen failed: {e}")
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 5 — Story Execution
    stories = []
    try:
        _update("generating", 78, f"Writing {audience} narratives…")
        if ideas:
            stories = await story_exec.run(ideas, audience=audience)
        job_store.update_job(job.job_id, stories=stories)
    except Exception as e:
        logger.error(f"Story exec failed: {e}")
    await asyncio.sleep(AGENT_PAUSE)

    # Stage 6 — Report Assembly
    try:
        _update("reporting", 93, "Assembling report…")
        pp_report = job_store.get_job(job.job_id).preprocessing_report
        report_html = report_gen.run(meta, rendered_charts, stories, pp_report)
        job_store.update_job(job.job_id, report_html=report_html)
    except Exception as e:
        logger.error(f"Report gen failed: {e}")
        job_store.update_job(job.job_id, report_html="<p>Report generation failed.</p>")

    _update("done", 100, "Report ready.")
    logger.info(f"Pipeline complete: {job.job_id}")
