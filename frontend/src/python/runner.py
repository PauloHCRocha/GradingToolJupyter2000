"""Run student code. Loaded only inside the runner Web Worker — a separate
Pyodide instance from the app's, so student code can't touch session state
and an infinite loop can be killed by terminating the worker.

Interactive input works by replay: `input()` answers from the list of
inputs typed so far, and when that runs out the program is stopped and the
console asks the teacher for the next line. The program is then run again
from the start with one more input. A fixed random seed per console
session keeps the replays identical for programs that use `random`.
"""

from __future__ import annotations

import builtins
import io
import json
import linecache
import os
import random
import sys
import time
import traceback

# Plots have nowhere to go in a worker; make plt.show() a no-op.
os.environ.setdefault("MPLBACKEND", "Agg")

FILENAME = "<student_code>"
MAX_CHARS = 100_000
FLUSH_EVERY_S = 0.25


class NeedInput(BaseException):
    """The program asked for more input than it was given."""


class _Transcript:
    """Console output as segments: program output ("out"), errors ("err"),
    input() prompts ("prompt") and the typed answers ("in")."""

    def __init__(self, on_chunk=None):
        self.segments: list[dict] = []
        self.size = 0
        self.truncated = False
        self.on_chunk = on_chunk
        self.last_flush = time.perf_counter()

    def add(self, kind: str, text: str):
        if not text or self.truncated:
            return
        if self.size + len(text) > MAX_CHARS:
            text = text[: MAX_CHARS - self.size]
            self.truncated = True
        self.size += len(text)
        if self.segments and self.segments[-1]["kind"] == kind:
            self.segments[-1]["text"] += text
        else:
            self.segments.append({"kind": kind, "text": text})
        if self.truncated:
            self.segments.append({"kind": "err", "text": "\n[output truncated]\n"})
        self._maybe_flush()

    def _maybe_flush(self):
        # Snapshots let the console show what a program printed before it
        # was killed for running too long.
        now = time.perf_counter()
        if self.on_chunk is not None and now - self.last_flush >= FLUSH_EVERY_S:
            self.last_flush = now
            self.on_chunk(json.dumps(self.segments))


class _Stream(io.TextIOBase):
    def __init__(self, transcript: _Transcript, kind: str, halted):
        self._t = transcript
        self._kind = kind
        self._halted = halted

    def writable(self):
        return True

    def write(self, s):
        if self._halted():
            raise NeedInput()
        s = str(s)
        self._t.add(self._kind, s)
        return len(s)

    def flush(self):
        pass


def run_code(code, inputs=(), seed=0, on_chunk=None):
    if hasattr(inputs, "to_py"):
        inputs = inputs.to_py()
    queue = [str(x) for x in inputs]
    given = len(queue)
    transcript = _Transcript(on_chunk)
    halted = {"value": False}

    def stop_everywhere(frame, event, arg):
        # A bare `except:` around input() would swallow NeedInput and loop
        # forever. Once input has run out, every new line of the student's
        # code raises again, so the program unwinds whatever it catches.
        if event == "line" and frame.f_code.co_filename == FILENAME:
            raise NeedInput()
        return stop_everywhere

    def take(prompt=""):
        if not halted["value"]:
            transcript.add("prompt", "" if prompt is None else str(prompt))
        if not queue:
            halted["value"] = True
            frame = sys._getframe(1)
            while frame is not None:
                frame.f_trace = stop_everywhere
                frame = frame.f_back
            sys.settrace(stop_everywhere)
            raise NeedInput()
        value = queue.pop(0)
        transcript.add("in", value + "\n")
        return value

    class _Stdin(io.TextIOBase):
        def readable(self):
            return True

        def readline(self, size=-1):
            return take() + "\n"

        def read(self, size=-1):
            return take() + "\n"

    saved = (sys.stdin, sys.stdout, sys.stderr, builtins.input)
    sys.stdin = _Stdin()
    sys.stdout = _Stream(transcript, "out", lambda: halted["value"])
    sys.stderr = _Stream(transcript, "err", lambda: halted["value"])
    builtins.input = take
    random.seed(seed)
    # Lets tracebacks quote the student's lines.
    linecache.cache[FILENAME] = (len(code or ""), None, (code or "").splitlines(True), FILENAME)

    status = "done"
    started = time.perf_counter()
    try:
        exec(compile(code or "", FILENAME, "exec"), {"__name__": "__main__", "__builtins__": builtins})
    except NeedInput:
        status = "needs_input"
    except SystemExit as e:
        if e.code not in (None, 0):
            status = "error"
            if isinstance(e.code, str):
                transcript.add("err", e.code + "\n")
    except BaseException:
        status = "error"
        etype, value, tb = sys.exc_info()
        # Skip this module's own frame: only the student's code is relevant.
        traceback.print_exception(etype, value, tb.tb_next if tb else None)
    finally:
        sys.settrace(None)
        sys.stdin, sys.stdout, sys.stderr, builtins.input = saved

    if halted["value"]:
        # Whatever the program did after input ran out (it can't have done
        # anything useful) is not part of the transcript.
        status = "needs_input"
    return {
        "status": status,
        "segments": transcript.segments,
        "inputs_used": given - len(queue),
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }
