from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.core import state
from app.core.ai_detection import detect_invisible
from app.core.question_window import compute_windows, detect_in_cells
from app.core.submission_loader import load_zip
from app.models.schemas import (
    CellOut,
    StudentDetail,
    StudentInfo,
    SubmissionsUploadResult,
)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def _student_info(rec: state.StudentRecord) -> StudentInfo:
    grades = state.get_grades(rec.id)
    total = sum(g.points for g in grades.values())
    return StudentInfo(
        id=rec.id,
        name=rec.name,
        filename=rec.filename,
        file_type=rec.file_type,  # type: ignore[arg-type]
        has_error=rec.error is not None,
        error=rec.error,
        total_grade=total,
        invisible_count=len(rec.invisible_findings),
    )


def _sorted_records(sort: str) -> list[state.StudentRecord]:
    if sort == "number":
        return state.list_students_sorted_by_number()
    return state.list_students_sorted_by_name()


@router.post("/upload", response_model=SubmissionsUploadResult)
async def upload_submissions(file: UploadFile = File(...)) -> SubmissionsUploadResult:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty.")

    try:
        records, warnings = load_zip(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read zip: {e}") from e

    if not records:
        raise HTTPException(
            status_code=400,
            detail="No .ipynb or .py submissions found in the zip.",
        )

    state.reset_submissions()

    # Annotate each record with question windows and invisible-character findings.
    questions = state.get_questions()
    for rec in records:
        if rec.cells:
            # Detect questions in this student's notebook for accurate windowing.
            student_questions = detect_in_cells(rec.cells)
            # Use the questions defined by the solution if available, but their
            # cell_indices come from the solution — the windows must use the student's.
            if questions:
                # Map by qid: use student's own marker indices when available.
                merged: list[dict] = []
                student_by_id = {q["id"]: q for q in student_questions}
                for q in questions:
                    sq = student_by_id.get(q["id"])
                    merged.append(
                        {
                            **q,
                            "cell_indices": sq["cell_indices"] if sq else q.get("cell_indices", []),
                        }
                    )
                rec.question_windows = compute_windows(rec.cells, merged)
            else:
                rec.question_windows = compute_windows(rec.cells, student_questions)

            rec.invisible_findings = detect_invisible(rec.cells)
        state.add_student(rec)

    return SubmissionsUploadResult(
        students=[_student_info(r) for r in _sorted_records("name")],
        warnings=warnings,
    )


@router.get("", response_model=list[StudentInfo])
def list_submissions(sort: str = Query("name", pattern="^(name|number)$")) -> list[StudentInfo]:
    return [_student_info(r) for r in _sorted_records(sort)]


@router.get("/{student_id}", response_model=StudentDetail)
def get_submission(student_id: str) -> StudentDetail:
    rec = state.get_student(student_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return StudentDetail(
        info=_student_info(rec),
        cells=[
            CellOut(
                cell_id=c.cell_id,
                cell_type=c.cell_type,
                source=c.source,
                output=c.output,
            )
            for c in rec.cells
        ],
        question_windows=rec.question_windows,
        invisible_findings=rec.invisible_findings,
    )
