"""Extract a zip of student submissions."""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from notebook_parser import Cell, _to_str, parse_notebook, parse_python

MOODLE_FOLDER_PATTERN = re.compile(r"^(?P<name>.+?)_(?P<number>\d+)_assignsubmission_file")


@dataclass
class StudentRecord:
    id: str
    name: str
    filename: str
    file_type: str
    cells: list[Cell] = field(default_factory=list)
    # Untouched file text (.py) or the code cells joined (.ipynb). The
    # teacher's working copy starts from it; it is never modified.
    source: str = ""
    error: str | None = None
    question_windows: dict = field(default_factory=dict)
    invisible_findings: list = field(default_factory=list)


def _student_from_path(path: str):
    parts = PurePosixPath(path).parts
    for part in parts:
        match = MOODLE_FOLDER_PATTERN.match(part)
        if match:
            return match.group("name"), match.group("number")
    parent = parts[-2] if len(parts) >= 2 else "unknown"
    stem = PurePosixPath(path).stem
    return parent, stem


def join_code_cells(cells: list[Cell]) -> str:
    """A notebook's code cells as one runnable script ("Run all")."""
    return "\n\n".join(f"# %% [cell {i + 1}]\n{c.source}" for i, c in enumerate(cells) if c.cell_type == "code")


def _to_bytes(content) -> bytes:
    if hasattr(content, "to_py") and not isinstance(content, (bytes, bytearray, memoryview, str)):
        content = content.to_py()
    if isinstance(content, str):
        return content.encode("utf-8")
    return bytes(content)


def load_zip(content) -> tuple[list[StudentRecord], list[str]]:
    records: list[StudentRecord] = []
    warnings: list[str] = []
    seen_ids: set = set()

    data = _to_bytes(content)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name_lower = info.filename.lower()
            if not (name_lower.endswith(".ipynb") or name_lower.endswith(".py")):
                continue
            if "__macosx" in name_lower or name_lower.endswith(".checkpoint.ipynb"):
                continue

            try:
                file_data = zf.read(info)
            except Exception as e:
                warnings.append(f"Could not read {info.filename}: {e}")
                continue

            student_name, student_id = _student_from_path(info.filename)
            if student_id in seen_ids:
                continue
            seen_ids.add(student_id)

            file_type = "ipynb" if name_lower.endswith(".ipynb") else "py"
            try:
                cells = (
                    parse_notebook(file_data) if file_type == "ipynb" else parse_python(file_data)
                )
                source = _to_str(file_data) if file_type == "py" else join_code_cells(cells)
                error = None
            except Exception as e:
                cells = []
                source = ""
                error = f"Could not parse {info.filename}: {e}"
                warnings.append(error)

            records.append(
                StudentRecord(
                    id=student_id,
                    name=student_name,
                    filename=PurePosixPath(info.filename).name,
                    file_type=file_type,
                    cells=cells,
                    source=source,
                    error=error,
                )
            )

    return records, warnings
