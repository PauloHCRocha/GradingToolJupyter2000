"""Top-level functions called from JavaScript. Returns plain dict/list values."""

from __future__ import annotations

import csv as _csv
import io
import secrets

import ai_detection
import anonymizer
import grade_suggester
import notebook_parser
import plagiarism
import question_detector
import question_window
import state
import submission_loader


def _enabled_question_ids() -> set[str]:
    return {q["id"] for q in state.get_questions() if q.get("enabled", True)}


def _enabled_questions() -> list[dict]:
    return [q for q in state.get_questions() if q.get("enabled", True)]


def _student_info(rec):
    grades = state.get_grades(rec.id)
    enabled = _enabled_question_ids()
    total = sum(g.points for qid, g in grades.items() if qid in enabled)
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
        source = submission_loader.join_code_cells(cells)
    else:
        cells = notebook_parser.parse_python(content)
        source = notebook_parser._to_str(content)

    detection = "questions" if hits else "none"
    if not hits and file_type == "py" and cells:
        hits = [question_detector.whole_file_hit(cells)]
        detection = "whole_file"

    questions = [
        {
            "id": h.qid,
            "label": h.label,
            "max_points": h.points if h.points is not None else 0.0,
            "statement": h.statement,
            "cell_indices": list(h.cell_indices),
            # All questions are graded by default; the user can opt some out
            # in the setup screen and the toggle propagates through totals,
            # CSV export and plagiarism per-question similarity.
            "enabled": True,
        }
        for h in hits
    ]
    windows = _single_question_windows(file_type, cells, questions) or question_window.compute_windows(cells, questions)
    state.set_solution(filename, file_type, cells, questions, windows, source)
    return {
        "filename": filename,
        "file_type": file_type,
        "detection": detection,
        "questions": questions,
        "total_max_points": sum(q["max_points"] for q in questions if q.get("enabled", True)),
        "question_windows": windows,
    }


def _single_question_windows(file_type, cells, questions):
    """A .py assignment with one question: that question is the whole file,
    imports above its header included — and so is every student's answer,
    whether or not they kept the header."""
    if file_type == "py" and len(questions) == 1 and cells:
        return {questions[0]["id"]: list(range(len(cells)))}
    return None


def update_questions(questions):
    # Coerce each entry into a clean dict with a default enabled=True so old
    # callers that don't send the field still produce well-formed state.
    qs = []
    for q in questions:
        d = dict(q)
        d.setdefault("enabled", True)
        qs.append(d)
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
        "source": state.get_solution_source(),
    }


def _match_windows(rec, questions):
    """Which of the student's cells answer each question."""
    student_questions = question_window.detect_in_cells(rec.cells, rec.file_type)
    if questions:
        student_by_id = {q["id"]: q for q in student_questions}
        merged = []
        for q in questions:
            sq = student_by_id.get(q["id"])
            # Notebooks built from the same template line up cell by
            # cell, so the solution's position is a fair guess. A .py
            # file's cells depend on its own headers — no guessing;
            # the UI falls back to the whole file instead.
            fallback = q.get("cell_indices", []) if rec.file_type == "ipynb" else []
            merged.append({
                **q,
                "cell_indices": sq["cell_indices"] if sq else fallback,
            })
        windows = question_window.compute_windows(rec.cells, merged)
    else:
        windows = question_window.compute_windows(rec.cells, student_questions)
    rec.question_windows = _single_question_windows(rec.file_type, rec.cells, questions) or windows


def _store_submissions(records, warnings):
    if not records:
        raise ValueError("No .ipynb or .py submissions found.")
    state.reset_submissions()
    questions = state.get_questions()
    for rec in records:
        if rec.cells:
            _match_windows(rec, questions)
            rec.invisible_findings = ai_detection.detect_invisible(rec.cells)
        state.add_student(rec)
    return {
        "students": [_student_info(r) for r in state.list_students_sorted_by_name()],
        "warnings": warnings,
    }


def upload_submissions(content):
    return _store_submissions(*submission_loader.load_zip(content))


def upload_submission_files(files):
    """Students' .py / .ipynb files dropped one by one instead of a zip."""
    return _store_submissions(*submission_loader.load_files(files))


def clear_solution():
    state.clear_solution()


def clear_submissions():
    state.reset_submissions()


def rematch_submissions():
    """A new solution file was analyzed: match the loaded submissions to its
    questions again. Grades already given are kept."""
    questions = state.get_questions()
    for rec in state.list_students_ordered():
        if rec.cells:
            _match_windows(rec, questions)
    return [_student_info(r) for r in state.list_students_sorted_by_name()]


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
        "source": rec.source,
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


def _build_clusters_payload(matrix, students, cluster_threshold):
    """Compute clusters and decorate with names/numbers — used by both
    plagiarism_analyze and plagiarism_cluster."""
    raw = plagiarism.cluster_students(matrix, threshold=float(cluster_threshold))
    decorated = []
    for c in raw["clusters"]:
        members = c["members"]
        decorated.append({
            "id": c["id"],
            "size": c["size"],
            "avg_similarity": c["avg_similarity"],
            "members": members,
            "member_ids": [students[m].id for m in members],
            "member_names": [students[m].name for m in members],
        })
    return {
        "cluster_assignments": raw["cluster_assignments"],
        "clusters": decorated,
        "outliers": raw["outliers"],
        "num_clusters": raw["num_clusters"],
    }


