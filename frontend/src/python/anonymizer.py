"""Strip personal data from submissions before they leave the browser.

Everything that is sent to an external grading service goes through
`anonymize_submission` first. The mapping back to the real student never
leaves the browser: the payload carries no name, number, filename or
folder — only the scrubbed code.

What is replaced:
  - the student's own name and number, and every other student's name
    (group mates), case- and accent-insensitive, inside comments, strings
    and markdown;
  - the student's number anywhere in the code when it is long enough not to
    collide with ordinary constants;
  - e-mail addresses anywhere;
  - number-like IDs ("a12345", "up201912345") inside comments and markdown;
  - the value part of identity lines ("# Nome: ...", "Número = ...",
    "Author - ...") in comments, strings and markdown.

Code tokens (identifiers, operators) are left alone so the program still
reads the same — a student called "Max" does not turn `max()` into
`<NAME>()`.
"""

from __future__ import annotations

import io
import re
import tokenize
import unicodedata

from notebook_parser import Cell

NAME = "<NAME>"
STUDENT_ID = "<STUDENT_ID>"
EMAIL = "<EMAIL>"
ID = "<ID>"
REDACTED = "<REDACTED>"

_PARTICLES = {"de", "da", "do", "das", "dos", "del", "della", "di", "du", "van", "von", "der", "le", "la", "e", "y"}
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_ID_RE = re.compile(r"(?<![\w<])[A-Za-z]{0,4}\d{5,}(?![\w>])")
_IDENTITY_RE = re.compile(
    r"(?P<key>(?<!\w)(?:nome|name|autor(?:a|es)?|authors?|alun[oa]s?|students?|estudantes?|"
    r"n[úu]mero|n\.?\s?[º°]|nr\.?|num\.?|e-?mail|turma|grupo|group)(?!\w)"
    r"(?:\s*[:=]\s*|\s+[-–]\s+))"
    r"(?P<value>[^\n]*)",
    re.IGNORECASE,
)
_STRING_RE = re.compile(r"^([rRbBuUfFtT]*)(\"\"\"|\'\'\'|\"|\')(.*?)(\2)?$", re.DOTALL)
_ACCENTS = {
    "a": "aáàâãäå", "e": "eéèêë", "i": "iíìîï", "o": "oóòôõö", "u": "uúùûü",
    "c": "cç", "n": "nñ", "y": "yý",
}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def _fuzzy(term: str) -> str:
    """Regex for `term` that matches any accent/case variant of it."""
    out = []
    for ch in _strip_accents(term).lower():
        if ch in _ACCENTS:
            out.append(f"[{_ACCENTS[ch]}]")
        elif ch.isspace() or ch in "_-.":
            out.append(r"[\s_.\-]+")
        else:
            out.append(re.escape(ch))
    return "".join(out)


def name_tokens(name: str) -> list[str]:
    parts = re.split(r"[\s_\-.]+", name or "")
    return [p for p in parts if len(p) >= 3 and p.lower() not in _PARTICLES and not p.isdigit()]


class Scrubber:
    """Replacement rules for one student. Build once per submission."""

    def __init__(self, name: str = "", number: str = "", roster_names: list[str] | None = None):
        tokens: set[str] = set()
        full_names: set[str] = set()
        for n in [name, *(roster_names or [])]:
            if not n:
                continue
            toks = name_tokens(n)
            tokens.update(toks)
            if len(toks) >= 2:
                full_names.add(n)
        # Longest first so "Maria" doesn't eat half of "Mariana".
        ordered = sorted(tokens, key=len, reverse=True)
        self._names = (
            re.compile(r"(?<!\w)(?:" + "|".join(_fuzzy(t) for t in ordered) + r")(?!\w)", re.IGNORECASE)
            if ordered else None
        )
        self._full_names = (
            re.compile(
                r"(?<!\w)(?:" + "|".join(_fuzzy(n) for n in sorted(full_names, key=len, reverse=True)) + r")(?!\w)",
                re.IGNORECASE,
            )
            if full_names else None
        )
        number = (number or "").strip()
        self._number = re.compile(r"(?<!\w)" + re.escape(number) + r"(?!\w)", re.IGNORECASE) if number else None
        # Only long, digit-heavy numbers are safe to replace inside code too.
        self._number_everywhere = sum(c.isdigit() for c in number) >= 5
        self.count = 0

    def _sub(self, pattern, repl, text):
        if pattern is None:
            return text
        new, n = pattern.subn(repl, text)
        self.count += n
        return new

    def text(self, s: str, kind: str = "text") -> str:
        """Free text: comments, string contents, markdown, outputs. Inside
        string literals bare numbers are left alone — they are usually
        program data, and the student's own number is still caught."""
        s = self._sub(_EMAIL_RE, EMAIL, s)

        def identity(m):
            value = m.group("value")
            # Keep format placeholders ("Nome: {nome}", "Name: %s") and empty prompts.
            if not value.strip() or value.lstrip()[:1] in "{%" or value.strip() in (REDACTED, NAME, STUDENT_ID):
                return m.group(0)
            self.count += 1
            return m.group("key") + REDACTED

        s = _IDENTITY_RE.sub(identity, s)
        s = self._sub(self._number, STUDENT_ID, s)
        if kind != "string":
            s = self._sub(_ID_RE, ID, s)
        s = self._sub(self._full_names, NAME, s)
        s = self._sub(self._names, NAME, s)
        return s

    def code_wide(self, s: str) -> str:
        """Rules safe to apply to the whole program, code tokens included."""
        s = self._sub(_EMAIL_RE, EMAIL, s)
        s = self._sub(self._full_names, NAME, s)
        if self._number_everywhere:
            s = self._sub(self._number, STUDENT_ID, s)
        return s


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _text_spans_tokenize(source: str):
    """(start, end, kind) for comments and string literals, via tokenize."""
    offsets = _line_offsets(source)
    kinds = {tokenize.COMMENT: "comment", tokenize.STRING: "string"}
    fstring_middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    if fstring_middle is not None:
        kinds[fstring_middle] = "string"
    tstring_middle = getattr(tokenize, "TSTRING_MIDDLE", None)
    if tstring_middle is not None:
        kinds[tstring_middle] = "string"
    spans = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        kind = kinds.get(tok.type)
        if kind is None:
            continue
        start = offsets[tok.start[0] - 1] + tok.start[1]
        end = offsets[tok.end[0] - 1] + tok.end[1]
        spans.append((start, end, kind))
    return spans


