"""Plagiarism detection — pure-Python TF-IDF + AST + token similarity (no numpy/sklearn)."""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass, field

from notebook_parser import Cell


@dataclass
class _Features:
    num_functions: int = 0
    num_classes: int = 0
    num_loops: int = 0
    num_if: int = 0
    num_assigns: int = 0
    num_calls: int = 0
    control_flow: list = field(default_factory=list)


def _ast_features(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    f = _Features()
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
    keys = ["num_functions", "num_classes", "num_loops", "num_if", "num_assigns", "num_calls"]
    structural = 0.0
    for k in keys:
        v1, v2 = getattr(f1, k), getattr(f2, k)
        if v1 == 0 and v2 == 0:
            structural += 1.0
        elif v1 == 0 or v2 == 0:
            structural += 0.0
        else:
            structural += 1.0 - abs(v1 - v2) / max(v1, v2)
    structural /= len(keys)
    cf = _seq_jaccard(" ".join(f1.control_flow), " ".join(f2.control_flow))
    return 0.7 * structural + 0.3 * cf


def _tokenize(code: str) -> list[str]:
    code = re.sub(r"[\"\'].*?[\"\']", "", code)
    code = re.sub(r"#.*", "", code)
    return re.findall(r"\w+|[+\-*/%=<>!]+|\(|\)|\[|\]|\{|\}|,|:|;", code)


def _tfidf_vec(tokens: list[str], df: dict, n_docs: int) -> dict:
    """Compute a TF-IDF vector for a single document."""
    if not tokens:
        return {}
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    vec = {}
    for t, f in tf.items():
        # Smoothed IDF, similar to sklearn defaults (with smooth_idf=True).
        idf = math.log((n_docs + 1) / (df.get(t, 0) + 1)) + 1.0
        vec[t] = (f / len(tokens)) * idf
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {t: v / norm for t, v in vec.items()}


def _cosine(v1: dict, v2: dict) -> float:
    keys = set(v1) & set(v2)
    return sum(v1[t] * v2[t] for t in keys)


def tfidf_similarity(code1: str, code2: str) -> float:
    if not code1.strip() or not code2.strip():
        return 0.0
    t1 = _tokenize(code1)
    t2 = _tokenize(code2)
    if not t1 or not t2:
        return 0.0
    df = {}
    for t in set(t1):
        df[t] = df.get(t, 0) + 1
    for t in set(t2):
        df[t] = df.get(t, 0) + 1
    v1 = _tfidf_vec(t1, df, 2)
    v2 = _tfidf_vec(t2, df, 2)
    return max(0.0, _cosine(v1, v2))


def token_similarity(code1: str, code2: str) -> float:
    s1, s2 = set(_tokenize(code1)), set(_tokenize(code2))
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


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


def compute_matrix(student_codes: list[str]) -> list[list[float]]:
    n = len(student_codes)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            sim = hybrid_similarity(student_codes[i], student_codes[j])
            matrix[i][j] = sim
            matrix[j][i] = sim
    for i in range(n):
        matrix[i][i] = 1.0
    return matrix


def find_suspicious_pairs(matrix: list[list[float]], threshold: float):
    n = len(matrix)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] >= threshold:
                pairs.append((i, j, float(matrix[i][j])))
    pairs.sort(key=lambda p: p[2], reverse=True)
    return pairs
