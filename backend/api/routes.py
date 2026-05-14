"""FastAPI routes — upload, preprocessing, job status, WebSocket, results."""
from __future__ import annotations
import asyncio
import json
import os
import uuid
from typing import Annotated

from fastapi import (
    APIRouter, BackgroundTasks, File, Form,
    HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse

from core import job_store
from core.config import get_settings
from core.schemas import (
    AudienceMode, JobResultResponse, JobStatusResponse,
    PipelineJob, UploadResponse,
)
from agents.orchestrator import run_pipeline

router = APIRouter()
settings = get_settings()

ACCEPTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".xlsm", ".json", ".tsv", ".parquet", ".docx"}


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    audience: AudienceMode = Form(default="executive"),
    preprocess: bool = Form(default=False),
):
    content = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_file_size_mb} MB limit.")

    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ACCEPTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Accepted: {', '.join(ACCEPTED_EXTENSIONS)}")

    os.makedirs(settings.upload_dir, exist_ok=True)
    job_id = str(uuid.uuid4())
    save_path = os.path.join(settings.upload_dir, f"{job_id}{ext}")
    with open(save_path, "wb") as f:
        f.write(content)

    job = PipelineJob(job_id=job_id, filename=filename, preprocess=preprocess)
    job_store.create_job(job)
    background_tasks.add_task(run_pipeline, job, save_path, audience)

    msg = "Preprocessing + analysis pipeline started." if preprocess else "Analysis pipeline started."
    return UploadResponse(job_id=job_id, filename=filename, message=msg)


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return JobStatusResponse(
        job_id=job.job_id, status=job.status,
        progress=job.progress, status_message=job.status_message,
        error=job.error,
    )


@router.get("/jobs/{job_id}/results", response_model=JobResultResponse)
async def get_job_results(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status not in {"done", "error"}:
        raise HTTPException(202, "Job still processing.")
    return JobResultResponse(
        job_id=job.job_id,
        metadata=job.metadata,
        chart_specs=job.chart_specs,
        stories=job.stories,
        report_html=job.report_html,
        preprocessing_report=job.preprocessing_report,
    )


@router.get("/jobs/{job_id}/preprocess-report")
async def get_preprocess_report(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if not job.preprocessing_report:
        raise HTTPException(404, "No preprocessing report for this job.")
    return job.preprocessing_report


@router.get("/jobs/{job_id}/cleaned")
async def download_cleaned(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if not job.clean_filepath or not os.path.exists(job.clean_filepath):
        raise HTTPException(404, "Cleaned file not available. Run with preprocess=true.")
    base = os.path.splitext(job.filename)[0]
    return FileResponse(
        path=job.clean_filepath,
        media_type="text/csv",
        filename=f"{base}_cleaned.csv",
    )


@router.websocket("/ws/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = job_store.get_job(job_id)
    if not job:
        await websocket.send_text(json.dumps({"error": "Job not found"}))
        await websocket.close()
        return

    await websocket.send_text(json.dumps({
        "status": job.status, "progress": job.progress,
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
                    "status": update["status"],
                    "progress": update["progress"],
                    "message": update["status_message"],
                    "error": update.get("error"),
                }))
                if update["status"] in {"done", "error"}:
                    break
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"ping": True}))
    except WebSocketDisconnect:
        pass
    finally:
        job_store.unsubscribe(job_id, q)
        await websocket.close()


@router.get("/jobs/{job_id}/report", response_class=HTMLResponse)
async def get_report(job_id: str):
    job = job_store.get_job(job_id)
    if not job or job.status != "done":
        raise HTTPException(404, "Report not ready.")
    return HTMLResponse(job.report_html)
