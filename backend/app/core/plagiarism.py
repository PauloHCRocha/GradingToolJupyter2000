"""Plagiarism detection — hybrid TF-IDF + AST + token similarity. Ported from old Flask app."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.notebook_parser import Cell


@dataclass
class _Features:
    num_functions: int = 0
    num_classes: int = 0
    num_loops: int = 0
    num_if: int = 0
    num_assigns: int = 0
    num_calls: int = 0
    control_flow: list[str] = None  # type: ignore[assignment]


def _ast_features(code: str) -> _Features | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    f = _Features(control_flow=[])
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            f.num_functions += 1
        elif isinstance(node, ast.ClassDef):
            f.num_classes += 1
        elif isinstance(node, (ast.For, ast.While)):
            f.num_loops += 1
            f.control_flow.append("loop")
        elif isinstance(node, ast.If):
            f.num_if += 1
            f.control_flow.append("if")
        elif isinstance(node, ast.Assign):
            f.num_assigns += 1
        elif isinstance(node, ast.Call):
            f.num_calls += 1
    return f


def _seq_jaccard(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def ast_similarity(code1: str, code2: str) -> float:
    f1, f2 = _ast_features(code1), _ast_features(code2)
    if f1 is None or f2 is None:
        return 0.0
    numeric = ["num_functions", "num_classes", "num_loops", "num_if", "num_assigns", "num_calls"]
    structural = 0.0
    for k in numeric:
        v1, v2 = getattr(f1, k), getattr(f2, k)
        if v1 == 0 and v2 == 0:
            structural += 1.0
        elif v1 == 0 or v2 == 0:
            structural += 0.0
        else:
            structural += 1.0 - abs(v1 - v2) / max(v1, v2)
    structural /= len(numeric)
    cf = _seq_jaccard(" ".join(f1.control_flow), " ".join(f2.control_flow))
    return 0.7 * structural + 0.3 * cf


def _tokenize(code: str) -> list[str]:
    code = re.sub(r"[\"\'].*?[\"\']", "", code)
    code = re.sub(r"#.*", "", code)
    return re.findall(r"\w+|[+\-*/%=<>!]+|\(|\)|\[|\]|\{|\}|,|:|;", code)


def tfidf_similarity(code1: str, code2: str) -> float:
    if not code1.strip() or not code2.strip():
        return 0.0
    try:
        v = TfidfVectorizer(token_pattern=r"\w+|[+\-*/%=<>!]+")
        m = v.fit_transform([code1, code2])
        return float(cosine_similarity(m[0:1], m[1:2])[0][0])
    except Exception:
        return 0.0


def token_similarity(code1: str, code2: str) -> float:
    t1, t2 = set(_tokenize(code1)), set(_tokenize(code2))
    if not t1 and not t2:
        return 1.0
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def hybrid_similarity(code1: str, code2: str) -> float:
    if not code1.strip() or not code2.strip():
        return 0.0
    return (
        0.4 * tfidf_similarity(code1, code2)
        + 0.3 * ast_similarity(code1, code2)
        + 0.3 * token_similarity(code1, code2)
    )


def extract_code(cells: list[Cell]) -> str:
    parts: list[str] = []
    for cell in cells:
        if cell.cell_type == "code":
            lines = [line for line in cell.source.split("\n") if line.strip() and not line.strip().startswith("#")]
            parts.append("\n".join(lines))
    return "\n\n".join(parts)


def extract_code_for_indices(cells: list[Cell], indices: list[int]) -> str:
    return extract_code([cells[i] for i in indices if 0 <= i < len(cells)])


def compute_matrix(student_codes: list[str]) -> np.ndarray:
    n = len(student_codes)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            sim = hybrid_similarity(student_codes[i], student_codes[j])
            matrix[i][j] = sim
            matrix[j][i] = sim
    np.fill_diagonal(matrix, 1.0)
    return matrix


def find_suspicious_pairs(matrix: np.ndarray, threshold: float) -> list[tuple[int, int, float]]:
    n = matrix.shape[0]
    pairs: list[tuple[int, int, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] >= threshold:
                pairs.append((i, j, float(matrix[i][j])))
    pairs.sort(key=lambda p: p[2], reverse=True)
    return pairs


def cluster_students(matrix: np.ndarray, threshold: float = 0.7) -> dict:
    n = matrix.shape[0]
    visited = [False] * n
    cluster_id = [-1] * n
    clusters: list[dict] = []
    cur = 0
    for i in range(n):
        if visited[i]:
            continue
        members = [i]
        visited[i] = True
        for j in range(n):
            if i != j and not visited[j] and matrix[i][j] >= threshold:
                members.append(j)
                visited[j] = True
        if len(members) >= 2:
            for m in members:
                cluster_id[m] = cur
            avg = 0.0
            count = 0
            for a in range(len(members)):
                for b in range(a + 1, len(members)):
                    avg += matrix[members[a]][members[b]]
                    count += 1
            clusters.append({"id": cur, "members": members, "avg_similarity": avg / count if count else 0.0})
            cur += 1
    outliers = [i for i in range(n) if cluster_id[i] == -1]
    return {"cluster_assignments": cluster_id, "clusters": clusters, "outliers": outliers, "num_clusters": cur}
