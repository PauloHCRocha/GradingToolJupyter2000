"""Parse Jupyter notebooks (.ipynb) and Python sources (.py) into a uniform cell list."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class Cell:
    cell_id: str
    cell_type: str  # "markdown" | "code"
    source: str
    output: str


def _join(value: str | list[str]) -> str:
    return value if isinstance(value, str) else "".join(value)


def parse_notebook(content: bytes) -> list[Cell]:
    notebook = json.loads(content.decode("utf-8"))
    cells: list[Cell] = []
    for idx, cell in enumerate(notebook.get("cells", [])):
        cell_id = cell.get("id") or f"cell-{idx}"
        cell_type = cell.get("cell_type", "code")
        source = _join(cell.get("source", []))

        output_parts: list[str] = []
        for out in cell.get("outputs", []) or []:
            if "text" in out:
                output_parts.append(_join(out["text"]))
            elif "data" in out and "text/plain" in out["data"]:
                output_parts.append(_join(out["data"]["text/plain"]))
        output = "\n".join(output_parts)

        cells.append(Cell(cell_id=cell_id, cell_type=cell_type, source=source, output=output))
    return cells


def parse_python(content: bytes) -> list[Cell]:
    """Wrap a .py file as a single 'code' cell so the UI can render it uniformly."""
    source = content.decode("utf-8", errors="replace")
    return [Cell(cell_id="py-0", cell_type="code", source=source, output="")]
