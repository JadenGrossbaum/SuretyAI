from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Lead
from app.schemas import LeadCreate
from app.services.lead_service import create_lead

SAMPLE_LEADS = (
    {
        'full_name': 'Jordan Principal',
        'company_name': 'Principal Builders LLC',
        'phone_number': '+15555550123',
        'email': 'jordan.principal@example.com',
        'contractor_type': 'general contractor',
        'interested_in_public_work': True,
        'bond_type_needed': 'performance and payment bond',
        'estimated_contract_amount': 250000.0,
        'has_prior_bonding': True,
        'current_bonding_capacity': 500000.0,
        'credit_score_range': '720-759',
        'bankruptcies': False,
        'foreclosures': False,
        'tax_liens': False,
        'judgments': False,
        'bond_claims': False,
        'spouse_financial_issues': False,
        'years_in_business': 6,
        'annual_revenue': 1250000.0,
        'working_capital': 150000.0,
        'has_financial_statements': True,
        'preferred_callback_time': 'weekday mornings',
        'notes': 'Sample lead interested in public work this quarter.',
    },
    {
        'full_name': 'Casey Contractor',
        'company_name': 'Casey Sitework Inc',
        'phone_number': '+15555550456',
        'email': 'casey.contractor@example.com',
        'contractor_type': 'sitework subcontractor',
        'interested_in_public_work': True,
        'bond_type_needed': 'bid bond',
        'estimated_contract_amount': 90000.0,
        'has_prior_bonding': False,
        'current_bonding_capacity': None,
        'credit_score_range': '620-679',
        'bankruptcies': False,
        'foreclosures': False,
        'tax_liens': True,
        'judgments': False,
        'bond_claims': False,
        'spouse_financial_issues': False,
        'years_in_business': 1,
        'annual_revenue': 325000.0,
        'working_capital': 15000.0,
        'has_financial_statements': False,
        'preferred_callback_time': 'weekday afternoons',
        'notes': 'Sample lead with review flags for local testing.',
    },
)


def seed_sample_leads(db: Session) -> list[Lead]:
    seeded: list[Lead] = []
    for payload in SAMPLE_LEADS:
        existing = db.scalar(select(Lead).where(Lead.email == payload['email']))
        if existing is not None:
            seeded.append(existing)
            continue
        seeded.append(create_lead(db, LeadCreate(**payload)))
    return seeded


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        leads = seed_sample_leads(db)
        for lead in leads:
            print(f'{lead.id}: {lead.full_name} <{lead.email}> - {lead.lead_status}')
    finally:
        db.close()


if __name__ == '__main__':
    main()
