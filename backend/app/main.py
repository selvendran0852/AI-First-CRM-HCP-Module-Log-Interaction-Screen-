import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import chat, hcps, interactions

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI-First CRM — HCP Module API",
    description="Log Interaction Screen backend: structured form endpoints "
    "plus a LangGraph + Groq conversational agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interactions.router)
app.include_router(hcps.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup():
    # For local dev / demo convenience only — in production use Alembic migrations.
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