def plagiarism_analyze(threshold, cluster_threshold=0.7):
    students = state.list_students_sorted_by_name()
    if len(students) < 2:
        raise ValueError("Need at least 2 submissions.")
    codes = [plagiarism.extract_code(s.cells) for s in students]
    matrix = plagiarism.compute_matrix(codes)
    state.set_plagiarism(matrix, [s.id for s in students])

    pairs_raw = plagiarism.find_suspicious_pairs(matrix, float(threshold))
    clusters_payload = _build_clusters_payload(matrix, students, cluster_threshold)
    cluster_of = clusters_payload["cluster_assignments"]

    pairs = [
        {
            "student1_id": students[i].id,
            "student1_name": students[i].name,
            "student1_index": i,
            "student2_id": students[j].id,
            "student2_name": students[j].name,
            "student2_index": j,
            "similarity": sim,
            "cluster_id": cluster_of[i] if cluster_of[i] == cluster_of[j] else -1,
        }
        for i, j, sim in pairs_raw
    ]
    n = len(students)
    upper = [matrix[i][j] for i in range(n) for j in range(i + 1, n)]
    high = sum(1 for s in upper if s >= 0.95)
    avg = (sum(upper) / len(upper)) if upper else 0.0

    return {
        "threshold": float(threshold),
        "cluster_threshold": float(cluster_threshold),
        "matrix": matrix,
        "student_ids": [s.id for s in students],
        "student_names": [s.name for s in students],
        "suspicious_pairs": pairs,
        "stats": {
            "total_comparisons": len(upper),
            "suspicious_count": len(pairs),
            "high_similarity_count": high,
            "avg_similarity": avg,
            "num_clusters": clusters_payload["num_clusters"],
            "largest_cluster": max((c["size"] for c in clusters_payload["clusters"]), default=0),
            "outliers_count": len(clusters_payload["outliers"]),
        },
        **clusters_payload,
    }


def plagiarism_cluster(threshold=0.7):
    """Re-cluster students with a different threshold without recomputing
    the (expensive) similarity matrix. Requires plagiarism_analyze to have
    run before."""
    matrix, ids = state.get_plagiarism()
    if matrix is None:
        raise ValueError("Run plagiarism analysis first.")
    students_by_id = {s.id: s for s in state.list_students_sorted_by_name()}
    students = [students_by_id[i] for i in ids if i in students_by_id]
    return _build_clusters_payload(matrix, students, threshold)


def plagiarism_compare(student1_id, student2_id):
    s1 = state.get_student(student1_id)
    s2 = state.get_student(student2_id)
    if s1 is None or s2 is None:
        raise ValueError("One of the students was not found.")
    code1 = plagiarism.extract_code(s1.cells)
    code2 = plagiarism.extract_code(s2.cells)

    questions = _enabled_questions()
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
            blocks = plagiarism.analyze_blocks(c1, c2)
        else:
            tf = asts = sim = 0.0
            blocks = []
        q_results.append({
            "question_id": qid,
            "similarity": sim,
            "tfidf": tf,
            "ast": asts,
            "code1": c1,
            "code2": c2,
            "matching_blocks": blocks,
        })

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


def _roster_names():
    return [s.name for s in state.list_students_ordered()]


def anonymize_reference(text, kind="code"):
    """Teacher-side text (statements, reference code) gets the same scrub —
    a template can mention a student, and nothing personal should leave."""
    scrubber = anonymizer.Scrubber(roster_names=_roster_names())
    if kind == "code":
        return anonymizer.scrub_python(text or "", scrubber)
    return scrubber.code_wide(scrubber.text(text or ""))


def _anonymize_record(rec, roster, strip_comments, include_outputs):
    scrubber = anonymizer.Scrubber(name=rec.name, number=rec.id, roster_names=roster)
    if rec.file_type == "py":
        text = anonymizer.scrub_python(rec.source, scrubber, strip_comments)
    else:
        text = anonymizer.anonymize_notebook(rec.cells, scrubber, strip_comments, include_outputs)
    return text, scrubber.count


def anonymized_submissions(strip_comments=False, include_outputs=False):
    """One scrubbed payload per gradable student, in random order, each with
    a random pseudonym. Only `text` is ever sent out; `student_id` stays in
    the browser to map results back."""
    roster = _roster_names()
    out = []
    for rec in state.list_students_ordered():
        if rec.error is not None or not rec.cells:
            continue
        text, count = _anonymize_record(rec, roster, bool(strip_comments), bool(include_outputs))
        out.append({
            "student_id": rec.id,
            "pseudonym": "S-" + secrets.token_hex(3).upper(),
            "file_type": rec.file_type,
            "text": text,
            "redactions": count,
        })
    secrets.SystemRandom().shuffle(out)
    return out


def anonymized_preview(student_id, strip_comments=False, include_outputs=False):
    rec = state.get_student(student_id)
    if rec is None:
        raise ValueError(f"Student {student_id} not found.")
    text, count = _anonymize_record(rec, _roster_names(), bool(strip_comments), bool(include_outputs))
    return {"text": text, "redactions": count}


def export_grades_csv():
    # Only the questions the teacher chose to grade end up in the CSV.
    questions = _enabled_questions()
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
