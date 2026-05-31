"""AI PR Reviewer — FastAPI REST API server with modular routers."""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import auth, repos, review, settings, eval as eval_router

app = FastAPI(title="AI PR Reviewer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:5174", "http://127.0.0.1:5174",
                   "http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Mount modular routers
app.include_router(auth.router)
app.include_router(repos.router)
app.include_router(review.router)
app.include_router(settings.router)
app.include_router(eval_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
