"""Sandboxed-ish Python code runner. Runs as a subprocess with a timeout.

Note: This is *not* a security sandbox. It is fine for local instructor use
(the same model as the original Flask app), but should not be exposed to
untrusted clients without further hardening.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time

from fastapi import APIRouter

from app.models.schemas import RunCodeRequest, RunCodeResponse

router = APIRouter(prefix="/api", tags=["run"])


@router.post("/run_code", response_model=RunCodeResponse)
def run_code(req: RunCodeRequest) -> RunCodeResponse:
    code = req.code or ""
    stdin = req.stdin or ""
    timeout = max(0.5, min(30.0, req.timeout or 10.0))

    started = time.perf_counter()
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name

    try:
        result = subprocess.run(
            [sys.executable, path],
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return RunCodeResponse(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
            duration_ms=duration_ms,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return RunCodeResponse(
            success=False,
            output="",
            error=f"Execution timed out after {timeout:.1f}s.",
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return RunCodeResponse(
            success=False,
            output="",
            error=f"Failed to run: {e}",
            duration_ms=duration_ms,
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
