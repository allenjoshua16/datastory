"""In-memory job store with proper cleanup."""
from __future__ import annotations
import asyncio
import logging
from core.schemas import PipelineJob, PipelineStatus

logger = logging.getLogger(__name__)

_store: dict[str, PipelineJob] = {}
_listeners: dict[str, list[asyncio.Queue]] = {}


def create_job(job: PipelineJob) -> None:
    _store[job.job_id] = job
    _listeners[job.job_id] = []


def get_job(job_id: str) -> PipelineJob | None:
    return _store.get(job_id)


def update_job(job_id: str, **kwargs) -> PipelineJob | None:
    job = _store.get(job_id)
    if not job:
        logger.warning(f"update_job: job {job_id} not found")
        return None
    for k, v in kwargs.items():
        try:
            setattr(job, k, v)
        except Exception as e:
            logger.warning(f"update_job: could not set {k}: {e}")
    _broadcast(job_id, job)
    return job


def subscribe(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _listeners.setdefault(job_id, []).append(q)
    return q


def unsubscribe(job_id: str, q: asyncio.Queue) -> None:
    listeners = _listeners.get(job_id, [])
    if q in listeners:
        listeners.remove(q)
    # Clean up empty listener lists for finished jobs
    job = _store.get(job_id)
    if job and job.status in {"done", "error"} and not listeners:
        _listeners.pop(job_id, None)


def _broadcast(job_id: str, job: PipelineJob) -> None:
    dead = []
    for q in _listeners.get(job_id, []):
        try:
            q.put_nowait(job.model_dump())
        except asyncio.QueueFull:
            logger.warning(f"Queue full for job {job_id}, dropping update")
        except Exception as e:
            logger.warning(f"Broadcast error for job {job_id}: {e}")
            dead.append(q)
    for q in dead:
        listeners = _listeners.get(job_id, [])
        if q in listeners:
            listeners.remove(q)
