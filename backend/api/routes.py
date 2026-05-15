"""FastAPI routes — CSV and Excel only."""
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
from agents.orchestrator import run_pipeline

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

# Restricted to CSV and Excel only
ACCEPTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".xlsm"}
ACCEPTED_DISPLAY    = "CSV (.csv) or Excel (.xlsx, .xls, .xlsm)"


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
        job_id = str(uuid.uuid4())
        save_path = os.path.join(settings.upload_dir, f"{job_id}{ext}")
        with open(save_path, "wb") as f:
            f.write(content)

        job = PipelineJob(job_id=job_id, filename=filename, preprocess=preprocess)
        job_store.create_job(job)
        background_tasks.add_task(run_pipeline, job, save_path, audience)

        msg = "Preprocessing + analysis started." if preprocess else "Analysis started."
        return UploadResponse(job_id=job_id, filename=filename, message=msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    try:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        return JSONResponse(content={
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "status_message": job.status_message,
            "error": job.error,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    try:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        if job.status not in {"done", "error"}:
            return JSONResponse(status_code=202, content={"detail": "Job still processing."})

        pp_report = None
        if job.preprocessing_report:
            try:
                pp_report = job.preprocessing_report.model_dump()
            except Exception as e:
                logger.warning(f"pp_report serialize failed: {e}")

        charts = []
        for c in (job.chart_specs or []):
            try:
                charts.append({
                    "chart_id":        c.chart_id or "unknown",
                    "chart_type":      c.chart_type or "bar",
                    "title":           c.title or "Untitled",
                    "x_column":        c.x_column,
                    "y_column":        c.y_column,
                    "color_column":    c.color_column,
                    "rationale":       c.rationale or "",
                    "rendered_html":   c.rendered_html or "",
                    "plotly_code":     "",
                    "available_columns": c.available_columns or [],
                })
            except Exception as e:
                logger.warning(f"chart serialize failed: {e}")

        stories = []
        for s in (job.stories or []):
            try:
                stories.append({
                    "title":              s.title or "",
                    "hook":               s.hook or "",
                    "context":            s.context or "",
                    "dispute":            s.dispute or "",
                    "solution":           s.solution or "",
                    "relevant_chart_ids": s.relevant_chart_ids or [],
                    "score":              float(s.score or 0.0),
                    "audience_mode":      s.audience_mode or "general",
                    "narrative_text":     s.narrative_text or "",
                })
            except Exception as e:
                logger.warning(f"story serialize failed: {e}")

        meta = None
        if job.metadata:
            try:
                meta = job.metadata.model_dump()
            except Exception as e:
                logger.warning(f"metadata serialize failed: {e}")

        return JSONResponse(content={
            "job_id":               job.job_id,
            "metadata":             meta,
            "chart_specs":          charts,
            "stories":              stories,
            "report_html":          job.report_html or "",
            "preprocessing_report": pp_report,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Results error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={"Access-Control-Allow-Origin": "*"},
        )


@router.get("/jobs/{job_id}/preprocess-report")
async def get_preprocess_report(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if not job.preprocessing_report:
        raise HTTPException(404, "No preprocessing report.")
    try:
        return job.preprocessing_report.model_dump()
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/jobs/{job_id}/cleaned")
async def download_cleaned(job_id: str):
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


@router.websocket("/ws/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    try:
        await websocket.accept()
        job = job_store.get_job(job_id)
        if not job:
            await websocket.send_text(json.dumps({"error": "Job not found"}))
            await websocket.close()
            return

        await websocket.send_text(json.dumps({
            "status": job.status,
            "progress": job.progress,
            "message": job.status_message,
        }))

        if job.status in {"done", "error"}:
            await websocket.close()
            return

        q = job_store.subscribe(job_id)
        try:
            while True:
                try:
                    update = await asyncio.wait_for(q.get(), timeout=30)
                    await websocket.send_text(json.dumps({
                        "status":   update.get("status"),
                        "progress": update.get("progress", 0),
                        "message":  update.get("status_message", ""),
                        "error":    update.get("error"),
                    }))
                    if update.get("status") in {"done", "error"}:
                        break
                except asyncio.TimeoutError:
                    await websocket.send_text(json.dumps({"ping": True}))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
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
    job = job_store.get_job(job_id)
    if not job or job.status != "done":
        raise HTTPException(404, "Report not ready.")
    return HTMLResponse(job.report_html or "<p>No report generated.</p>")
