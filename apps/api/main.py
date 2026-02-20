from fastapi import FastAPI
from apps.api.routers import applications, auth, docs, jobs, llm, profile, reports
from core.config import settings
from core.logging import setup_logging
from core.security import ensure_data_dirs
from db.base import Base
from db.session import engine

setup_logging()
ensure_data_dirs(settings.data_dir)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MJAC API")
app.include_router(profile.router)
app.include_router(auth.router)
app.include_router(llm.router)
app.include_router(jobs.router)
app.include_router(docs.router)
app.include_router(applications.router)
app.include_router(reports.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
