from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.tools import edit_interaction as edit_interaction_tool
from app.agent.tools import log_interaction as log_interaction_tool
from app.database import get_db

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("", response_model=schemas.InteractionOut)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """Structured-form path: rep filled in the Log Interaction form directly."""
    result = log_interaction_tool(db, payload.model_dump())
    interaction = db.query(models.Interaction).get(result["interaction_id"])
    return interaction


@router.get("", response_model=list[schemas.InteractionOut])
def list_interactions(hcp_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Interaction)
    if hcp_id:
        q = q.filter(models.Interaction.hcp_id == hcp_id)
    return q.order_by(models.Interaction.occurred_at.desc()).all()


@router.get("/{interaction_id}", response_model=schemas.InteractionOut)
def get_interaction(interaction_id: str, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).get(interaction_id)
    if not interaction:
        raise HTTPException(404, "Interaction not found")
    return interaction


@router.patch("/{interaction_id}", response_model=schemas.InteractionOut)
def update_interaction(
    interaction_id: str, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)
):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    result = edit_interaction_tool(db, {"interaction_id": interaction_id, "updates": updates})
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return db.query(models.Interaction).get(interaction_id)
