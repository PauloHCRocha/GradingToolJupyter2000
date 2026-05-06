"""Top-level functions called from JavaScript. Returns plain dict/list values."""

from __future__ import annotations

import csv as _csv
import io
import sys
import time
import traceback
from dataclasses import asdict

import ai_detection
import grade_suggester
import notebook_parser
import plagiarism
import question_detector
import question_window
import state
import submission_loader


def _student_info(rec):
    grades = state.get_grades(rec.id)
    total = sum(g.points for g in grades.values())
    return {
        "id": rec.id,
        "name": rec.name,
        "filename": rec.filename,
        "file_type": rec.file_type,
        "has_error": rec.error is not None,
        "error": rec.error,
        "total_grade": total,
        "invisible_count": len(rec.invisible_findings),
    }


def _cell_to_dict(c):
    return {
        "cell_id": c.cell_id,
        "cell_type": c.cell_type,
        "source": c.source,
        "output": c.output,
    }


def analyze_solution(content, filename):
    file_type, hits = question_detector.detect(filename, content)
    if file_type == "ipynb":
        cells = notebook_parser.parse_notebook(content)
    else:
        cells = notebook_parser.parse_python(content)

    questions = [
        {
            "id": h.qid,
            "label": h.label,
            "max_points": h.points if h.points is not None else 0.0,
            "statement": h.statement,
            "cell_indices": list(h.cell_indices),
        }
        for h in hits
    ]
    windows = question_window.compute_windows(cells, questions)
    state.set_solution(filename, file_type, cells, questions, windows)
    return {
        "filename": filename,
        "file_type": file_type,
        "questions": questions,
        "total_max_points": sum(q["max_points"] for q in questions),
        "question_windows": windows,
    }


def update_questions(questions):
    qs = [dict(q) for q in questions]
    state.set_questions(qs)
    return qs


def get_solution_cells():
    cells, windows, filename, file_type = state.get_solution()
    if not filename:
        raise ValueError("No solution uploaded yet.")
    return {
        "filename": filename,
        "file_type": file_type or "ipynb",
        "cells": [_cell_to_dict(c) for c in cells],
        "question_windows": windows,
    }


def upload_submissions(content):
    records, warnings = submission_loader.load_zip(content)
    if not records:
        raise ValueError("No .ipynb or .py submissions found in the zip.")

    state.reset_submissions()
    questions = state.get_questions()
    for rec in records:
        if rec.cells:
            student_questions = question_window.detect_in_cells(rec.cells)
            if questions:
                student_by_id = {q["id"]: q for q in student_questions}
                merged = []
                for q in questions:
                    sq = student_by_id.get(q["id"])
                    merged.append({
                        **q,
                        "cell_indices": sq["cell_indices"] if sq else q.get("cell_indices", []),
                    })
                rec.question_windows = question_window.compute_windows(rec.cells, merged)
            else:
                rec.question_windows = question_window.compute_windows(rec.cells, student_questions)
            rec.invisible_findings = ai_detection.detect_invisible(rec.cells)
        state.add_student(rec)

    return {
        "students": [_student_info(r) for r in state.list_students_sorted_by_name()],
        "warnings": warnings,
    }


def list_submissions(sort="name"):
    if sort == "number":
        recs = state.list_students_sorted_by_number()
    else:
        recs = state.list_students_sorted_by_name()
    return [_student_info(r) for r in recs]


def get_submission(student_id):
    rec = state.get_student(student_id)
    if rec is None:
        raise ValueError(f"Student {student_id} not found.")
    return {
        "info": _student_info(rec),
        "cells": [_cell_to_dict(c) for c in rec.cells],
        "question_windows": rec.question_windows,
        "invisible_findings": list(rec.invisible_findings),
    }


def get_student_grades(student_id):
    rec = state.get_student(student_id)
    if rec is None:
        raise ValueError(f"Student {student_id} not found.")
    grades = state.get_grades(student_id)
    entries = [
        {"question_id": qid, "points": g.points, "comment": g.comment}
        for qid, g in grades.items()
    ]
    return {
        "student_id": student_id,
        "entries": entries,
        "total": sum(e["points"] for e in entries),
    }


def set_student_grade(student_id, question_id, points, comment=""):
    rec = state.get_student(student_id)
    if rec is None:
        raise ValueError(f"Student {student_id} not found.")
    state.set_grade(student_id, question_id, state.GradeEntry(points=float(points), comment=comment or ""))
    return get_student_grades(student_id)


