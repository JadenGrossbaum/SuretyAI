from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lead
from app.schemas import LeadCreate


def create_lead(db: Session, payload: LeadCreate) -> Lead:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def list_leads(db: Session) -> list[Lead]:
    return list(db.scalars(select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc())))


def get_lead(db: Session, lead_id: int) -> Lead | None:
    return db.get(Lead, lead_id)
