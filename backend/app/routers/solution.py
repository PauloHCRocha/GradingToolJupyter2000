from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core import state
from app.core.notebook_parser import parse_notebook, parse_python
from app.core.question_detector import detect
from app.core.question_window import compute_windows
from app.models.schemas import (
    CellOut,
    DetectedQuestion,
    SolutionAnalysis,
    SolutionDetail,
)

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
        cells = parse_notebook(content) if file_type == "ipynb" else parse_python(content)
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
    questions_dump = [q.model_dump() for q in questions]
    windows = compute_windows(cells, questions_dump)

    state.set_solution(
        filename=file.filename,
        file_type=file_type,
        cells=cells,
        questions=questions_dump,
        windows=windows,
    )

    return SolutionAnalysis(
        filename=file.filename,
        file_type=file_type,  # type: ignore[arg-type]
        questions=questions,
        total_max_points=sum(q.max_points for q in questions),
        question_windows=windows,
    )


@router.put("/questions", response_model=list[DetectedQuestion])
def update_questions(questions: list[DetectedQuestion]) -> list[DetectedQuestion]:
    """Persist user-edited question metadata (e.g. adjusted max_points)."""
    state.set_questions([q.model_dump() for q in questions])
    return questions


@router.get("/cells", response_model=SolutionDetail)
def get_solution_cells() -> SolutionDetail:
    cells, windows, filename, file_type = state.get_solution()
    if not filename:
        raise HTTPException(status_code=404, detail="No solution uploaded yet.")
    return SolutionDetail(
        filename=filename,
        file_type=file_type or "ipynb",  # type: ignore[arg-type]
        cells=[
            CellOut(cell_id=c.cell_id, cell_type=c.cell_type, source=c.source, output=c.output)
            for c in cells
        ],
        question_windows=windows,
    )
