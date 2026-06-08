from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lead(Base):
    __tablename__ = 'leads'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contractor_type: Mapped[str | None] = mapped_column(String(100))
    interested_in_public_work: Mapped[bool | None] = mapped_column(Boolean)
    bond_type_needed: Mapped[str | None] = mapped_column(String(100))
    estimated_contract_amount: Mapped[float | None] = mapped_column(Float)
    has_prior_bonding: Mapped[bool | None] = mapped_column(Boolean)
    current_bonding_capacity: Mapped[float | None] = mapped_column(Float)
    credit_score_range: Mapped[str | None] = mapped_column(String(50))
    bankruptcies: Mapped[bool | None] = mapped_column(Boolean)
    foreclosures: Mapped[bool | None] = mapped_column(Boolean)
    tax_liens: Mapped[bool | None] = mapped_column(Boolean)
    judgments: Mapped[bool | None] = mapped_column(Boolean)
    bond_claims: Mapped[bool | None] = mapped_column(Boolean)
    spouse_financial_issues: Mapped[bool | None] = mapped_column(Boolean)
    years_in_business: Mapped[int | None] = mapped_column(Integer)
    annual_revenue: Mapped[float | None] = mapped_column(Float)
    working_capital: Mapped[float | None] = mapped_column(Float)
    has_financial_statements: Mapped[bool | None] = mapped_column(Boolean)
    preferred_callback_time: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    lead_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_status: Mapped[str] = mapped_column(String(50), default='new', nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
