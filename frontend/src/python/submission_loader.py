"""Extract a zip of student submissions."""

from __future__ import annotations

import io
import re
import zipfile
from collections import Counter
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


def _student_from_path(path: str, per_folder: Counter):
    p = PurePosixPath(path)
    for part in p.parts:
        match = MOODLE_FOLDER_PATTERN.match(part)
        if match:
            return match.group("name"), match.group("number")
    # One submission per folder ("Ana Silva/ficha3.py"): the folder is the
    # student. Several in one folder ("turma/1234.py", "turma/4566.py") or
    # none at all ("1234.py"): each file is.
    folder = str(p.parent)
    if folder != "." and per_folder[folder] == 1:
        return p.parent.name, p.parent.name
    return p.stem, p.stem


def _is_submission(path: str) -> bool:
    lower = path.lower()
    if not (lower.endswith(".py") or lower.endswith(".ipynb")):
        return False
    # macOS resource forks ("__MACOSX/…", "._ficha.py") and Jupyter autosaves.
    return not (
        "__macosx/" in lower
        or PurePosixPath(lower).name.startswith("._")
        or ".ipynb_checkpoints/" in lower
        or lower.endswith("-checkpoint.ipynb")
    )


def join_code_cells(cells: list[Cell]) -> str:
    """A notebook's code cells as one runnable script ("Run all")."""
    return "\n\n".join(f"# %% [cell {i + 1}]\n{c.source}" for i, c in enumerate(cells) if c.cell_type == "code")


def _to_bytes(content) -> bytes:
    if hasattr(content, "to_py") and not isinstance(content, (bytes, bytearray, memoryview, str)):
        content = content.to_py()
    if isinstance(content, str):
        return content.encode("utf-8")
    return bytes(content)


def _load_entries(entries) -> tuple[list[StudentRecord], list[str]]:
    """entries: (path, read) pairs, read() returning the file's bytes."""
    records: list[StudentRecord] = []
    warnings: list[str] = []
    first_file: dict[str, str] = {}
    per_folder = Counter(str(PurePosixPath(path).parent) for path, _ in entries)

    for path, read in entries:
        try:
            file_data = read()
        except Exception as e:
            warnings.append(f"Could not read {path}: {e}")
            continue

        student_name, student_id = _student_from_path(path, per_folder)
        if student_id in first_file:
            warnings.append(f"Skipped {path}: {student_name} already has a submission ({first_file[student_id]}).")
            continue
        first_file[student_id] = path

        file_type = "ipynb" if path.lower().endswith(".ipynb") else "py"
        try:
            cells = parse_notebook(file_data) if file_type == "ipynb" else parse_python(file_data)
            source = _to_str(file_data) if file_type == "py" else join_code_cells(cells)
            error = None
        except Exception as e:
            cells = []
            source = ""
            error = f"Could not parse {path}: {e}"
            warnings.append(error)

        records.append(
            StudentRecord(
                id=student_id,
                name=student_name,
                filename=PurePosixPath(path).name,
                file_type=file_type,
                cells=cells,
                source=source,
                error=error,
            )
        )

    return records, warnings


def load_zip(content) -> tuple[list[StudentRecord], list[str]]:
    with zipfile.ZipFile(io.BytesIO(_to_bytes(content))) as zf:
        entries = [
            (info.filename, (lambda info=info: zf.read(info)))
            for info in zf.infolist()
            if not info.is_dir() and _is_submission(info.filename)
        ]
        return _load_entries(entries)


def load_files(files) -> tuple[list[StudentRecord], list[str]]:
    """Loose student files dropped without a zip: [{"name", "content"}].
    Each file is one student, named after the file."""
    if hasattr(files, "to_py"):
        files = files.to_py()
    entries = [
        (f["name"], (lambda f=f: _to_bytes(f["content"])))
        for f in files
        if _is_submission(f["name"])
    ]
    return _load_entries(entries)
