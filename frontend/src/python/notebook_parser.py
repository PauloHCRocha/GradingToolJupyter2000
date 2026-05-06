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


def _join(value):
    return value if isinstance(value, str) else "".join(value)


def _to_str(content):
    # Pyodide may hand us a JsProxy wrapping a TypedArray; unwrap it first.
    if hasattr(content, "to_py") and not isinstance(content, (bytes, bytearray, memoryview, str)):
        content = content.to_py()
    if isinstance(content, str):
        return content
    return bytes(content).decode("utf-8", errors="replace")


def parse_notebook(content) -> list[Cell]:
    notebook = json.loads(_to_str(content))
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


def parse_python(content) -> list[Cell]:
    source = _to_str(content)
    return [Cell(cell_id="py-0", cell_type="code", source=source, output="")]
