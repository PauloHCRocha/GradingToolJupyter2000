# GradingToolJupyter2000

Web app for grading Jupyter (`.ipynb`) and Python (`.py`) student submissions.

Successor to the single-file Flask grader. Vue 3 frontend + FastAPI backend.

## Features (planned)

- Upload a solution file (`.ipynb` or `.py`) and detect questions automatically
- Compare student submissions against the solution
- Suggest grades and export to CSV
- AST-based plagiarism detection with PDF reports

## Stack

- **Frontend:** Vue 3, Vite, TypeScript, Pinia, Vue Router
- **Backend:** FastAPI, Python 3.11+

## Development

### Backend

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Frontend

```sh
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` to the backend on port 8000.
