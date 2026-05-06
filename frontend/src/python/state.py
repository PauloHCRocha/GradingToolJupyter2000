"""In-browser session state. Single-process, single-tab — no locking needed."""

from __future__ import annotations

from dataclasses import dataclass, field

from notebook_parser import Cell
from submission_loader import StudentRecord


@dataclass
class GradeEntry:
    points: float = 0.0
    comment: str = ""


@dataclass
class _SessionState:
    students: dict = field(default_factory=dict)
    student_order: list = field(default_factory=list)
    grades: dict = field(default_factory=dict)  # student_id -> qid -> GradeEntry
    questions: list = field(default_factory=list)
    solution_filename: str | None = None
    solution_file_type: str | None = None
    solution_cells: list = field(default_factory=list)
    solution_question_windows: dict = field(default_factory=dict)
    plagiarism_matrix: list | None = None
    plagiarism_student_ids: list = field(default_factory=list)


_state = _SessionState()


def reset_submissions():
    _state.students.clear()
    _state.student_order.clear()
    _state.grades.clear()
    _state.plagiarism_matrix = None
    _state.plagiarism_student_ids = []


def reset_all():
    reset_submissions()
    _state.questions.clear()
    _state.solution_filename = None
    _state.solution_file_type = None
    _state.solution_cells.clear()
    _state.solution_question_windows.clear()


def set_solution(filename, file_type, cells, questions, windows):
    _state.solution_filename = filename
    _state.solution_file_type = file_type
    _state.solution_cells = list(cells)
    _state.questions = list(questions)
    _state.solution_question_windows = dict(windows)


def get_solution():
    return (
        list(_state.solution_cells),
        dict(_state.solution_question_windows),
        _state.solution_filename,
        _state.solution_file_type,
    )


def set_questions(questions):
    _state.questions = list(questions)


def get_questions():
    return list(_state.questions)


def add_student(student: StudentRecord):
    if student.id not in _state.students:
        _state.student_order.append(student.id)
    _state.students[student.id] = student
    _state.grades.setdefault(student.id, {})


def list_students_ordered():
    return [_state.students[sid] for sid in _state.student_order if sid in _state.students]


def list_students_sorted_by_name():
    return sorted(list_students_ordered(), key=lambda s: s.name.lower())


def list_students_sorted_by_number():
    def key(s):
        try:
            return (int(s.id), s.id)
        except ValueError:
            return (10**9, s.id)
    return sorted(list_students_ordered(), key=key)


def get_student(student_id):
    return _state.students.get(student_id)


def set_grade(student_id, question_id, entry: GradeEntry):
    if student_id not in _state.students:
        raise KeyError(student_id)
    _state.grades.setdefault(student_id, {})[question_id] = entry


def get_grades(student_id):
    return dict(_state.grades.get(student_id, {}))


def set_plagiarism(matrix, student_ids):
    _state.plagiarism_matrix = matrix
    _state.plagiarism_student_ids = list(student_ids)


def get_plagiarism():
    return _state.plagiarism_matrix, list(_state.plagiarism_student_ids)
