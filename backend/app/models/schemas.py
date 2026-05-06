from pydantic import BaseModel
from typing import Literal


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
