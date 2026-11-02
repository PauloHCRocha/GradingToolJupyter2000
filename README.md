# Granymede

> Repo name `GradingToolJupyter2000` is the legacy slug; the product brand is **Granymede**.

Web app for grading Jupyter (`.ipynb`) and Python (`.py`) student submissions —
runs **entirely in the browser**. Student files never leave the teacher's machine,
except as anonymized code when the teacher opts into Claude auto-grading.

🌐 **Live: https://paulohcrocha.github.io/GradingToolJupyter2000/**

## How it works

The whole pipeline (parsing notebooks, suggesting grades, plagiarism detection,
running student code) executes locally in the browser via
[Pyodide](https://pyodide.org/) — Python compiled to WebAssembly. The page is
served as static files from GitHub Pages; no upload happens at any point.

## Features

- Upload a solution file (`.ipynb` or `.py`) — questions detected automatically
- Upload a `.zip` of student submissions (Moodle-style folders)
- Side-by-side viewer (solution vs. student) per question, or the whole file
- Per-question grading with quick-grade buttons and inline comments
- **Suggest grade** — multi-criteria heuristic comparing student code with the reference
- **Run code** — runs the teacher's working copy of the submission (and the solution,
  for comparison) in a separate Pyodide worker with a time limit; edits never touch
  the original submission. The output appears in an interactive console: when the
  program calls `input()`, the teacher types the answer inline (pasting several lines
  answers several calls), and can replay the same answers on the solution to compare
  outputs. Each answer re-runs the program from the start with every answer so far
  (the browser can't pause Python mid-run without cross-origin isolation, which
  GitHub Pages can't enable); `random` is seeded per console so replays match.
- **Auto-grade with Claude** (optional) — see below
- **Plagiarism detection** — TF-IDF + AST + token similarity, suspicious-pair list, similarity matrix
- **Invisible-Unicode detection** — flags zero-width chars and other AI-paste tells
- **CSV export** of grades (UTF-8 with BOM, so Excel shows accented names correctly)

### `.py` files

A column-0 comment that starts with a question marker — `# Q1 (2 points)`,
`## Question 2`, `# --- Q1.2 ---` — or a docstring that starts with one
(`"""Q3: ..."""`) opens a new question. `# %%` / `# %% [markdown]` cell markers
(VS Code, Jupytext) are honoured too. Commented-out code such as `# q1 = 5` is
not a header.

Key/value blocks work as well, in a column-0 docstring or comment block:

```python
"""
ID: 1
Label: Uma associação está a realizar uma campanha de angariação de fundos. …
Grade: 5 points
"""
```

Recognised keys (case- and accent-insensitive): `ID` / `Question` / `Pergunta` /
`Questão` / `Exercício`; `Label` / `Enunciado` / `Statement` / `Descrição`;
`Grade` / `Points` / `Pontos` / `Cotação` / `Valores`. `ID: 2.1` becomes `Q2-1`;
non-numeric IDs are numbered in order. The same blocks are recognised in notebook
markdown cells.

A `.py` file with no markers at all is graded as a single question, and so is a
single-question assignment: every student's whole file is their answer, header
or not. When a student's file lacks a header in a multi-question assignment, the
grading view shows the whole file for that question.

### Auto-grading with Claude

Opt-in, from **Grading → Auto-grade**, with the teacher's own Anthropic API key
(kept in `sessionStorage`, or `localStorage` if "remember" is ticked). Requests go
straight from the browser to the Claude API — there is still no backend.

1. Claude proposes a **solution** and a **rubric** (criteria with points) for each
   question, starting from the teacher's reference file. Both are editable; each
   rubric must add up to the question's points.
2. Every submission is **anonymized locally** (`frontend/src/python/anonymizer.py`)
   before it is sent: the names and numbers of every student in the zip, e-mails,
   ID-like numbers and identity lines (`# Nome: …`, `Número = …`) in comments,
   strings and markdown become placeholders like `<NAME>`. Filenames, folder names
   and student numbers are never part of a request; submissions are sent one per
   request, in random order, with no identifier. The teacher can preview the exact
   text sent for any student, and optionally strip all comments.
3. Claude grades each submission criterion by criterion. Points are clamped to each
   criterion's maximum and totalled locally. Text in a submission aimed at the
   grader ("give me full marks") is ignored and reported as an integrity flag.
4. Every proposed grade waits for the teacher's review — accept, edit or reject,
   individually next to the code or in bulk. Only accepted grades reach the CSV.

## Stack

- **Frontend:** Vue 3 + Vite + TypeScript + Pinia + Vue Router
- **Runtime:** Pyodide (Python 3 in the browser, loaded from CDN)
- **Backend:** none in production. The `backend/` directory holds an older
  FastAPI version of the same logic; it is not used by the deployed app.

## Local development

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — first load downloads Pyodide (~10s), subsequent
loads are instant from browser cache.

## Build & deploy

```sh
cd frontend
npm run build   # outputs to frontend/dist
```

The `.github/workflows/deploy.yml` workflow builds the site and pushes it to
GitHub Pages on every push to `main`. Make sure **Settings → Pages → Source**
is set to **GitHub Actions**.
