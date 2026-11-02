"""Detect questions and their max points in a solution file."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from notebook_parser import _DECORATION, QUESTION_HEADER, Cell, parse_metadata, parse_notebook, parse_python

SUB_QUESTION_PATTERN = re.compile(r"\bQ\s*(\d+)\s*[-.]\s*(\d+)\b", re.IGNORECASE)
TOP_QUESTION_PATTERN = re.compile(r"\b(?:Question|Q)\s*(\d+)\b(?!\s*[-.]\s*\d)", re.IGNORECASE)
POINTS_PATTERN = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*(?:point|pt)s?\s*\)", re.IGNORECASE)


@dataclass
class Hit:
    qid: str
    label: str
    statement: str
    points: float | None = None
    cell_indices: list[int] = field(default_factory=list)


def _extract_points(text: str):
    match = POINTS_PATTERN.search(text)
    return float(match.group(1)) if match else None


def _scan_text_block(text: str, cell_index: int) -> list[Hit]:
    markers: list[tuple[int, str, str]] = []
    for m in SUB_QUESTION_PATTERN.finditer(text):
        qid = f"Q{m.group(1)}-{m.group(2)}"
        markers.append((m.start(), qid, qid))
    for m in TOP_QUESTION_PATTERN.finditer(text):
        qid = f"Q{m.group(1)}"
        markers.append((m.start(), qid, f"Question {m.group(1)}"))
    markers.sort()

    hits: list[Hit] = []
    for i, (start, qid, label) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        local = text[start:end]
        hits.append(
            Hit(
                qid=qid,
                label=label,
                statement=local.strip(),
                points=_extract_points(local),
                cell_indices=[cell_index],
            )
        )
    return hits


def _merge_hits(hits: list[Hit]) -> list[Hit]:
    by_id: dict[str, Hit] = {}
    for h in hits:
        existing = by_id.get(h.qid)
        if existing is None:
            by_id[h.qid] = h
        else:
            existing.cell_indices.extend(h.cell_indices)
            if existing.points is None and h.points is not None:
                existing.points = h.points

    sub_parents = {qid.split("-")[0] for qid in by_id if "-" in qid}
    for parent in sub_parents:
        by_id.pop(parent, None)

    def sort_key(qid: str):
        parts = qid.lstrip("Qq").split("-")
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)

    return [by_id[qid] for qid in sorted(by_id, key=sort_key)]


def detect_in_notebook(content) -> list[Hit]:
    return detect_in_cells(parse_notebook(content), "ipynb")


def _code_header(source: str) -> str:
    """Leading comment block (and a docstring right after it) of a .py cell,
    with the comment markers stripped."""
    out: list[str] = []
    lines = source.splitlines()
    i = 0
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
        if not _DECORATION.match(lines[i].strip()):  # skip "# =====" rulers
            out.append(lines[i].lstrip().lstrip("#").strip())
        i += 1
    if i < len(lines):
        m = re.match(r"\s*[rRuU]?(\"\"\"|\'\'\')", lines[i])
        if m:
            quote = m.group(1)
            rest = lines[i][m.end():]
            while True:
                if quote in rest:
                    out.append(rest.split(quote, 1)[0])
                    break
                out.append(rest)
                i += 1
                if i >= len(lines):
                    break
                rest = lines[i]
    return "\n".join(out).strip()


_ID_VALUE = re.compile(r"^\D{0,12}?(\d+)(?:\s*[.\-]\s*(\d+))?")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _metadata_hit(meta: dict, idx: int) -> Hit:
    """Hit from an "ID: / Label: / Grade:" block. The qid is left empty when
    the ID isn't numeric; detect_in_cells numbers those in order."""
    qid = label = ""
    m = _ID_VALUE.match(meta.get("id", ""))
    if m and m.group(2):
        qid = label = f"Q{int(m.group(1))}-{int(m.group(2))}"
    elif m:
        qid, label = f"Q{int(m.group(1))}", f"Question {int(m.group(1))}"
    pts = _NUMBER.search(meta.get("points", ""))
    return Hit(
        qid=qid,
        label=label,
        statement=meta.get("label") or meta.get("id", ""),
        points=float(pts.group().replace(",", ".")) if pts else None,
        cell_indices=[idx],
    )


def whole_file_hit(cells: list[Cell]) -> Hit:
    """A .py file with no question markers at all is one question: its
    opening comment/docstring (if any) is the statement."""
    header = _code_header(cells[0].source) if cells else ""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:points?|pts?|pontos?|valores?)\b", header, re.IGNORECASE)
    return Hit(
        qid="Q1",
        label="Question 1",
        statement=header or "Whole file (no question markers found)",
        points=float(m.group(1).replace(",", ".")) if m else None,
        cell_indices=[0],
    )


def detect_in_cells(cells: list[Cell], file_type: str = "ipynb") -> list[Hit]:
    """Notebooks: scan markdown cells. Python files: also scan the header of
    each code cell — but only cells that *open* with a question header, and
    only that header's first marker, so "# Q2: reuse the function from Q1"
    belongs to Q2 alone. Key/value blocks ("ID: 1 / Label: … / Grade: 5
    points") are understood in both."""
    hits: list[Hit] = []
    for idx, cell in enumerate(cells):
        if cell.cell_type == "markdown":
            found = _scan_text_block(cell.source, idx)
            if not found:
                meta = parse_metadata(cell.source)
                found = [_metadata_hit(meta, idx)] if meta else []
            hits.extend(found)
            continue
        if file_type != "py":
            continue
        meta = parse_metadata(_code_header(cell.source))
        if meta:
            hits.append(_metadata_hit(meta, idx))
            continue
        first = next((l for l in cell.source.splitlines() if l.strip() and not _DECORATION.match(l)), "")
        if not QUESTION_HEADER.match(first):
            continue
        header = _code_header(cell.source)
        found = _scan_text_block(header, idx)
        if found:
            h = found[0]
            hits.append(Hit(
                qid=h.qid,
                label=h.label,
                statement=header,
                points=_extract_points(header),
                cell_indices=[idx],
            ))

    # Non-numeric IDs ("ID: A", "ID: soma") get the next free numbers, in order.
    used = {int(h.qid[1:].split("-")[0]) for h in hits if h.qid}
    n = 0
    for h in hits:
        if not h.qid:
            n += 1
            while n in used:
                n += 1
            used.add(n)
            h.qid, h.label = f"Q{n}", f"Question {n}"
    return _merge_hits(hits)


def detect_in_python(content) -> list[Hit]:
    return detect_in_cells(parse_python(content), "py")


def detect(filename: str, content) -> tuple[str, list[Hit]]:
    lower = filename.lower()
    if lower.endswith(".ipynb"):
        return "ipynb", detect_in_notebook(content)
    if lower.endswith(".py"):
        return "py", detect_in_python(content)
    raise ValueError(f"Unsupported file type: {filename}")
