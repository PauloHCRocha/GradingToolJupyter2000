"""Extract a zip of student submissions and turn each into a StudentRecord."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePosixPath

from app.core.notebook_parser import parse_notebook, parse_python
from app.core.state import StudentRecord

# Moodle-style: "<Name>_<Number>_assignsubmission_file/<file>.ipynb"
MOODLE_FOLDER_PATTERN = re.compile(
    r"^(?P<name>.+?)_(?P<number>\d+)_assignsubmission_file"
)


def _student_from_path(path: str) -> tuple[str, str]:
    """Return (name, student_number) inferred from the path of a submission file."""
    parts = PurePosixPath(path).parts
    for part in parts:
        match = MOODLE_FOLDER_PATTERN.match(part)
        if match:
            return match.group("name"), match.group("number")
    # Fallback: use the parent folder (or filename stem) and a hash-like id.
    parent = parts[-2] if len(parts) >= 2 else "unknown"
    stem = PurePosixPath(path).stem
    return parent, stem


def load_zip(content: bytes) -> tuple[list[StudentRecord], list[str]]:
    """Return (records, warnings)."""
    records: list[StudentRecord] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name_lower = info.filename.lower()
            if not (name_lower.endswith(".ipynb") or name_lower.endswith(".py")):
                continue
            if "__macosx" in name_lower or name_lower.endswith(".checkpoint.ipynb"):
                continue

            try:
                data = zf.read(info)
            except Exception as e:
                warnings.append(f"Could not read {info.filename}: {e}")
                continue

            student_name, student_id = _student_from_path(info.filename)
            if student_id in seen_ids:
                # Same student appears with multiple files; keep the first.
                continue
            seen_ids.add(student_id)

            file_type = "ipynb" if name_lower.endswith(".ipynb") else "py"
            try:
                cells = (
                    parse_notebook(data) if file_type == "ipynb" else parse_python(data)
                )
                error = None
            except Exception as e:
                cells = []
                error = f"Could not parse {info.filename}: {e}"
                warnings.append(error)

            records.append(
                StudentRecord(
                    id=student_id,
                    name=student_name,
                    filename=PurePosixPath(info.filename).name,
                    file_type=file_type,
                    cells=cells,
                    error=error,
                )
            )

    return records, warnings
