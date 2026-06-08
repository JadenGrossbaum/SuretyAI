from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lead
from app.schemas import LeadCreate
from app.scoring import evaluate_lead
from app.services.notification_service import notify_lead_created


def create_lead(db: Session, payload: LeadCreate) -> Lead:
    lead = Lead(**payload.model_dump())
    score_result = evaluate_lead(lead)
    lead.lead_score = score_result.score
    lead.lead_status = score_result.category.value
    db.add(lead)
    db.commit()
    db.refresh(lead)
    notify_lead_created(lead, score_result)
    return lead


def list_leads(db: Session) -> list[Lead]:
    return list(db.scalars(select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc())))


def get_lead(db: Session, lead_id: int) -> Lead | None:
    return db.get(Lead, lead_id)
