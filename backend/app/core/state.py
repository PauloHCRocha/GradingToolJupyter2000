"""In-memory session state. Resets on server restart (acceptable for current MVP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from app.core.notebook_parser import Cell


@dataclass
class StudentRecord:
    id: str
    name: str
    filename: str
    file_type: str  # "ipynb" | "py"
    cells: list[Cell] = field(default_factory=list)
    error: str | None = None


@dataclass
class GradeEntry:
    points: float = 0.0
    comment: str = ""


@dataclass
class _SessionState:
    students: dict[str, StudentRecord] = field(default_factory=dict)
    # student_id -> question_id -> entry
    grades: dict[str, dict[str, GradeEntry]] = field(default_factory=dict)
    questions: list[dict] = field(default_factory=list)


_state = _SessionState()
_lock = Lock()


def reset() -> None:
    with _lock:
        _state.students.clear()
        _state.grades.clear()
        _state.questions.clear()


def set_questions(questions: list[dict]) -> None:
    with _lock:
        _state.questions = list(questions)


def get_questions() -> list[dict]:
    with _lock:
        return list(_state.questions)


def add_student(student: StudentRecord) -> None:
    with _lock:
        _state.students[student.id] = student
        _state.grades.setdefault(student.id, {})


def list_students() -> list[StudentRecord]:
    with _lock:
        return sorted(_state.students.values(), key=lambda s: s.name.lower())


def get_student(student_id: str) -> StudentRecord | None:
    with _lock:
        return _state.students.get(student_id)


def set_grade(student_id: str, question_id: str, entry: GradeEntry) -> None:
    with _lock:
        if student_id not in _state.students:
            raise KeyError(student_id)
        _state.grades.setdefault(student_id, {})[question_id] = entry


def get_grades(student_id: str) -> dict[str, GradeEntry]:
    with _lock:
        return dict(_state.grades.get(student_id, {}))


def all_grades() -> dict[str, dict[str, GradeEntry]]:
    with _lock:
        return {sid: dict(g) for sid, g in _state.grades.items()}
