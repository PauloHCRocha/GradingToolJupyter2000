"""Parse Jupyter notebooks (.ipynb) and Python sources (.py) into a uniform cell list."""

from __future__ import annotations

import io
import json
import re
import tokenize
import unicodedata
from dataclasses import dataclass


@dataclass
class Cell:
    cell_id: str
    cell_type: str  # "markdown" | "code"
    source: str
    output: str


# A column-0 comment (or bare string) that *starts* with a question marker —
# "# Q1", "## Question 2 (3 points)", "# --- Q1.2 ---", '"""Q3: ..."""' —
# opens a new cell, so .py files get the same per-question windows as
# notebooks. "(?!\s*=)" keeps commented-out code like "# q1 = 5" from matching.
QUESTION_HEADER = re.compile(
    r"^(?:#+|[rRuUbBfF]{0,2}(?:\"\"\"|'''|\"|'))[\s\-=*~#:]*(?:question|q)\s*\d+\b(?!\s*=)",
    re.IGNORECASE,
)
# "# %%" / "# %% [markdown]" cell markers (VS Code, Jupytext percent format).
CELL_MARKER = re.compile(r"^#\s*%%(?P<rest>.*)$")
# Pure decoration lines ("# =====", "#------") directly above a header belong
# to that header's cell, not to the end of the previous one.
_DECORATION = re.compile(r"^#[\s\-=*~#]*$")

# Key/value question blocks, in a docstring or a comment block:
#     """
#     ID: 1
#     Label: <statement>
#     Grade: 5 points
#     """
# Keys are matched case- and accent-insensitively.
_META_KEYS = {
    "id": {"id", "question", "pergunta", "questao", "exercicio", "exercise", "problem", "problema", "q"},
    "label": {"label", "enunciado", "statement", "descricao", "description", "texto", "text", "prompt",
              "title", "titulo"},
    "points": {"grade", "points", "pontos", "cotacao", "valor", "valores", "score", "marks", "max points",
               "pontuacao"},
}
_META_LINE = re.compile(r"^\s*([^\W\d_][\w .]{0,20}?)\s*[:=]\s*(.*)$")
_TRIPLE_OPEN = re.compile(r"^[rRuU]?(\"\"\"|''')")


def _norm_key(key: str) -> str:
    key = unicodedata.normalize("NFD", key.strip().lower())
    return "".join(c for c in key if not unicodedata.combining(c))


def parse_metadata(text: str) -> dict | None:
    """{"id", "label", "points"} from a key/value question block, or None when
    the text isn't one. Lines after "Label:" that aren't a known key continue
    the statement (statements often contain colons of their own)."""
    fields: dict[str, str] = {}
    last = None
    for line in text.splitlines():
        m = _META_LINE.match(line)
        field = None
        if m:
            key = _norm_key(m.group(1))
            field = next((f for f, keys in _META_KEYS.items() if key in keys), None)
            value = m.group(2).strip()
            # "Valor: o valor da doação" or "Pergunta: qual é…" inside a
            # statement are prose, not keys.
            if field == "points" and not re.search(r"\d", value):
                field = None
            if field == "id" and (not value or len(value) > 20):
                field = None
        if field and field not in fields:
            fields[field] = m.group(2).strip()
            last = field
        elif last == "label":
            fields["label"] += "\n" + line.strip()
    if "label" in fields:
        fields["label"] = fields["label"].strip()
    has_id = bool(fields.get("id"))
    if not ((has_id and ("label" in fields or "points" in fields)) or ("label" in fields and "points" in fields)):
        return None
    return fields


def _metadata_starts(lines: list[str], in_string: set[int]) -> set[int]:
    """Line numbers where a column-0 question block (docstring or comment
    block) begins."""
    starts: set[int] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        if i in in_string:
            i += 1
            continue
        opening = _TRIPLE_OPEN.match(line)
        if opening:
            quote = opening.group(1)
            rest = line[opening.end():]
            j = i
            if quote not in rest:
                j = i + 1
                while j < len(lines) and quote not in lines[j]:
                    j += 1
            body = "\n".join([rest] + lines[i + 1:j + 1]).split(quote)[0]
            if parse_metadata(body):
                starts.add(i)
            i = j + 1
            continue
        if line.startswith("#"):
            j = i
            while j < len(lines) and lines[j].startswith("#") and not CELL_MARKER.match(lines[j]):
                j += 1
            if j > i and parse_metadata("\n".join(l.lstrip("#").strip() for l in lines[i:j])):
                starts.add(i)
            i = max(j, i + 1)
            continue
        i += 1
    return starts


def _join(value):
    return value if isinstance(value, str) else "".join(value)


def _to_str(content):
    # Pyodide may hand us a JsProxy wrapping a TypedArray; unwrap it first.
    if hasattr(content, "to_py") and not isinstance(content, (bytes, bytearray, memoryview, str)):
        content = content.to_py()
    if isinstance(content, str):
        return content
    return bytes(content).decode("utf-8", errors="replace")


def parse_notebook(content) -> list[Cell]:
    notebook = json.loads(_to_str(content))
    cells: list[Cell] = []
    for idx, cell in enumerate(notebook.get("cells", [])):
        cell_id = cell.get("id") or f"cell-{idx}"
        cell_type = cell.get("cell_type", "code")
        source = _join(cell.get("source", []))

        output_parts: list[str] = []
        for out in cell.get("outputs", []) or []:
            if "text" in out:
                output_parts.append(_join(out["text"]))
            elif "data" in out and "text/plain" in out["data"]:
                output_parts.append(_join(out["data"]["text/plain"]))
        output = "\n".join(output_parts)

        cells.append(Cell(cell_id=cell_id, cell_type=cell_type, source=source, output=output))
    return cells


def _string_lines(source: str) -> set[int]:
    """0-based line numbers that sit *inside* a multi-line string (not its
    first line), so a "# Q1" inside a docstring never splits the file.
    Student code may not tokenize (syntax errors) — then nothing is excluded."""
    inside: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                # Token rows are 1-based: this yields the 0-based indices of
                # every line after the opening one.
                inside.update(range(tok.start[0], tok.end[0]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return set()
    return inside


def _is_header(line: str) -> bool:
    return bool(QUESTION_HEADER.match(line))


def parse_python(content) -> list[Cell]:
    source = _to_str(content)
    lines = source.splitlines()
    in_string = _string_lines(source)
    meta_starts = _metadata_starts(lines, in_string)

    # (start_line, cell_type) for each cell boundary.
    starts: list[tuple[int, str]] = [(0, "code")]
    current_type = "code"
    for i, line in enumerate(lines):
        if i in in_string:
            continue
        marker = CELL_MARKER.match(line)
        if marker:
            current_type = "markdown" if "markdown" in marker.group("rest").lower() else "code"
            starts.append((i, current_type))
            continue
        if current_type == "code" and (_is_header(line) or i in meta_starts):
            start = i
            while start > 0 and _DECORATION.match(lines[start - 1]) and not CELL_MARKER.match(lines[start - 1]):
                start -= 1
            # A header right after a "# %%" marker stays in that marker's cell.
            if starts[-1][0] < start and not (start > 0 and CELL_MARKER.match(lines[start - 1])):
                starts.append((start, "code"))

    cells: list[Cell] = []
    for n, (start, cell_type) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        chunk = lines[start:end]
        if chunk and CELL_MARKER.match(chunk[0]):
            chunk = chunk[1:]
        if cell_type == "markdown":
            chunk = [re.sub(r"^#\s?", "", l) for l in chunk]
        text = "\n".join(chunk).strip("\n")
        if not text.strip():
            continue
        cells.append(Cell(cell_id=f"py-{len(cells)}", cell_type=cell_type, source=text, output=""))

    if not cells:
        cells.append(Cell(cell_id="py-0", cell_type="code", source=source, output=""))
    return cells
