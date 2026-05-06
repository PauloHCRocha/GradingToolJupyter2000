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
    question_windows: dict[str, list[int]] = {}


class CellOut(BaseModel):
    cell_id: str
    cell_type: str
    source: str
    output: str


class SolutionDetail(BaseModel):
    filename: str
    file_type: Literal["ipynb", "py"]
    cells: list[CellOut]
    question_windows: dict[str, list[int]] = {}


class StudentInfo(BaseModel):
    id: str
    name: str
    filename: str
    file_type: Literal["ipynb", "py"]
    has_error: bool
    error: str | None = None
    total_grade: float = 0.0
    invisible_count: int = 0


class StudentDetail(BaseModel):
    info: StudentInfo
    cells: list[CellOut]
    question_windows: dict[str, list[int]] = {}
    invisible_findings: list[dict] = []


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


class SuggestRequest(BaseModel):
    question_id: str


class SuggestResponse(BaseModel):
    points: float | None
    score: float
    confidence: Literal["high", "medium", "low", "none"]
    comment: str
    max_points: float


class RunCodeRequest(BaseModel):
    code: str
    stdin: str = ""
    timeout: float = 10.0


class RunCodeResponse(BaseModel):
    success: bool
    output: str
    error: str
    duration_ms: int


class PlagiarismAnalyzeRequest(BaseModel):
    threshold: float = 0.85


class SuspiciousPair(BaseModel):
    student1_id: str
    student1_name: str
    student2_id: str
    student2_name: str
    similarity: float


class PlagiarismAnalyzeResponse(BaseModel):
    threshold: float
    matrix: list[list[float]]
    student_ids: list[str]
    student_names: list[str]
    suspicious_pairs: list[SuspiciousPair]
    stats: dict


class PlagiarismCompareRequest(BaseModel):
    student1_id: str
    student2_id: str


class QuestionSimilarity(BaseModel):
    question_id: str
    similarity: float
    tfidf: float
    ast: float


class PlagiarismCompareResponse(BaseModel):
    student1_id: str
    student1_name: str
    student2_id: str
    student2_name: str
    overall_similarity: float
    questions: list[QuestionSimilarity]
    code1: str
    code2: str
