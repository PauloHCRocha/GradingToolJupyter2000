from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.question_detector import detect
from app.models.schemas import DetectedQuestion, SolutionAnalysis

router = APIRouter(prefix="/api/solution", tags=["solution"])

ALLOWED_EXTENSIONS = (".ipynb", ".py")


@router.post("/analyze", response_model=SolutionAnalysis)
async def analyze_solution(file: UploadFile = File(...)) -> SolutionAnalysis:
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Only .ipynb and .py files are supported.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty.")

    try:
        file_type, hits = detect(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse file: {e}",
        ) from e

    questions = [
        DetectedQuestion(
            id=h.qid,
            label=h.label,
            max_points=h.points if h.points is not None else 0.0,
            statement=h.statement,
            cell_indices=h.cell_indices,
        )
        for h in hits
    ]

    return SolutionAnalysis(
        filename=file.filename,
        file_type=file_type,  # type: ignore[arg-type]
        questions=questions,
        total_max_points=sum(q.max_points for q in questions),
    )
