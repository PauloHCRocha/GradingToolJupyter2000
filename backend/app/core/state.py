"""In-memory session state. Resets on server restart (acceptable for current MVP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

import numpy as np

from app.core.notebook_parser import Cell


@dataclass
class StudentRecord:
    id: str
    name: str
    filename: str
    file_type: str  # "ipynb" | "py"
    cells: list[Cell] = field(default_factory=list)
    error: str | None = None
    question_windows: dict[str, list[int]] = field(default_factory=dict)
    invisible_findings: list[dict] = field(default_factory=list)


@dataclass
class GradeEntry:
    points: float = 0.0
    comment: str = ""


@dataclass
class _SessionState:
    students: dict[str, StudentRecord] = field(default_factory=dict)
    student_order: list[str] = field(default_factory=list)
    # student_id -> question_id -> entry
    grades: dict[str, dict[str, GradeEntry]] = field(default_factory=dict)
    questions: list[dict] = field(default_factory=list)
    solution_filename: str | None = None
    solution_file_type: str | None = None
    solution_cells: list[Cell] = field(default_factory=list)
    solution_question_windows: dict[str, list[int]] = field(default_factory=dict)
    plagiarism_matrix: np.ndarray | None = None


_state = _SessionState()
_lock = Lock()


def reset_submissions() -> None:
    with _lock:
        _state.students.clear()
        _state.student_order.clear()
        _state.grades.clear()
        _state.plagiarism_matrix = None


def reset_all() -> None:
    with _lock:
        _state.students.clear()
        _state.student_order.clear()
        _state.grades.clear()
        _state.questions.clear()
        _state.solution_filename = None
        _state.solution_file_type = None
        _state.solution_cells.clear()
        _state.solution_question_windows.clear()
        _state.plagiarism_matrix = None


def set_solution(
    filename: str,
    file_type: str,
    cells: list[Cell],
    questions: list[dict],
    windows: dict[str, list[int]],
) -> None:
    with _lock:
        _state.solution_filename = filename
        _state.solution_file_type = file_type
        _state.solution_cells = cells
        _state.questions = list(questions)
        _state.solution_question_windows = dict(windows)


def get_solution() -> tuple[list[Cell], dict[str, list[int]], str | None, str | None]:
    with _lock:
        return (
            list(_state.solution_cells),
            dict(_state.solution_question_windows),
            _state.solution_filename,
            _state.solution_file_type,
        )


def set_questions(questions: list[dict]) -> None:
    with _lock:
        _state.questions = list(questions)


def get_questions() -> list[dict]:
    with _lock:
        return list(_state.questions)


def add_student(student: StudentRecord) -> None:
    with _lock:
        if student.id not in _state.students:
            _state.student_order.append(student.id)
        _state.students[student.id] = student
        _state.grades.setdefault(student.id, {})


def list_students_ordered() -> list[StudentRecord]:
    with _lock:
        return [_state.students[sid] for sid in _state.student_order if sid in _state.students]


def list_students_sorted_by_name() -> list[StudentRecord]:
    return sorted(list_students_ordered(), key=lambda s: s.name.lower())


def list_students_sorted_by_number() -> list[StudentRecord]:
    def key(s: StudentRecord) -> tuple[int, str]:
        try:
            return (int(s.id), s.id)
        except ValueError:
            return (10**9, s.id)
    return sorted(list_students_ordered(), key=key)


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


def set_plagiarism_matrix(matrix: np.ndarray | None) -> None:
    with _lock:
        _state.plagiarism_matrix = matrix


def get_plagiarism_matrix() -> np.ndarray | None:
    with _lock:
        return _state.plagiarism_matrix
