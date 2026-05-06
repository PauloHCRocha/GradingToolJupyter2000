"""Multi-criteria grade suggestion. Ported from the Flask app's calculate_suggested_grade.

Compares a student's code for one question against the reference solution code
and produces (grade, score, confidence, comment).
"""

from __future__ import annotations

import re
from typing import Literal

Confidence = Literal["high", "medium", "low", "none"]


def _clean_code(code: str) -> str:
    out = []
    for line in code.split("\n"):
        cleaned = re.sub(r"#.*", "", line).rstrip()
        if cleaned:
            out.append(cleaned)
    return "\n".join(out)


def _score_imports(code: str, ref: str) -> float:
    ref_imports = set(re.findall(r"import\s+(\w+)", ref))
    ref_from = set(re.findall(r"from\s+(\w+)", ref))
    if not ref_imports and not ref_from:
        return 1.0
    student = set(re.findall(r"import\s+(\w+)", code)) | set(re.findall(r"from\s+(\w+)", code))
    needed = ref_imports | ref_from
    return len(needed & student) / len(needed) if needed else 1.0


def _score_logic(code: str, ref: str) -> float:
    score = 0.0
    checks = 0

    ref_funcs = re.findall(r"def\s+(\w+)", ref)
    if ref_funcs:
        checks += 1
        student_funcs = re.findall(r"def\s+(\w+)", code)
        if student_funcs:
            score += 1.0 if any(f in student_funcs for f in ref_funcs) else 0.7

    if re.search(r"\b(for|while)\b", ref):
        checks += 1
        if re.search(r"\b(for|while)\b", code):
            score += 1.0

    if re.search(r"\bif\b", ref):
        checks += 1
        if re.search(r"\bif\b", code):
            score += 1.0

    return score / checks if checks else 1.0


def _score_operations(code: str, ref: str) -> float:
    score = 0.0
    checks = 0

    if "open(" in ref:
        checks += 1
        if "open(" in code:
            score += 1.0
        elif "read" in code or "write" in code:
            score += 0.5

    if re.search(r"\[.*\]|\blist\(", ref):
        checks += 1
        if re.search(r"\[.*\]|\blist\(", code):
            score += 1.0

    if re.search(r"\{.*\}|\bdict\(", ref):
        checks += 1
        if re.search(r"\{.*\}|\bdict\(", code):
            score += 1.0

    ref_methods = set(re.findall(r"\.(\w+)\(", ref))
    if ref_methods:
        checks += 1
        student_methods = set(re.findall(r"\.(\w+)\(", code))
        score += len(ref_methods & student_methods) / len(ref_methods)

    return score / checks if checks else 1.0


def _score_output(code: str, ref: str) -> float:
    score = 0.0
    checks = 0

    ref_prints = len(re.findall(r"\bprint\(", ref))
    if ref_prints:
        checks += 1
        student_prints = len(re.findall(r"\bprint\(", code))
        if student_prints:
            score += min(student_prints / ref_prints, 1.0)

    ref_returns = len(re.findall(r"\breturn\b", ref))
    if ref_returns:
        checks += 1
        if re.search(r"\breturn\b", code):
            score += 1.0

    return score / checks if checks else 1.0


def _score_completeness(code: str, ref: str) -> float:
    ref_lines = len([l for l in ref.split("\n") if l.strip()])
    student_lines = len([l for l in code.split("\n") if l.strip()])
    if student_lines == 0:
        return 0.0
    if ref_lines == 0:
        return 1.0
    ratio = student_lines / ref_lines
    if 0.5 <= ratio <= 2.0:
        return 1.0
    if ratio < 0.5:
        return ratio / 0.5
    return max(0.3, 2.0 / ratio)


def _grade_curve(score: float, max_points: float) -> float:
    if score >= 0.90:
        pct = 1.0
    elif score >= 0.75:
        pct = 0.85 + (score - 0.75)
    elif score >= 0.60:
        pct = 0.70 + (score - 0.60)
    elif score >= 0.40:
        pct = 0.50 + (score - 0.40)
    elif score >= 0.20:
        pct = 0.30 + (score - 0.20)
    else:
        pct = score * 1.5
    pct = min(1.0, pct)
    return round(pct * max_points, 2)


def _build_comment(scores: dict[str, float], grade: float, max_points: float, score: float, confidence: str) -> str:
    lines: list[str] = []
    if grade == max_points:
        lines.append("✓ Excelente! Solução completa e correta.")
    elif grade >= max_points * 0.85:
        lines.append("✓ Muito bom! Solução quase completa.")
    elif grade >= max_points * 0.70:
        lines.append("✓ Bom trabalho! Alguns aspetos podem melhorar.")
    elif grade >= max_points * 0.50:
        lines.append("○ Solução parcial. Vários elementos em falta.")
    else:
        lines.append("○ Solução incompleta. Faltam elementos essenciais.")
    lines.append("")

    weak_keys = {
        "imports": "Imports",
        "logic": "Estruturas lógicas (funções/loops/condicionais)",
        "operations": "Operações-chave (file I/O, data structures, métodos)",
        "output": "Output (prints/returns)",
    }
    for key, label in weak_keys.items():
        s = scores[key]
        if s < 0.7:
            mark = "✗" if s == 0 else "○"
            pct = int(s * 100)
            lines.append(f"{mark} {label} ({pct}%)" if s > 0 else f"{mark} {label} em falta")

    if scores["completeness"] < 0.7:
        lines.append(f"○ Código muito {'curto' if scores['completeness'] < 0.5 else 'longo'}")

    strengths = []
    if scores["imports"] >= 0.9:
        strengths.append("imports corretos")
    if scores["logic"] >= 0.9:
        strengths.append("boa estrutura lógica")
    if scores["operations"] >= 0.9:
        strengths.append("operações corretas")
    if scores["output"] >= 0.9:
        strengths.append("output adequado")
    if strengths:
        lines.append("")
        lines.append("Pontos fortes: " + ", ".join(strengths))

    lines.append("")
    lines.append(f"Score geral: {int(score * 100)}% (confiança: {confidence})")
    return "\n".join(lines)


def suggest_grade(student_code: str, reference: str, max_points: float) -> tuple[float | None, float, Confidence, str]:
    if not student_code or not student_code.strip():
        return 0.0, 0.0, "low", "○ Sem código submetido."
    if not reference or not reference.strip():
        return None, 0.0, "none", "Sem solução de referência disponível para esta questão."

    code = _clean_code(student_code)
    ref = _clean_code(reference)
    scores = {
        "imports": _score_imports(code, ref),
        "logic": _score_logic(code, ref),
        "operations": _score_operations(code, ref),
        "output": _score_output(code, ref),
        "completeness": _score_completeness(code, ref),
    }
    final = (
        0.15 * scores["imports"]
        + 0.25 * scores["logic"]
        + 0.25 * scores["operations"]
        + 0.20 * scores["output"]
        + 0.15 * scores["completeness"]
    )
    good = sum(1 for s in scores.values() if s >= 0.7)
    confidence: Confidence = "high" if good >= 4 else "medium" if good >= 3 else "low"
    grade = _grade_curve(final, max_points)
    comment = _build_comment(scores, grade, max_points, final, confidence)
    return grade, final, confidence, comment
