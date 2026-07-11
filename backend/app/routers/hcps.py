from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/hcps", tags=["hcps"])


@router.get("", response_model=list[schemas.HCPOut])
def search_hcps(q: str = "", db: Session = Depends(get_db)):
    query = db.query(models.HCP)
    if q:
        query = query.filter(models.HCP.name.ilike(f"%{q}%"))
    return query.limit(10).all()


@router.post("", response_model=schemas.HCPOut)
def create_hcp(payload: schemas.HCPCreate, db: Session = Depends(get_db)):
    hcp = models.HCP(**payload.model_dump())
    db.add(hcp)
    db.commit()
    db.refresh(hcp)
    return hcp
