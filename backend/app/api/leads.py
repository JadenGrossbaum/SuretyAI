from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import LeadCreate, LeadRead
from app.services import create_lead as create_lead_record
from app.services import get_lead as get_lead_record
from app.services import list_leads as list_lead_records

router = APIRouter(prefix='/api/leads', tags=['leads'])


@router.post('', response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    return create_lead_record(db, payload)


@router.get('', response_model=list[LeadRead])
def list_leads(db: Session = Depends(get_db)):
    return list_lead_records(db)


@router.get('/{lead_id}', response_model=LeadRead)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = get_lead_record(db, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Lead not found')
    return lead
