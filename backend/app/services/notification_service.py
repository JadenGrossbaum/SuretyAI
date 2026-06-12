from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import CallSession, Lead, TranscriptEntry
from app.scoring import LeadScoreResult, evaluate_lead

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'templates' / 'lead_summary_email.txt'
PHONE_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'templates' / 'phone_intake_summary_email.txt'
DISCLAIMER = 'This is a preliminary intake summary only. It is not an approval, denial, quote, or underwriting decision.'


@dataclass(frozen=True)
class NotificationResult:
    sent: bool
    reason: str


@dataclass(frozen=True)
class PhoneIntakeScoringInput:
    interested_in_public_work: bool | None = None
    bankruptcies: bool | None = None
    foreclosures: bool | None = None
    tax_liens: bool | None = None
    judgments: bool | None = None
    bond_claims: bool | None = None
    credit_score_range: str | None = None
    has_prior_bonding: bool | None = None
    years_in_business: int | None = None
    has_financial_statements: bool | None = None
    working_capital: float | None = None


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


def notify_phone_intake_completed(
    db: Session,
    *,
    call_session: CallSession,
    settings: Optional[Settings] = None,
) -> NotificationResult:
    settings = settings or get_settings()
    if not settings.smtp_host or not settings.internal_notification_email:
        return NotificationResult(sent=False, reason='smtp_not_configured')

    transcript_entries = list_phone_transcript_entries(db, call_session.id)
    message = build_phone_intake_summary_email(call_session, transcript_entries, settings)
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


def build_phone_intake_summary_email(
    call_session: CallSession,
    transcript_entries: list[TranscriptEntry],
    settings: Settings,
) -> EmailMessage:
    fields = extract_phone_intake_fields(transcript_entries)
    score_result = evaluate_phone_intake(fields)
    message = EmailMessage()
    caller_name = value_or_unknown(fields.get('full_name'))
    company_name = value_or_unknown(fields.get('company_name'))
    message['Subject'] = f'SuretyAI phone intake: {caller_name} - {company_name}'
    message['From'] = settings.smtp_username or 'suretyai@localhost'
    message['To'] = settings.internal_notification_email or ''
    message.set_content(render_phone_intake_summary(call_session, transcript_entries, fields, score_result))
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


def render_phone_intake_summary(
    call_session: CallSession,
    transcript_entries: list[TranscriptEntry],
    fields: dict[str, str],
    score_result: LeadScoreResult,
) -> str:
    template = PHONE_TEMPLATE_PATH.read_text(encoding='utf-8')
    return template.format(
        call_session_id=value_or_unknown(call_session.id),
        twilio_call_sid=value_or_unknown(call_session.twilio_call_sid),
        caller_name=value_or_unknown(fields.get('full_name')),
        company=value_or_unknown(fields.get('company_name')),
        phone=value_or_unknown(fields.get('phone_number_confirmation') or call_session.from_number),
        email=value_or_unknown(fields.get('email')),
        bond_type=value_or_unknown(fields.get('bond_type_needed')),
        estimated_contract_amount=value_or_unknown(fields.get('estimated_contract_amount')),
        credit_score_range=value_or_unknown(fields.get('credit_score_range')),
        risk_flags=format_risk_flags(score_result.negative_factors),
        lead_score=score_result.score,
        lead_status=score_result.category,
        transcript_summary=format_transcript_summary(transcript_entries),
        recommended_next_step=recommend_next_step(score_result),
        disclaimer=DISCLAIMER,
    )


def list_phone_transcript_entries(db: Session, call_session_id: int) -> list[TranscriptEntry]:
    return list(
        db.scalars(
            select(TranscriptEntry)
            .where(TranscriptEntry.call_session_id == call_session_id)
            .order_by(TranscriptEntry.id)
        )
    )


def extract_phone_intake_fields(transcript_entries: list[TranscriptEntry]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for entry in transcript_entries:
        if not entry.speaker.startswith('caller:'):
            continue
        key = entry.speaker.removeprefix('caller:')
        fields.setdefault(key, entry.text)
    return fields


def evaluate_phone_intake(fields: dict[str, str]) -> LeadScoreResult:
    scoring_input = PhoneIntakeScoringInput(
        interested_in_public_work=parse_yes_no(fields.get('interested_in_public_work')),
        bankruptcies=parse_yes_no(fields.get('bankruptcies')),
        foreclosures=parse_yes_no(fields.get('foreclosures')),
        tax_liens=parse_yes_no(fields.get('tax_liens')),
        judgments=parse_yes_no(fields.get('judgments')),
        bond_claims=parse_yes_no(fields.get('bond_claims')),
        credit_score_range=fields.get('credit_score_range'),
    )
    return evaluate_lead(scoring_input)


def parse_yes_no(value: Optional[str]) -> bool | None:
    if not value:
        return None
    normalized = value.casefold().strip()
    negative_phrases = ('no', 'nope', 'none', 'not that i know', 'not aware')
    positive_phrases = ('yes', 'yeah', 'yep', 'there are', 'i have', 'we have')
    if any(normalized.startswith(phrase) for phrase in negative_phrases):
        return False
    if any(normalized.startswith(phrase) for phrase in positive_phrases):
        return True
    return None


def format_transcript_summary(transcript_entries: list[TranscriptEntry]) -> str:
    caller_entries = [entry for entry in transcript_entries if entry.speaker.startswith('caller:')]
    if not caller_entries:
        return '- No caller responses were captured.'
    lines = []
    for entry in caller_entries:
        label = entry.speaker.removeprefix('caller:').replace('_', ' ')
        lines.append('- {}: {}'.format(label, entry.text))
    return '\n'.join(lines)


def recommend_next_step(score_result: LeadScoreResult) -> str:
    if score_result.negative_factors:
        return 'Human surety professional should review the flagged items and call the prospect to clarify details.'
    return 'Human surety professional should verify the intake details and request any supporting documents needed for review.'


def format_risk_flags(risk_flags: tuple[str, ...]) -> str:
    if not risk_flags:
        return '- No key risk flags identified during preliminary scoring'
    return '\n'.join('- {}'.format(flag) for flag in risk_flags)


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
