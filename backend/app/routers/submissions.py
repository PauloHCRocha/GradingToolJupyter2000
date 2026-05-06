from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core import state
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
    )


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

    # Replace existing submissions on every upload.
    state.reset()
    for rec in records:
        state.add_student(rec)

    return SubmissionsUploadResult(
        students=[_student_info(r) for r in state.list_students()],
        warnings=warnings,
    )


@router.get("", response_model=list[StudentInfo])
def list_submissions() -> list[StudentInfo]:
    return [_student_info(r) for r in state.list_students()]


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
    )
