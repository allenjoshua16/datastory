"""Code Execution Agent — runs Plotly code with retry/feedback loop."""
from __future__ import annotations
import asyncio
import logging
import os
import tempfile
import textwrap
from core.schemas import ChartSpec
from agents import code_gen

logger = logging.getLogger(__name__)
MAX_RETRIES = 3
TIMEOUT_SECONDS = 45


async def _exec_code(code: str, filepath: str, output_path: str) -> tuple[bool, str]:
    preamble = textwrap.dedent(f"""
import os
os.makedirs(os.path.dirname({repr(output_path)}), exist_ok=True)
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
            return False, "Execution timed out after 45 seconds."

        if proc.returncode != 0:
            error_msg = stderr.decode()
            logger.warning(f"Chart code failed: {error_msg[:500]}")
            return False, error_msg
        return True, ""
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def run(spec: ChartSpec, filepath: str, output_dir: str) -> ChartSpec:
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{spec.chart_id}.html")
    error: str | None = None

    for attempt in range(MAX_RETRIES):
        logger.info(f"Chart '{spec.title}' attempt {attempt+1}/{MAX_RETRIES}")
        code = await code_gen.run(spec, error=error)
        spec.plotly_code = code
        success, error = await _exec_code(code, filepath, output_path)

        if success and os.path.exists(output_path):
            with open(output_path) as f:
                spec.rendered_html = f.read()
            logger.info(f"Chart '{spec.title}' rendered successfully")
            break
        logger.warning(f"Chart '{spec.title}' attempt {attempt+1} failed: {error[:200] if error else 'unknown'}")

    if not spec.rendered_html:
        logger.error(f"Chart '{spec.title}' failed after {MAX_RETRIES} attempts. Last error: {error}")
        spec.rendered_html = (
            f"<div style='padding:2rem;color:#888;font-family:monospace;font-size:12px'>"
            f"<b>Chart could not be rendered</b><br><br>"
            f"<i>{spec.title}</i><br><br>"
            f"Error: {error[:300] if error else 'Unknown error'}</div>"
        )
    return spec
