from fastapi import APIRouter, HTTPException

from app.core import state
from app.core.plagiarism import (
    ast_similarity,
    compute_matrix,
    extract_code,
    extract_code_for_indices,
    find_suspicious_pairs,
    tfidf_similarity,
)
from app.models.schemas import (
    PlagiarismAnalyzeRequest,
    PlagiarismAnalyzeResponse,
    PlagiarismCompareRequest,
    PlagiarismCompareResponse,
    QuestionSimilarity,
    SuspiciousPair,
)

router = APIRouter(prefix="/api/plagiarism", tags=["plagiarism"])


@router.post("/analyze", response_model=PlagiarismAnalyzeResponse)
def analyze(req: PlagiarismAnalyzeRequest) -> PlagiarismAnalyzeResponse:
    students = state.list_students_sorted_by_name()
    if len(students) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 submissions.")

    codes = [extract_code(s.cells) for s in students]
    matrix = compute_matrix(codes)
    state.set_plagiarism_matrix(matrix)

    pairs_raw = find_suspicious_pairs(matrix, req.threshold)
    pairs = [
        SuspiciousPair(
            student1_id=students[i].id,
            student1_name=students[i].name,
            student2_id=students[j].id,
            student2_name=students[j].name,
            similarity=sim,
        )
        for i, j, sim in pairs_raw
    ]

    n = len(students)
    upper = [matrix[i][j] for i in range(n) for j in range(i + 1, n)]
    high = sum(1 for s in upper if s >= 0.95)
    avg = float(sum(upper) / len(upper)) if upper else 0.0

    return PlagiarismAnalyzeResponse(
        threshold=req.threshold,
        matrix=matrix.tolist(),
        student_ids=[s.id for s in students],
        student_names=[s.name for s in students],
        suspicious_pairs=pairs,
        stats={
            "total_comparisons": len(upper),
            "suspicious_count": len(pairs),
            "high_similarity_count": high,
            "avg_similarity": avg,
        },
    )


@router.post("/compare", response_model=PlagiarismCompareResponse)
def compare(req: PlagiarismCompareRequest) -> PlagiarismCompareResponse:
    s1 = state.get_student(req.student1_id)
    s2 = state.get_student(req.student2_id)
    if s1 is None or s2 is None:
        raise HTTPException(status_code=404, detail="One of the students was not found.")

    code1 = extract_code(s1.cells)
    code2 = extract_code(s2.cells)

    questions = state.get_questions()
    q_results: list[QuestionSimilarity] = []
    for q in questions:
        qid = q["id"]
        idx1 = s1.question_windows.get(qid, [])
        idx2 = s2.question_windows.get(qid, [])
        c1 = extract_code_for_indices(s1.cells, idx1) if idx1 else ""
        c2 = extract_code_for_indices(s2.cells, idx2) if idx2 else ""
        if c1.strip() and c2.strip():
            tf = tfidf_similarity(c1, c2)
            asts = ast_similarity(c1, c2)
            sim = 0.6 * tf + 0.4 * asts
        else:
            tf = asts = sim = 0.0
        q_results.append(QuestionSimilarity(question_id=qid, similarity=sim, tfidf=tf, ast=asts))

    matrix = state.get_plagiarism_matrix()
    overall = 0.0
    if matrix is not None:
        ids = [s.id for s in state.list_students_sorted_by_name()]
        if req.student1_id in ids and req.student2_id in ids:
            i = ids.index(req.student1_id)
            j = ids.index(req.student2_id)
            overall = float(matrix[i][j])

    if overall == 0.0:
        from app.core.plagiarism import hybrid_similarity
        overall = hybrid_similarity(code1, code2)

    return PlagiarismCompareResponse(
        student1_id=s1.id,
        student1_name=s1.name,
        student2_id=s2.id,
        student2_name=s2.name,
        overall_similarity=overall,
        questions=q_results,
        code1=code1,
        code2=code2,
    )
