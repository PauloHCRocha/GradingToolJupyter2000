from fastapi import APIRouter, HTTPException

from app.core import state
from app.core.grade_suggester import suggest_grade
from app.core.plagiarism import extract_code_for_indices
from app.models.schemas import SuggestResponse

router = APIRouter(prefix="/api/suggest", tags=["suggest"])


def _question_max(question_id: str) -> tuple[float, dict]:
    questions = state.get_questions()
    for q in questions:
        if q["id"] == question_id:
            return float(q.get("max_points") or 0.0), q
    raise HTTPException(status_code=404, detail=f"Question {question_id} not found.")


@router.post("/{student_id}/{question_id}", response_model=SuggestResponse)
def suggest(student_id: str, question_id: str) -> SuggestResponse:
    rec = state.get_student(student_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    max_points, _ = _question_max(question_id)
    sol_cells, sol_windows, _, _ = state.get_solution()
    sol_indices = sol_windows.get(question_id, [])
    student_indices = rec.question_windows.get(question_id, [])

    student_code = extract_code_for_indices(rec.cells, student_indices) if student_indices else ""
    reference = extract_code_for_indices(sol_cells, sol_indices) if sol_indices else ""

    grade, score, confidence, comment = suggest_grade(student_code, reference, max_points)
    return SuggestResponse(
        points=grade,
        score=float(score),
        confidence=confidence,
        comment=comment,
        max_points=max_points,
    )
