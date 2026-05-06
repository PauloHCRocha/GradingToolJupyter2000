"""Detect questions and their max points in a solution file.

Supports two source types:
- Jupyter notebooks (.ipynb): scans markdown cells.
- Python scripts (.py): scans comments and docstrings.

The detector returns a flat list of questions. A question may be a top-level
"Question N" or a sub-question like "Q1-1". Sub-questions, when present,
take precedence over their parent for grading purposes.
"""

import ast
import json
import re
from dataclasses import dataclass, field

# Patterns ordered most-specific first.
SUB_QUESTION_PATTERN = re.compile(
    r"\bQ\s*(\d+)\s*[-.]\s*(\d+)\b", re.IGNORECASE
)
TOP_QUESTION_PATTERN = re.compile(
    r"\b(?:Question|Q)\s*(\d+)\b(?!\s*[-.]\s*\d)", re.IGNORECASE
)
POINTS_PATTERN = re.compile(
    r"\(\s*(\d+(?:\.\d+)?)\s*(?:point|pt)s?\s*\)", re.IGNORECASE
)


@dataclass
class _Hit:
    qid: str
    label: str
    statement: str
    points: float | None = None
    cell_indices: list[int] = field(default_factory=list)


def _extract_points(text: str) -> float | None:
    match = POINTS_PATTERN.search(text)
    return float(match.group(1)) if match else None


def _scan_text_block(text: str, cell_index: int) -> list[_Hit]:
    """Find all question markers inside a single block of text.

    Points are extracted from the text *between this marker and the next one*,
    so a parent "Question 1 (4 points)" doesn't leak its score onto the
    sub-question "Q1-1 (2 points)" that follows it in the same block.
    """
    markers: list[tuple[int, str, str]] = []  # (position, qid, label)

    for m in SUB_QUESTION_PATTERN.finditer(text):
        qid = f"Q{m.group(1)}-{m.group(2)}"
        markers.append((m.start(), qid, qid))

    for m in TOP_QUESTION_PATTERN.finditer(text):
        qid = f"Q{m.group(1)}"
        markers.append((m.start(), qid, f"Question {m.group(1)}"))

    markers.sort()

    hits: list[_Hit] = []
    for i, (start, qid, label) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        local = text[start:end]
        hits.append(_Hit(
            qid=qid,
            label=label,
            statement=local.strip(),
            points=_extract_points(local),
            cell_indices=[cell_index],
        ))

    return hits


def _merge_hits(hits: list[_Hit]) -> list[_Hit]:
    """Deduplicate by qid (first occurrence wins, but accumulate cell indices)."""
    by_id: dict[str, _Hit] = {}
    for h in hits:
        existing = by_id.get(h.qid)
        if existing is None:
            by_id[h.qid] = h
        else:
            existing.cell_indices.extend(h.cell_indices)
            if existing.points is None and h.points is not None:
                existing.points = h.points

    # If any sub-questions exist for a parent QN, drop the parent QN itself.
    sub_parents = {qid.split("-")[0] for qid in by_id if "-" in qid}
    for parent in sub_parents:
        by_id.pop(parent, None)

    def sort_key(qid: str) -> tuple[int, int]:
        parts = qid.lstrip("Qq").split("-")
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)

    return [by_id[qid] for qid in sorted(by_id, key=sort_key)]


def detect_in_notebook(notebook_bytes: bytes) -> list[_Hit]:
    notebook = json.loads(notebook_bytes.decode("utf-8"))
    hits: list[_Hit] = []
    for idx, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "markdown":
            continue
        source = cell.get("source", "")
        text = source if isinstance(source, str) else "".join(source)
        hits.extend(_scan_text_block(text, idx))
    return _merge_hits(hits)


def detect_in_python(source_bytes: bytes) -> list[_Hit]:
    source = source_bytes.decode("utf-8", errors="replace")
    hits: list[_Hit] = []

    for line_no, line in enumerate(source.splitlines()):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            hits.extend(_scan_text_block(stripped.lstrip("#").strip(), line_no))

    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            doc = ast.get_docstring(node) if isinstance(
                node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ) else None
            if doc:
                hits.extend(_scan_text_block(doc, getattr(node, "lineno", 0) or 0))

    return _merge_hits(hits)


def detect(filename: str, content: bytes) -> tuple[str, list[_Hit]]:
    """Return (file_type, hits) for the given file."""
    lower = filename.lower()
    if lower.endswith(".ipynb"):
        return "ipynb", detect_in_notebook(content)
    if lower.endswith(".py"):
        return "py", detect_in_python(content)
    raise ValueError(f"Unsupported file type: {filename}")
