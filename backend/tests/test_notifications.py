from unittest.mock import Mock

from app.config import Settings
from app.models import CallSession, Lead, TranscriptEntry
from app.scoring import evaluate_lead
from app.services.notification_service import (
    DISCLAIMER,
    build_lead_summary_email,
    build_phone_intake_summary_email,
    notify_lead_created,
    notify_phone_intake_completed,
    render_lead_summary,
)


def make_lead(**overrides):
    defaults = {
        'id': 42,
        'full_name': 'Jordan Principal',
        'company_name': 'Principal Builders LLC',
        'phone_number': '+15555550123',
        'email': 'jordan@example.com',
        'contractor_type': 'general contractor',
        'interested_in_public_work': True,
        'bond_type_needed': 'performance bond',
        'estimated_contract_amount': 250000.0,
        'has_prior_bonding': True,
        'current_bonding_capacity': 500000.0,
        'credit_score_range': '580-619',
        'bankruptcies': True,
        'foreclosures': False,
        'tax_liens': True,
        'judgments': False,
        'bond_claims': True,
        'spouse_financial_issues': False,
        'years_in_business': 1,
        'annual_revenue': 1250000.0,
        'working_capital': -1000.0,
        'has_financial_statements': False,
        'preferred_callback_time': 'weekday mornings',
        'notes': 'Please call back soon.',
        'lead_score': 0,
        'lead_status': 'Higher Risk / Human Review Required',
    }
    defaults.update(overrides)
    return Lead(**defaults)


def make_settings():
    return Settings(
        smtp_host='smtp.example.com',
        smtp_port=2525,
        smtp_username='alerts@example.com',
        smtp_password='secret',
        internal_notification_email='team@example.com',
    )


def test_render_lead_summary_includes_score_status_risk_contact_and_notes():
    lead = make_lead()
    score_result = evaluate_lead(lead)

    body = render_lead_summary(lead, score_result)

    assert 'Lead score: 0' in body
    assert 'Review category: Higher Risk / Human Review Required' in body
    assert 'Recent bankruptcy' in body
    assert 'Tax liens' in body
    assert 'Jordan Principal' in body
    assert '+15555550123' in body
    assert 'Please call back soon.' in body
    assert 'human surety review only' in body


def test_notify_lead_created_skips_when_smtp_not_configured():
    result = notify_lead_created(make_lead(), settings=Settings())

    assert result.sent is False
    assert result.reason == 'smtp_not_configured'


def test_notify_lead_created_sends_email_with_mocked_smtp(monkeypatch):
    smtp_context = Mock()
    smtp_client = Mock()
    smtp_context.__enter__ = Mock(return_value=smtp_client)
    smtp_context.__exit__ = Mock(return_value=None)
    smtp_factory = Mock(return_value=smtp_context)
    monkeypatch.setattr('app.services.notification_service.SMTP', smtp_factory)

    result = notify_lead_created(make_lead(), settings=make_settings())

    assert result.sent is True
    smtp_factory.assert_called_once_with('smtp.example.com', 2525, timeout=10)
    smtp_client.starttls.assert_called_once()
    smtp_client.login.assert_called_once_with('alerts@example.com', 'secret')
    sent_message = smtp_client.send_message.call_args.args[0]
    assert sent_message['To'] == 'team@example.com'
    assert sent_message['From'] == 'alerts@example.com'
    assert 'SuretyAI lead: Jordan Principal' in sent_message['Subject']
    assert 'Key risk flags:' in sent_message.get_content()


def test_build_lead_summary_email_sets_headers():
    message = build_lead_summary_email(make_lead(), None, make_settings())

    assert message['To'] == 'team@example.com'
    assert message['From'] == 'alerts@example.com'
    assert 'Principal Builders LLC' in message['Subject']


def make_call_session_with_transcripts(db_session):
    call_session = CallSession(
        twilio_call_sid='CA_PHONE_EMAIL',
        from_number='+15555550123',
        to_number='+15555550999',
        call_status='in-progress',
        direction='inbound',
    )
    db_session.add(call_session)
    db_session.commit()
    db_session.refresh(call_session)

    responses = [
        ('caller:full_name', 'Alex Caller'),
        ('caller:company_name', 'Caller Contracting LLC'),
        ('caller:phone_number_confirmation', '+15555550123'),
        ('caller:email', 'alex@example.com'),
        ('caller:bond_type_needed', 'bid bond'),
        ('caller:estimated_contract_amount', '350000'),
        ('caller:interested_in_public_work', 'yes'),
        ('caller:credit_score_range', '580-619'),
        ('caller:bankruptcies', 'yes'),
        ('caller:foreclosures', 'no'),
        ('caller:tax_liens', 'yes'),
        ('caller:judgments', 'no'),
        ('caller:bond_claims', 'yes'),
        ('caller:preferred_callback_time', 'Friday morning'),
    ]
    for speaker, text in responses:
        db_session.add(TranscriptEntry(call_session=call_session, speaker=speaker, text=text))
    db_session.commit()
    return call_session


def test_build_phone_intake_summary_email_includes_required_fields(db_session):
    call_session = make_call_session_with_transcripts(db_session)

    message = build_phone_intake_summary_email(
        call_session,
        call_session.transcripts,
        make_settings(),
    )
    body = message.get_content()

    assert message['To'] == 'team@example.com'
    assert message['From'] == 'alerts@example.com'
    assert 'SuretyAI phone intake: Alex Caller - Caller Contracting LLC' in message['Subject']
    assert 'Caller name: Alex Caller' in body
    assert 'Company: Caller Contracting LLC' in body
    assert 'Phone: +15555550123' in body
    assert 'Email: alex@example.com' in body
    assert 'Bond type: bid bond' in body
    assert 'Estimated contract amount: 350000' in body
    assert 'Credit score range: 580-619' in body
    assert 'Lead score:' in body
    assert 'Lead status: Higher Risk / Human Review Required' in body
    assert '- Recent bankruptcy' in body
    assert '- Tax liens' in body
    assert '- Prior bond claims' in body
    assert '- full name: Alex Caller' in body
    assert '- preferred callback time: Friday morning' in body
    assert 'Recommended next step:' in body
    assert DISCLAIMER in body


def test_notify_phone_intake_completed_sends_email_with_mocked_smtp(monkeypatch, db_session):
    call_session = make_call_session_with_transcripts(db_session)
    smtp_context = Mock()
    smtp_client = Mock()
    smtp_context.__enter__ = Mock(return_value=smtp_client)
    smtp_context.__exit__ = Mock(return_value=None)
    smtp_factory = Mock(return_value=smtp_context)
    monkeypatch.setattr('app.services.notification_service.SMTP', smtp_factory)

    result = notify_phone_intake_completed(db_session, call_session=call_session, settings=make_settings())

    assert result.sent is True
    smtp_factory.assert_called_once_with('smtp.example.com', 2525, timeout=10)
    sent_message = smtp_client.send_message.call_args.args[0]
    body = sent_message.get_content()
    assert sent_message['To'] == 'team@example.com'
    assert 'SuretyAI phone intake: Alex Caller' in sent_message['Subject']
    assert 'Transcript summary:' in body
    assert DISCLAIMER in body


def test_notify_phone_intake_completed_skips_when_smtp_not_configured(db_session):
    call_session = make_call_session_with_transcripts(db_session)

    result = notify_phone_intake_completed(db_session, call_session=call_session, settings=Settings())

    assert result.sent is False
    assert result.reason == 'smtp_not_configured'
