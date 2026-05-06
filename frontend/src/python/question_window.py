"""Map detected questions to ranges of notebook cells."""

from __future__ import annotations

from notebook_parser import Cell


def compute_windows(cells: list[Cell], questions: list[dict]) -> dict[str, list[int]]:
    if not questions or not cells:
        return {}

    ordered: list[tuple[int, str]] = []
    for q in questions:
        idxs = q.get("cell_indices") or []
        if not idxs:
            continue
        ordered.append((min(idxs), q["id"]))
    ordered.sort()

    starts = [(start, qid) for start, qid in ordered]
    windows: dict[str, list[int]] = {}
    for i, (start, qid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(cells)
        windows[qid] = list(range(start, end))
    return windows


def detect_in_cells(cells: list[Cell]) -> list[dict]:
    from question_detector import _scan_text_block, _merge_hits

    hits = []
    for idx, cell in enumerate(cells):
        if cell.cell_type != "markdown":
            continue
        hits.extend(_scan_text_block(cell.source, idx))
    merged = _merge_hits(hits)
    return [
        {
            "id": h.qid,
            "label": h.label,
            "max_points": h.points or 0.0,
            "statement": h.statement,
            "cell_indices": h.cell_indices,
        }
        for h in merged
    ]
