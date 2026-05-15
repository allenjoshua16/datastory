"""FastAPI routes — airtight error handling, nan-safe serialization."""
from __future__ import annotations
import asyncio
import json
import logging
import os
import uuid
from typing import Annotated

from fastapi import (
    APIRouter, BackgroundTasks, File, Form,
    HTTPException, UploadFile, WebSocket, WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from core import job_store
from core.config import get_settings
from core.schemas import AudienceMode, PipelineJob, UploadResponse
from core.utils import sanitize
from agents.orchestrator import run_pipeline

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

ACCEPTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".xlsm"}
ACCEPTED_DISPLAY    = "CSV (.csv) or Excel (.xlsx, .xls, .xlsm)"


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    audience: AudienceMode = Form(default="executive"),
    preprocess: bool = Form(default=False),
):
    try:
        content = await file.read()
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(413, f"File exceeds {settings.max_file_size_mb} MB limit.")

        filename = file.filename or "upload"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ACCEPTED_EXTENSIONS:
            raise HTTPException(
                400,
                f"Unsupported file type '{ext}'. Please upload a {ACCEPTED_DISPLAY} file."
            )

        os.makedirs(settings.upload_dir, exist_ok=True)
        job_id  = str(uuid.uuid4())
        save_path = os.path.join(settings.upload_dir, f"{job_id}{ext}")
        with open(save_path, "wb") as f:
            f.write(content)

        job = PipelineJob(job_id=job_id, filename=filename, preprocess=preprocess)
        job_store.create_job(job)
        background_tasks.add_task(run_pipeline, job, save_path, audience)

        return UploadResponse(
            job_id=job_id, filename=filename,
            message="Preprocessing + analysis started." if preprocess else "Analysis started."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload failed", exc_info=True)
        raise HTTPException(500, f"Upload error: {e}")


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    try:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        return JSONResponse(content=sanitize({
            "job_id":         job.job_id,
            "status":         job.status,
            "progress":       job.progress,
            "status_message": job.status_message,
            "error":          job.error,
        }))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Status endpoint failed", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ── Results ───────────────────────────────────────────────────────────────────

def _serialize_chart(c) -> dict:
    return {
        "chart_id":          str(c.chart_id or "unknown"),
        "chart_type":        str(c.chart_type or "bar"),
        "title":             str(c.title or "Untitled"),
        "x_column":          c.x_column,
        "y_column":          c.y_column,
        "color_column":      c.color_column,
        "rationale":         str(c.rationale or ""),
        "rendered_html":     str(c.rendered_html or ""),
        "plotly_code":       "",
        "available_columns": list(c.available_columns or []),
    }


def _serialize_story(s) -> dict:
    return {
        "title":              str(s.title or ""),
        "hook":               str(s.hook or ""),
        "context":            str(s.context or ""),
        "dispute":            str(s.dispute or ""),
        "solution":           str(s.solution or ""),
        "relevant_chart_ids": list(s.relevant_chart_ids or []),
        "score":              float(s.score) if s.score is not None else 0.0,
        "audience_mode":      str(s.audience_mode or "general"),
        "narrative_text":     str(s.narrative_text or ""),
    }


def _serialize_metadata(meta) -> dict | None:
    if not meta:
        return None
    columns = []
    for c in (meta.columns or []):
        columns.append(sanitize({
            "name":           c.name,
            "dtype":          c.dtype,
            "non_null_count": c.non_null_count,
            "null_count":     c.null_count,
            "unique_count":   c.unique_count,
            "sample_values":  c.sample_values,
            "mean":           c.mean,
            "std":            c.std,
            "min":            c.min,
            "max":            c.max,
            "median":         c.median,
        }))
    return sanitize({
        "row_count":       meta.row_count,
        "column_count":    meta.column_count,
        "columns":         columns,
        "correlations":    meta.correlations,
        "anomalies":       meta.anomalies,
        "inferred_domain": meta.inferred_domain,
    })


@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    try:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        if job.status not in {"done", "error"}:
            return JSONResponse(status_code=202, content={"detail": "Job still processing."})

        charts = []
        for c in (job.chart_specs or []):
            try:
                charts.append(sanitize(_serialize_chart(c)))
            except Exception as e:
                logger.warning(f"Chart serialize failed: {e}")

        stories = []
        for s in (job.stories or []):
            try:
                stories.append(sanitize(_serialize_story(s)))
            except Exception as e:
                logger.warning(f"Story serialize failed: {e}")

        meta = None
        try:
            meta = _serialize_metadata(job.metadata)
        except Exception as e:
            logger.warning(f"Metadata serialize failed: {e}")

        pp_report = None
        try:
            if job.preprocessing_report:
                pp_report = sanitize(
                    job.preprocessing_report.model_dump()
                    if hasattr(job.preprocessing_report, "model_dump")
                    else job.preprocessing_report.__dict__
                )
        except Exception as e:
            logger.warning(f"Preprocessing report serialize failed: {e}")

        payload = sanitize({
            "job_id":               job.job_id,
            "metadata":             meta,
            "chart_specs":          charts,
            "stories":              stories,
            "report_html":          job.report_html or "",
            "preprocessing_report": pp_report,
        })

        return JSONResponse(content=payload)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Results endpoint failed", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={"Access-Control-Allow-Origin": "*"},
        )


