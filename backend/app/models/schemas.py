from typing import Literal

from pydantic import BaseModel


class DetectedQuestion(BaseModel):
    id: str
    label: str
    max_points: float
    statement: str
    cell_indices: list[int] = []


class SolutionAnalysis(BaseModel):
    filename: str
    file_type: Literal["ipynb", "py"]
    questions: list[DetectedQuestion]
    total_max_points: float


class StudentInfo(BaseModel):
    id: str
    name: str
    filename: str
    file_type: Literal["ipynb", "py"]
    has_error: bool
    error: str | None = None
    total_grade: float = 0.0


class CellOut(BaseModel):
    cell_id: str
    cell_type: str
    source: str
    output: str


class StudentDetail(BaseModel):
    info: StudentInfo
    cells: list[CellOut]


class SubmissionsUploadResult(BaseModel):
    students: list[StudentInfo]
    warnings: list[str] = []


class GradeIn(BaseModel):
    points: float
    comment: str = ""


class GradeOut(GradeIn):
    question_id: str


class StudentGrades(BaseModel):
    student_id: str
    entries: list[GradeOut]
    total: float
