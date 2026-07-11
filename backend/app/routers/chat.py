from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.graph import run_agent
from app.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Single entry point for the AI Assistant chat panel. The LangGraph
    agent classifies intent and dispatches to one of the 5 tools, or
    answers directly."""

    db.add(models.ChatMessage(session_id=payload.session_id, role="user", content=payload.message))
    db.commit()

    final_state = run_agent(db, payload.session_id, payload.message)

    db.add(
        models.ChatMessage(
            session_id=payload.session_id,
            role="assistant",
            content=final_state.get("reply", ""),
            tool_name=",".join(final_state.get("tool_calls", [])) or None,
        )
    )
    db.commit()

    interaction = None
    if final_state.get("interaction_id"):
        interaction = db.query(models.Interaction).get(final_state["interaction_id"])

    return schemas.ChatResponse(
        session_id=payload.session_id,
        reply=final_state.get("reply", ""),
        tool_calls=final_state.get("tool_calls", []),
        tool_result=final_state.get("tool_result"),
        interaction=interaction,
    )
