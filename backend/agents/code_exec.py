"""Code Execution Agent.
Uses deterministic chart engine first (always works).
Falls back to LLM code generation if needed.
"""
from __future__ import annotations
import asyncio
import logging
import os
import tempfile
import textwrap
from core.schemas import ChartSpec
from agents.chart_engine import render_chart
from agents import code_gen

logger = logging.getLogger(__name__)
MAX_LLM_RETRIES = 2
TIMEOUT_SECONDS = 45


async def _exec_llm_code(code: str, filepath: str, output_path: str) -> tuple[bool, str]:
    preamble = textwrap.dedent(f"""
import os
os.makedirs(os.path.dirname({repr(output_path)}) or '.', exist_ok=True)
filepath = {repr(filepath)}
output_path = {repr(output_path)}
""")
    full_code = preamble + "\n" + code
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(full_code)
        tmp_path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            proc.kill()
            return False, "Timed out after 45s"
        if proc.returncode != 0:
            return False, stderr.decode()
        return True, ""
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def run(spec: ChartSpec, filepath: str, output_dir: str) -> ChartSpec:
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{spec.chart_id}.html")

    # Step 1: Try deterministic engine (no LLM, always reliable)
    logger.info(f"Chart '{spec.title}': trying deterministic engine")
    success = render_chart(spec, filepath, output_path)

    if success and os.path.exists(output_path):
        with open(output_path) as f:
            spec.rendered_html = f.read()
        logger.info(f"Chart '{spec.title}': deterministic engine succeeded")
        return spec

    # Step 2: Fall back to LLM code generation
    logger.warning(f"Chart '{spec.title}': deterministic failed, trying LLM fallback")
    error: str | None = "Deterministic rendering failed, try a different approach."
    for attempt in range(MAX_LLM_RETRIES):
        code = await code_gen.run(spec, error=error)
        spec.plotly_code = code
        ok, error = await _exec_llm_code(code, filepath, output_path)
        if ok and os.path.exists(output_path):
            with open(output_path) as f:
                spec.rendered_html = f.read()
            logger.info(f"Chart '{spec.title}': LLM fallback succeeded on attempt {attempt+1}")
            return spec
        logger.warning(f"Chart '{spec.title}': LLM attempt {attempt+1} failed: {error[:200]}")

    # Step 3: Give up gracefully
    logger.error(f"Chart '{spec.title}': all methods failed")
    spec.rendered_html = (
        f"<div style='padding:2rem;color:#999;font-family:sans-serif;text-align:center'>"
        f"<div style='font-size:2rem;margin-bottom:1rem'>📊</div>"
        f"<b>{spec.title}</b><br><br>"
        f"<span style='font-size:12px;color:#bbb'>{spec.rationale}</span>"
        f"</div>"
    )
    return spec
