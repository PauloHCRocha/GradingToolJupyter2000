"""Run student code. Loaded only inside the runner Web Worker — a separate
Pyodide instance from the app's, so student code can't touch session state
and an infinite loop can be killed by terminating the worker."""

from __future__ import annotations

import io
import os
import sys
import time
import traceback

# Plots have nowhere to go in a worker; make plt.show() a no-op.
os.environ.setdefault("MPLBACKEND", "Agg")


def run_code(code, stdin=""):
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    real_stdin = sys.stdin
    real_stdout = sys.stdout
    real_stderr = sys.stderr
    sys.stdin = io.StringIO(stdin or "")
    sys.stdout = out_buf
    sys.stderr = err_buf
    started = time.perf_counter()
    success = True
    try:
        exec(compile(code or "", "<student_code>", "exec"), {"__name__": "__main__"})
    except SystemExit as e:
        success = e.code in (None, 0)
    except BaseException:
        success = False
        traceback.print_exc(file=err_buf)
    finally:
        sys.stdin = real_stdin
        sys.stdout = real_stdout
        sys.stderr = real_stderr
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "success": success,
        "output": out_buf.getvalue(),
        "error": err_buf.getvalue(),
        "duration_ms": duration_ms,
    }
