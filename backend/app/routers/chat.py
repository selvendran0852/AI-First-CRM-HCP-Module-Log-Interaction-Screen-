from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.graph import run_agent
from app.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])

# In-memory "what interaction is this session currently talking about" tracker.
# Good enough for a single-process demo; a production build would persist
# this per session_id in the DB (e.g. a column on a Session/Conversation table).
_SESSION_LAST_INTERACTION: dict[str, str] = {}


@router.post("", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Single entry point for the AI Assistant chat panel. The LangGraph
    agent classifies intent and dispatches to one of the 5 tools, or
    answers directly."""

    db.add(models.ChatMessage(session_id=payload.session_id, role="user", content=payload.message))
    db.commit()

    last_interaction_id = _SESSION_LAST_INTERACTION.get(payload.session_id)
    final_state = run_agent(db, payload.session_id, payload.message, interaction_id=last_interaction_id)

    if final_state.get("interaction_id"):
        _SESSION_LAST_INTERACTION[payload.session_id] = final_state["interaction_id"]

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
