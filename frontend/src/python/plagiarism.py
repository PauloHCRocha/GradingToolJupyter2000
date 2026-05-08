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


# ---------------------------------------------------------------------------
# Density-based clustering on the similarity matrix.
# Two students fall in the same cluster if they're above `threshold` similar.
# ---------------------------------------------------------------------------
def cluster_students(matrix: list[list[float]], threshold: float = 0.7):
    n = len(matrix)
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
            clusters.append({
                "id": cur,
                "members": members,
                "size": len(members),
                "avg_similarity": avg / count if count else 0.0,
            })
            cur += 1
    outliers = [i for i in range(n) if cluster_id[i] == -1]
    return {
        "cluster_assignments": cluster_id,
        "clusters": clusters,
        "outliers": outliers,
        "num_clusters": cur,
    }


# ---------------------------------------------------------------------------
# Matching-block detection (port of highlight_similar_lines from the old Flask
# tool). Returns *only* the line ranges + classification — the frontend renders
# the bubbles. Two-stage normalization pipeline:
#   1. strip_comments → preserves Python code intent without comments
#   2. normalize_for_structure → normalizes whitespace, quotes, parens, then
#      replaces identifiers with VAR / numbers with NUM, keeping keywords
# A SequenceMatcher then aligns blocks of normalized lines; each matched block
# is classified:
#   - "exact"   : identical without comments
#   - "similar" : same structure, different variable names
#   - "invisible": isolated lines containing zero-width / suspicious unicode
# ---------------------------------------------------------------------------

import re as _re
import unicodedata as _ud
from difflib import SequenceMatcher as _SequenceMatcher

_PY_KEYWORDS = frozenset({
    "if", "elif", "else", "while", "for", "in", "def", "class", "return",
    "break", "continue", "pass", "import", "from", "as", "try", "except",
    "finally", "with", "lambda", "yield", "raise", "assert", "and", "or",
    "not", "is", "True", "False", "None", "global", "nonlocal", "async", "await",
})

_SUSPICIOUS_UNICODE = frozenset({
    "​", "‌", "‍", "\u200E", "\u200F",
    "\u202A", "\u202B", "\u202C", "\u202D", "\u202E",
    "⁠", "⁡", "⁢", "⁣", "⁤",
    "﻿", " ",
})


