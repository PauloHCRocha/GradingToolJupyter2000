# Ganymede

> Repo name `GradingToolJupyter2000` is the legacy slug; the product brand is **Ganymede**.

Web app for grading Jupyter (`.ipynb`) and Python (`.py`) student submissions —
runs **entirely in the browser**. Student files never leave the teacher's machine.

🌐 **Live: https://paulohcrocha.github.io/GradingToolJupyter2000/**

## How it works

The whole pipeline (parsing notebooks, suggesting grades, plagiarism detection,
running student code) executes locally in the browser via
[Pyodide](https://pyodide.org/) — Python compiled to WebAssembly. The page is
served as static files from GitHub Pages; no upload happens at any point.

## Features

- Upload a solution file (`.ipynb` or `.py`) — questions detected automatically
- Upload a `.zip` of student submissions (Moodle-style folders)
- Side-by-side notebook viewer (solution vs. student) per question
- Per-question grading with quick-grade buttons and inline comments
- **Suggest grade** — multi-criteria heuristic comparing student code with the reference
- **Run code** — executes the student's Python directly in the browser sandbox
- **Plagiarism detection** — TF-IDF + AST + token similarity, suspicious-pair list, similarity matrix
- **Invisible-Unicode detection** — flags zero-width chars and other AI-paste tells
- **CSV export** of grades

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
