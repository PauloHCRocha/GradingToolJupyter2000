import csv
import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core import state
from app.models.schemas import GradeIn, GradeOut, StudentGrades

router = APIRouter(prefix="/api/grades", tags=["grades"])


def _student_grades(student_id: str) -> StudentGrades:
    grades = state.get_grades(student_id)
    entries = [
        GradeOut(question_id=qid, points=g.points, comment=g.comment)
        for qid, g in grades.items()
    ]
    return StudentGrades(
        student_id=student_id,
        entries=entries,
        total=sum(e.points for e in entries),
    )


@router.get("/export.csv")
def export_csv() -> StreamingResponse:
    questions = state.get_questions()
    qids = [q["id"] for q in questions]

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = ["Student Name", "Student Number"]
    for qid in qids:
        header.extend([qid, f"{qid}_comment"])
    header.extend(["Total", "Max Points"])
    writer.writerow(header)

    max_points = sum(q.get("max_points", 0) for q in questions)

    for rec in state.list_students():
        grades = state.get_grades(rec.id)
        row: list[object] = [rec.name, rec.id]
        total = 0.0
        for qid in qids:
            entry = grades.get(qid)
            row.append(entry.points if entry else "")
            row.append(entry.comment if entry else "")
            if entry:
                total += entry.points
        row.append(total)
        row.append(max_points)
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="grades.csv"'},
    )


@router.get("/{student_id}", response_model=StudentGrades)
def get_student_grades(student_id: str) -> StudentGrades:
    if state.get_student(student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return _student_grades(student_id)


@router.put("/{student_id}/{question_id}", response_model=StudentGrades)
def set_student_grade(
    student_id: str, question_id: str, grade: GradeIn
) -> StudentGrades:
    if state.get_student(student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    state.set_grade(
        student_id, question_id, state.GradeEntry(points=grade.points, comment=grade.comment)
    )
    return _student_grades(student_id)