def _strip_comments(line: str) -> str:
    in_string = False
    quote = None
    out = []
    i = 0
    while i < len(line):
        ch = line[i]
        prev = line[i - 1] if i > 0 else ""
        if ch in ("'", '"') and prev != "\\":
            if not in_string:
                in_string = True
                quote = ch
            elif ch == quote:
                in_string = False
                quote = None
            out.append(ch)
        elif ch == "#" and not in_string:
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _normalize_quotes(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in ("'", '"'):
            quote = ch
            content = []
            i += 1
            while i < len(text):
                if text[i] == "\\" and i + 1 < len(text):
                    content.append(text[i])
                    content.append(text[i + 1])
                    i += 2
                elif text[i] == quote:
                    out.append('"')
                    out.extend(content)
                    out.append('"')
                    i += 1
                    break
                else:
                    content.append(text[i])
                    i += 1
            else:
                # Unterminated string — write what we have.
                out.append('"')
                out.extend(content)
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _normalize_for_structure(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    indent_match = _re.match(r"^(\s*)", line)
    indent = indent_match.group(1) if indent_match else ""

    s = _normalize_quotes(stripped)
    # tighten whitespace around brackets/parens/braces
    s = _re.sub(r"\s+\(", "(", s)
    s = _re.sub(r"\s+\[", "[", s)
    s = _re.sub(r"\s+\{", "{", s)
    s = _re.sub(r"\(\s+", "(", s)
    s = _re.sub(r"\s+\)", ")", s)
    s = _re.sub(r"\[\s+", "[", s)
    s = _re.sub(r"\s+\]", "]", s)
    s = _re.sub(r"\{\s+", "{", s)
    s = _re.sub(r"\s+\}", "}", s)
    # spaces around binary operators (best-effort)
    s = _re.sub(r"([^\s])\*\*([^\s])", r"\1 ** \2", s)
    s = _re.sub(r"([^\s])([+\-*/%])([^\s])", r"\1 \2 \3", s)
    s = _re.sub(r"([^\s])([<>=!]=?)([^\s])", r"\1 \2 \3", s)
    s = _re.sub(r"([^\s])([,;:])([^\s])", r"\1\2 \3", s)
    # collapse runs of spaces inside the line
    s = _re.sub(r" +", " ", s)

    tokens = _re.findall(r"\w+|[^\w\s]|\s+", s)
    out = []
    for tok in tokens:
        if tok.strip() == "":
            out.append(tok)
        elif tok in _PY_KEYWORDS:
            out.append(tok)
        elif tok.isdigit():
            out.append("NUM")
        elif _re.match(r"^[a-zA-Z_]\w*$", tok):
            out.append("VAR")
        else:
            out.append(tok)
    return indent + "".join(out)


def _detect_invisible_lines(lines: list[str]) -> set[int]:
    suspicious = set()
    for line_idx, line in enumerate(lines):
        for ch in line:
            if ch in _SUSPICIOUS_UNICODE:
                suspicious.add(line_idx)
                break
            if ord(ch) > 127 and ch not in ("\n", "\r", "\t"):
                cat = _ud.category(ch)
                if cat in ("Cc", "Cf", "Cs", "Co"):
                    suspicious.add(line_idx)
                    break
    return suspicious


def analyze_blocks(code1: str, code2: str) -> list[dict]:
    """Return matching/invisible blocks between two code strings.

    Each block is {id, start1, end1, start2, end2, color, type, size}.
    Lines are 0-indexed, end is exclusive. -1 in start/end means "no
    counterpart on the other side" (used for invisible-char blocks).
    """
    if not code1 or not code2:
        return []

    lines1 = code1.split("\n")
    lines2 = code2.split("\n")

    no_comments1 = [_strip_comments(line) for line in lines1]
    no_comments2 = [_strip_comments(line) for line in lines2]
    norm1 = [_normalize_for_structure(line) for line in no_comments1]
    norm2 = [_normalize_for_structure(line) for line in no_comments2]

    matcher = _SequenceMatcher(None, norm1, norm2, autojunk=False)
    blocks: list[dict] = []
    block_id = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        # Only multi-line equal runs count as plagiarism evidence.
        if tag != "equal" or (i2 - i1) < 2:
            continue
        exact = all(no_comments1[a] == no_comments2[b]
                    for a, b in zip(range(i1, i2), range(j1, j2)))
        kind = "exact" if exact else "similar"
        color = "#ef4444" if exact else "#f59e0b"
        blocks.append({
            "id": f"blk{block_id}",
            "start1": i1, "end1": i2,
            "start2": j1, "end2": j2,
            "color": color,
            "type": kind,
            "size": i2 - i1,
        })
        block_id += 1

    # Invisible-char lines that aren't already inside a block.
    invisible1 = _detect_invisible_lines(lines1)
    invisible2 = _detect_invisible_lines(lines2)

    def in_left_block(line: int) -> bool:
        return any(b["start1"] <= line < b["end1"] for b in blocks if b["start1"] >= 0)

    def in_right_block(line: int) -> bool:
        return any(b["start2"] <= line < b["end2"] for b in blocks if b["start2"] >= 0)

    for line in sorted(invisible1):
        if not in_left_block(line):
            blocks.append({
                "id": f"inv1_{line}",
                "start1": line, "end1": line + 1,
                "start2": -1, "end2": -1,
                "color": "#3b82f6",
                "type": "invisible",
                "size": 1,
            })
    for line in sorted(invisible2):
        if not in_right_block(line):
            blocks.append({
                "id": f"inv2_{line}",
                "start1": -1, "end1": -1,
                "start2": line, "end2": line + 1,
                "color": "#3b82f6",
                "type": "invisible",
                "size": 1,
            })

    return blocks
