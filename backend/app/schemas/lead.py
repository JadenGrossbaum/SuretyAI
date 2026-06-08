from datetime import datetime
from re import fullmatch

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    phone_number: str = Field(min_length=7, max_length=50)
    email: str = Field(max_length=255)
    contractor_type: str | None = Field(default=None, max_length=100)
    interested_in_public_work: bool | None = None
    bond_type_needed: str | None = Field(default=None, max_length=100)
    estimated_contract_amount: float | None = Field(default=None, ge=0)
    has_prior_bonding: bool | None = None
    current_bonding_capacity: float | None = Field(default=None, ge=0)
    credit_score_range: str | None = Field(default=None, max_length=50)
    bankruptcies: bool | None = None
    foreclosures: bool | None = None
    tax_liens: bool | None = None
    judgments: bool | None = None
    bond_claims: bool | None = None
    spouse_financial_issues: bool | None = None
    years_in_business: int | None = Field(default=None, ge=0)
    annual_revenue: float | None = Field(default=None, ge=0)
    working_capital: float | None = None
    has_financial_statements: bool | None = None
    preferred_callback_time: str | None = Field(default=None, max_length=100)
    notes: str | None = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', normalized):
            raise ValueError('email must be a valid email address')
        return normalized

    @field_validator('full_name', 'phone_number')
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError('field cannot be blank')
        return stripped


class LeadCreate(LeadBase):
    pass


class LeadRead(LeadBase):
    id: int
    lead_score: int
    lead_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
