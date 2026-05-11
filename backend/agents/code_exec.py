"""Code Execution Agent.

Executes Plotly Python code in a sandboxed subprocess.
On failure, returns the error so Code Generation Agent can retry.
This is the core of the feedback loop.
"""
from __future__ import annotations
import asyncio
import os
import tempfile
import textwrap
from core.schemas import ChartSpec
from agents import code_gen

MAX_RETRIES = 3
TIMEOUT_SECONDS = 30


async def _exec_code(code: str, filepath: str, output_path: str) -> tuple[bool, str]:
    """Write code to a temp file and run it. Returns (success, error_or_empty)."""
    preamble = textwrap.dedent(f"""
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
            return False, "Execution timed out after 30 seconds."

        if proc.returncode != 0:
            return False, stderr.decode()
        return True, ""
    finally:
        os.unlink(tmp_path)


async def run(
    spec: ChartSpec,
    filepath: str,
    output_dir: str,
) -> ChartSpec:
    """Run code generation + execution loop. Returns spec with rendered_html filled."""
    output_path = os.path.join(output_dir, f"{spec.chart_id}.html")
    error: str | None = None

    for attempt in range(MAX_RETRIES):
        code = await code_gen.run(spec, error=error)
        spec.plotly_code = code

        success, error = await _exec_code(code, filepath, output_path)
        if success and os.path.exists(output_path):
            with open(output_path) as f:
                spec.rendered_html = f.read()
            break
        # Feed error back to code_gen on next iteration

    if not spec.rendered_html:
        # Fallback: empty placeholder so pipeline continues
        spec.rendered_html = (
            f"<div style='padding:2rem;color:#888'>"
            f"Chart '{spec.title}' could not be rendered after {MAX_RETRIES} attempts.</div>"
        )
    return spec