def suggest(student_id, question_id):
    rec = state.get_student(student_id)
    if rec is None:
        raise ValueError(f"Student {student_id} not found.")
    questions = state.get_questions()
    q = next((x for x in questions if x["id"] == question_id), None)
    if q is None:
        raise ValueError(f"Question {question_id} not found.")
    max_points = float(q.get("max_points") or 0.0)

    sol_cells, sol_windows, _, _ = state.get_solution()
    sol_idx = sol_windows.get(question_id, [])
    student_idx = rec.question_windows.get(question_id, [])

    student_code = plagiarism.extract_code_for_indices(rec.cells, student_idx) if student_idx else ""
    reference = plagiarism.extract_code_for_indices(sol_cells, sol_idx) if sol_idx else ""

    grade, score, confidence, comment = grade_suggester.suggest_grade(student_code, reference, max_points)
    return {
        "points": grade,
        "score": float(score),
        "confidence": confidence,
        "comment": comment,
        "max_points": max_points,
    }


def run_code(code, stdin=""):
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    real_stdin = sys.stdin
    real_stdout = sys.stdout
    real_stderr = sys.stderr
    sys.stdin = io.StringIO(stdin or "")
    sys.stdout = out_buf
    sys.stderr = err_buf
    started = time.perf_counter()
    success = True
    try:
        exec(compile(code or "", "<student_code>", "exec"), {"__name__": "__main__"})
    except Exception:
        success = False
        traceback.print_exc(file=err_buf)
    finally:
        sys.stdin = real_stdin
        sys.stdout = real_stdout
        sys.stderr = real_stderr
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "success": success,
        "output": out_buf.getvalue(),
        "error": err_buf.getvalue(),
        "duration_ms": duration_ms,
    }


def plagiarism_analyze(threshold):
    students = state.list_students_sorted_by_name()
    if len(students) < 2:
        raise ValueError("Need at least 2 submissions.")
    codes = [plagiarism.extract_code(s.cells) for s in students]
    matrix = plagiarism.compute_matrix(codes)
    state.set_plagiarism(matrix, [s.id for s in students])

    pairs_raw = plagiarism.find_suspicious_pairs(matrix, float(threshold))
    pairs = [
        {
            "student1_id": students[i].id,
            "student1_name": students[i].name,
            "student2_id": students[j].id,
            "student2_name": students[j].name,
            "similarity": sim,
        }
        for i, j, sim in pairs_raw
    ]
    n = len(students)
    upper = [matrix[i][j] for i in range(n) for j in range(i + 1, n)]
    high = sum(1 for s in upper if s >= 0.95)
    avg = (sum(upper) / len(upper)) if upper else 0.0

    return {
        "threshold": float(threshold),
        "matrix": matrix,
        "student_ids": [s.id for s in students],
        "student_names": [s.name for s in students],
        "suspicious_pairs": pairs,
        "stats": {
            "total_comparisons": len(upper),
            "suspicious_count": len(pairs),
            "high_similarity_count": high,
            "avg_similarity": avg,
        },
    }


def plagiarism_compare(student1_id, student2_id):
    s1 = state.get_student(student1_id)
    s2 = state.get_student(student2_id)
    if s1 is None or s2 is None:
        raise ValueError("One of the students was not found.")
    code1 = plagiarism.extract_code(s1.cells)
    code2 = plagiarism.extract_code(s2.cells)

    questions = state.get_questions()
    q_results = []
    for q in questions:
        qid = q["id"]
        idx1 = s1.question_windows.get(qid, [])
        idx2 = s2.question_windows.get(qid, [])
        c1 = plagiarism.extract_code_for_indices(s1.cells, idx1) if idx1 else ""
        c2 = plagiarism.extract_code_for_indices(s2.cells, idx2) if idx2 else ""
        if c1.strip() and c2.strip():
            tf = plagiarism.tfidf_similarity(c1, c2)
            asts = plagiarism.ast_similarity(c1, c2)
            sim = 0.6 * tf + 0.4 * asts
        else:
            tf = asts = sim = 0.0
        q_results.append({"question_id": qid, "similarity": sim, "tfidf": tf, "ast": asts})

    matrix, ids = state.get_plagiarism()
    overall = 0.0
    if matrix is not None and student1_id in ids and student2_id in ids:
        i = ids.index(student1_id)
        j = ids.index(student2_id)
        overall = float(matrix[i][j])
    if overall == 0.0:
        overall = plagiarism.hybrid_similarity(code1, code2)

    return {
        "student1_id": s1.id,
        "student1_name": s1.name,
        "student2_id": s2.id,
        "student2_name": s2.name,
        "overall_similarity": overall,
        "questions": q_results,
        "code1": code1,
        "code2": code2,
    }


def export_grades_csv():
    questions = state.get_questions()
    qids = [q["id"] for q in questions]

    buf = io.StringIO()
    writer = _csv.writer(buf)
    header = ["Student Name", "Student Number"]
    for qid in qids:
        header.extend([qid, f"{qid}_comment"])
    header.extend(["Total", "Max Points"])
    writer.writerow(header)

    max_points = sum(q.get("max_points", 0) for q in questions)
    for rec in state.list_students_sorted_by_name():
        grades = state.get_grades(rec.id)
        row = [rec.name, rec.id]
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

    return buf.getvalue()