# ── Other endpoints ───────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/preprocess-report")
async def get_preprocess_report(job_id: str):
    try:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        if not job.preprocessing_report:
            raise HTTPException(404, "No preprocessing report.")
        data = job.preprocessing_report.model_dump() \
            if hasattr(job.preprocessing_report, "model_dump") \
            else job.preprocessing_report.__dict__
        return JSONResponse(content=sanitize(data))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Preprocess report failed", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/jobs/{job_id}/cleaned")
async def download_cleaned(job_id: str):
    try:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        if not job.clean_filepath or not os.path.exists(job.clean_filepath):
            raise HTTPException(404, "Cleaned file not available.")
        base = os.path.splitext(job.filename)[0]
        return FileResponse(
            path=job.clean_filepath,
            media_type="text/csv",
            filename=f"{base}_cleaned.csv",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Download cleaned failed", exc_info=True)
        raise HTTPException(500, str(e))


@router.websocket("/ws/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    try:
        await websocket.accept()
        job = job_store.get_job(job_id)
        if not job:
            await websocket.send_text(json.dumps({"error": "Job not found"}))
            await websocket.close()
            return

        await websocket.send_text(json.dumps(sanitize({
            "status":   job.status,
            "progress": job.progress,
            "message":  job.status_message,
        })))

        if job.status in {"done", "error"}:
            await websocket.close()
            return

        q = job_store.subscribe(job_id)
        try:
            while True:
                try:
                    update = await asyncio.wait_for(q.get(), timeout=30)
                    await websocket.send_text(json.dumps(sanitize({
                        "status":   update.get("status"),
                        "progress": update.get("progress", 0),
                        "message":  update.get("status_message", ""),
                        "error":    update.get("error"),
                    })))
                    if update.get("status") in {"done", "error"}:
                        break
                except asyncio.TimeoutError:
                    await websocket.send_text(json.dumps({"ping": True}))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket stream error: {e}")
        finally:
            job_store.unsubscribe(job_id, q)
            try:
                await websocket.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")


@router.get("/jobs/{job_id}/report", response_class=HTMLResponse)
async def get_report(job_id: str):
    try:
        job = job_store.get_job(job_id)
        if not job or job.status != "done":
            raise HTTPException(404, "Report not ready.")
        return HTMLResponse(job.report_html or "<p>No report generated.</p>")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Report endpoint failed", exc_info=True)
        raise HTTPException(500, str(e))
