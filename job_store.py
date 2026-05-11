"""Simple in-memory job store.  Replace with Redis for multi-worker deploys."""
from __future__ import annotations
import asyncio
from typing import Callable
from core.schemas import PipelineJob, PipelineStatus


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
        return None
    for k, v in kwargs.items():
        setattr(job, k, v)
    _broadcast(job_id, job)
    return job


def subscribe(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _listeners.setdefault(job_id, []).append(q)
    return q


def unsubscribe(job_id: str, q: asyncio.Queue) -> None:
    listeners = _listeners.get(job_id, [])
    if q in listeners:
        listeners.remove(q)


def _broadcast(job_id: str, job: PipelineJob) -> None:
    for q in _listeners.get(job_id, []):
        try:
            q.put_nowait(job.model_dump())
        except asyncio.QueueFull:
            pass
