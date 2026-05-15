"""Utility functions — safe JSON serialization."""
from __future__ import annotations
import math
import json
from typing import Any


def safe_float(val) -> float | None:
    """Convert to float, return None for nan/inf."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except (TypeError, ValueError):
        return None


def sanitize(obj: Any) -> Any:
    """Recursively sanitize any object for JSON serialization.
    Converts nan/inf → None, non-serializable types → str.
    """
    if obj is None:
        return None
    if isinstance(obj, float):
        return safe_float(obj)
    if isinstance(obj, (int, str, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    # numpy types
    try:
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return safe_float(float(obj))
        if isinstance(obj, np.ndarray):
            return [sanitize(v) for v in obj.tolist()]
        if isinstance(obj, np.bool_):
            return bool(obj)
    except ImportError:
        pass
    # pandas NA/NaT
    try:
        import pandas as pd
        if pd.isna(obj):
            return None
    except (ImportError, TypeError, ValueError):
        pass
    # fallback
    try:
        return str(obj)
    except Exception:
        return None


def safe_json_response(data: Any) -> dict:
    """Sanitize entire response dict for safe JSON serialization."""
    return sanitize(data)