def _text_spans_scan(source: str):
    """Tolerant fallback for code that doesn't tokenize (syntax errors are
    common in student work): a small scanner for quotes and '#'."""
    spans = []
    i, n = 0, len(source)
    while i < n:
        c = source[i]
        if c == "#":
            j = source.find("\n", i)
            j = n if j == -1 else j
            spans.append((i, j, "comment"))
            i = j
        elif c in "\"'":
            triple = source[i:i + 3] in ('"""', "'''")
            quote = source[i:i + 3] if triple else c
            j = i + len(quote)
            while j < n:
                if source[j] == "\\":
                    j += 2
                    continue
                if source.startswith(quote, j):
                    j += len(quote)
                    break
                if not triple and source[j] == "\n":
                    break
                j += 1
            spans.append((i, min(j, n), "string"))
            i = j
        else:
            i += 1
    return spans


def scrub_python(source: str, scrubber: Scrubber, strip_comments: bool = False) -> str:
    try:
        spans = _text_spans_tokenize(source)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        spans = _text_spans_scan(source)

    from notebook_parser import QUESTION_HEADER

    out = []
    pos = 0
    for start, end, kind in spans:
        out.append(source[pos:start])
        chunk = source[start:end]
        line_start = source.rfind("\n", 0, start) + 1
        is_header = kind == "comment" and line_start == start and QUESTION_HEADER.match(chunk)
        if kind == "comment" and strip_comments and not is_header:
            chunk = ""
        elif kind == "comment":
            chunk = scrubber.text(chunk)
        else:
            # Scrub only what is between the quotes so the literal stays valid.
            m = _STRING_RE.match(chunk)
            if m and m.group(2):
                chunk = m.group(1) + m.group(2) + scrubber.text(m.group(3), "string") + (m.group(4) or "")
            else:  # f-string middle part: content only, no quotes
                chunk = scrubber.text(chunk, "string")
        out.append(chunk)
        pos = end
    out.append(source[pos:])
    return scrubber.code_wide("".join(out))


def anonymize_notebook(
    cells: list[Cell],
    scrubber: Scrubber,
    strip_comments: bool = False,
    include_outputs: bool = False,
) -> str:
    """Render a notebook as plain text for the grader, already scrubbed: a
    sequence of "# %% [markdown]" / "# %%" blocks, so the grader sees the
    same cell structure the teacher sees."""
    parts = []
    for i, cell in enumerate(cells):
        if cell.cell_type == "markdown":
            text = scrubber.text(cell.source)
            if strip_comments:
                # Markdown in a notebook is the student's prose answer;
                # keep only question headers so the grader can still
                # find each answer.
                text = "\n".join(l for l in text.splitlines() if re.search(r"\bQ(?:uestion)?\s*\d", l, re.I))
            if text.strip():
                parts.append("# %% [markdown]\n" + "\n".join("# " + l for l in text.splitlines()))
            continue
        block = f"# %% [cell {i + 1}]\n" + scrub_python(cell.source, scrubber, strip_comments)
        if include_outputs and cell.output:
            out = scrubber.text(cell.output[:2000])
            block += "\n# Output:\n" + "\n".join("# " + l for l in out.splitlines())
        parts.append(block)
    return "\n\n".join(parts)
