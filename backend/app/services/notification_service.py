from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from typing import Optional

from app.config import Settings, get_settings
from app.models import Lead
from app.scoring import LeadScoreResult, evaluate_lead

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'templates' / 'lead_summary_email.txt'


@dataclass(frozen=True)
class NotificationResult:
    sent: bool
    reason: str


def notify_lead_created(
    lead: Lead,
    score_result: Optional[LeadScoreResult] = None,
    settings: Optional[Settings] = None,
) -> NotificationResult:
    settings = settings or get_settings()
    if not settings.smtp_host or not settings.internal_notification_email:
        return NotificationResult(sent=False, reason='smtp_not_configured')

    message = build_lead_summary_email(lead, score_result, settings)
    send_email(message, settings)
    return NotificationResult(sent=True, reason='sent')


def build_lead_summary_email(
    lead: Lead,
    score_result: Optional[LeadScoreResult],
    settings: Settings,
) -> EmailMessage:
    score_result = score_result or evaluate_lead(lead)
    message = EmailMessage()
    message['Subject'] = build_subject(lead)
    message['From'] = settings.smtp_username or 'suretyai@localhost'
    message['To'] = settings.internal_notification_email or ''
    message.set_content(render_lead_summary(lead, score_result))
    return message


def build_subject(lead: Lead) -> str:
    company = lead.company_name or 'No company provided'
    return f'SuretyAI lead: {lead.full_name} - {company}'


def render_lead_summary(lead: Lead, score_result: LeadScoreResult) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    return template.format(
        lead_id=value_or_unknown(lead.id),
        full_name=value_or_unknown(lead.full_name),
        company_name=value_or_unknown(lead.company_name),
        phone_number=value_or_unknown(lead.phone_number),
        email=value_or_unknown(lead.email),
        bond_type_needed=value_or_unknown(lead.bond_type_needed),
        contractor_type=value_or_unknown(lead.contractor_type),
        interested_in_public_work=value_or_unknown(lead.interested_in_public_work),
        estimated_contract_amount=value_or_unknown(lead.estimated_contract_amount),
        has_prior_bonding=value_or_unknown(lead.has_prior_bonding),
        current_bonding_capacity=value_or_unknown(lead.current_bonding_capacity),
        lead_score=value_or_unknown(lead.lead_score),
        lead_status=value_or_unknown(lead.lead_status),
        risk_flags=format_risk_flags(score_result.negative_factors),
        credit_score_range=value_or_unknown(lead.credit_score_range),
        years_in_business=value_or_unknown(lead.years_in_business),
        annual_revenue=value_or_unknown(lead.annual_revenue),
        working_capital=value_or_unknown(lead.working_capital),
        has_financial_statements=value_or_unknown(lead.has_financial_statements),
        preferred_callback_time=value_or_unknown(lead.preferred_callback_time),
        notes=value_or_unknown(lead.notes),
    )


def format_risk_flags(risk_flags: tuple[str, ...]) -> str:
    if not risk_flags:
        return '- No key risk flags identified during preliminary scoring'
    return '\n'.join(f'- {flag}' for flag in risk_flags)


def value_or_unknown(value: object) -> object:
    if value is None or value == '':
        return 'Unknown'
    return value


def send_email(message: EmailMessage, settings: Settings) -> None:
    with SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_username and settings.smtp_password:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
