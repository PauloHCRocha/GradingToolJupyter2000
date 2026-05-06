from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import grades, solution, submissions

app = FastAPI(title="GradingToolJupyter2000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solution.router)
app.include_router(submissions.router)
app.include_router(grades.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
