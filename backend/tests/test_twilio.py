from unittest.mock import Mock

from twilio.request_validator import RequestValidator

from app.api.twilio import FINAL_MESSAGE, INTAKE_STEPS, NO_CONSENT_MESSAGE
from app.config import Settings, get_settings
from app.models import CallSession, TranscriptEntry


def assert_no_decision_language(text: str):
    forbidden = ['approved', 'denied', 'guaranteed', 'officially qualified']
    lowered = text.lower()
    for phrase in forbidden:
        assert phrase not in lowered


def test_twilio_voice_starts_gather_flow_and_logs_call(client, db_session):
    response = client.post(
        '/api/twilio/voice',
        data={
            'CallSid': 'CA123',
            'From': '+15555550123',
            'To': '+15555550999',
            'CallStatus': 'ringing',
            'Direction': 'inbound',
        },
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/xml')
    assert '<Response>' in response.text
    assert '<Gather' in response.text
    assert 'Thank you for calling SuretyAI' in response.text
    assert 'human surety professional' in response.text
    assert 'Is it okay if I ask you a few preliminary intake questions?' in response.text
    assert '/api/twilio/gather?step=0' in response.text
    assert_no_decision_language(response.text)

    call_session = db_session.query(CallSession).filter_by(twilio_call_sid='CA123').one()
    assert call_session.from_number == '+15555550123'
    assert call_session.to_number == '+15555550999'
    assert call_session.call_status == 'ringing'
    assert call_session.direction == 'inbound'

    transcript = db_session.query(TranscriptEntry).filter_by(call_session_id=call_session.id).one()
    assert transcript.speaker == 'system'
    assert 'preliminary surety bond intake' in transcript.text


def test_twilio_gather_stores_response_and_asks_next_question(client, db_session):
    client.post('/api/twilio/voice', data={'CallSid': 'CA_FLOW', 'From': '+1', 'To': '+2'})

    response = client.post(
        '/api/twilio/gather?step=0',
        data={'CallSid': 'CA_FLOW', 'SpeechResult': 'yes', 'From': '+1', 'To': '+2'},
    )

    assert response.status_code == 200
    assert 'What is your full name?' in response.text
    assert '/api/twilio/gather?step=1' in response.text

    call_session = db_session.query(CallSession).filter_by(twilio_call_sid='CA_FLOW').one()
    transcript = (
        db_session.query(TranscriptEntry)
        .filter_by(call_session_id=call_session.id, speaker='caller:consent')
        .one()
    )
    assert transcript.text == 'yes'


def test_twilio_gather_reprompts_when_no_input(client, db_session):
    response = client.post('/api/twilio/gather?step=1', data={'CallSid': 'CA_EMPTY'})

    assert response.status_code == 200
    assert 'I did not catch that' in response.text
    assert 'What is your full name?' in response.text
    assert '/api/twilio/gather?step=1' in response.text

    call_session = db_session.query(CallSession).filter_by(twilio_call_sid='CA_EMPTY').one()
    assert db_session.query(TranscriptEntry).filter_by(call_session_id=call_session.id).count() == 0


def test_twilio_gather_no_consent_hangs_up(client, db_session):
    response = client.post(
        '/api/twilio/gather?step=0',
        data={'CallSid': 'CA_NO_CONSENT', 'SpeechResult': 'no'},
    )

    assert response.status_code == 200
    assert NO_CONSENT_MESSAGE in response.text
    assert '<Hangup' in response.text
    assert_no_decision_language(response.text)

    call_session = db_session.query(CallSession).filter_by(twilio_call_sid='CA_NO_CONSENT').one()
    speakers = [
        row.speaker
        for row in db_session.query(TranscriptEntry)
        .filter_by(call_session_id=call_session.id)
        .order_by(TranscriptEntry.id)
    ]
    assert speakers == ['caller:consent', 'system']


def test_twilio_gather_completes_flow_after_last_step(client, db_session, monkeypatch):
    notification_mock = Mock()
    notification_mock.return_value.sent = True
    notification_mock.return_value.reason = 'sent'
    monkeypatch.setattr('app.api.twilio.notify_phone_intake_completed', notification_mock)
    last_step = len(INTAKE_STEPS) - 1

    response = client.post(
        f'/api/twilio/gather?step={last_step}',
        data={'CallSid': 'CA_DONE', 'SpeechResult': 'tomorrow morning'},
    )

    assert response.status_code == 200
    assert FINAL_MESSAGE in response.text
    assert '<Hangup' in response.text
    assert_no_decision_language(response.text)

    call_session = db_session.query(CallSession).filter_by(twilio_call_sid='CA_DONE').one()
    speakers = [
        row.speaker
        for row in db_session.query(TranscriptEntry)
        .filter_by(call_session_id=call_session.id)
        .order_by(TranscriptEntry.id)
    ]
    assert speakers == ['caller:preferred_callback_time', 'system']
    notification_mock.assert_called_once()
    assert notification_mock.call_args.kwargs['call_session'].twilio_call_sid == 'CA_DONE'


def test_twilio_status_updates_existing_call_session(client, db_session):
    client.post('/api/twilio/voice', data={'CallSid': 'CA456', 'From': '+1', 'To': '+2'})

    response = client.post(
        '/api/twilio/status',
        data={'CallSid': 'CA456', 'CallStatus': 'completed', 'From': '+1', 'To': '+2'},
    )

    assert response.status_code == 200
    data = response.json()
    assert data['twilio_call_sid'] == 'CA456'
    assert data['call_status'] == 'completed'

    call_session = db_session.query(CallSession).filter_by(twilio_call_sid='CA456').one()
    assert call_session.call_status == 'completed'


def test_twilio_status_creates_call_session_if_status_arrives_first(client, db_session):
    response = client.post('/api/twilio/status', data={'CallSid': 'CA789', 'CallStatus': 'busy'})

    assert response.status_code == 200
    assert response.json()['call_status'] == 'busy'
    assert db_session.query(CallSession).filter_by(twilio_call_sid='CA789').count() == 1


def signed_headers(settings, path, data):
    signature = RequestValidator(settings.twilio_auth_token).compute_signature(
        '{}{}'.format(settings.public_base_url.rstrip('/'), path),
        data,
    )
    return {'X-Twilio-Signature': signature}


def test_twilio_voice_accepts_valid_signature_when_auth_token_configured(client, db_session):
    settings = Settings(
        app_env='production',
        twilio_auth_token='secret',
        public_base_url='http://testserver',
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    data = {
        'CallSid': 'CA_SIGNED',
        'From': '+15555550123',
        'To': '+15555550999',
        'CallStatus': 'ringing',
    }

    response = client.post(
        '/api/twilio/voice',
        data=data,
        headers=signed_headers(settings, '/api/twilio/voice', data),
    )

    assert response.status_code == 200
    assert db_session.query(CallSession).filter_by(twilio_call_sid='CA_SIGNED').count() == 1


def test_twilio_gather_accepts_valid_signature_when_auth_token_configured(client, db_session):
    settings = Settings(
        app_env='production',
        twilio_auth_token='secret',
        public_base_url='http://testserver',
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    data = {'CallSid': 'CA_GATHER_SIGNED', 'SpeechResult': 'yes'}

    response = client.post(
        '/api/twilio/gather?step=0',
        data=data,
        headers=signed_headers(settings, '/api/twilio/gather?step=0', data),
    )

    assert response.status_code == 200
    assert db_session.query(CallSession).filter_by(twilio_call_sid='CA_GATHER_SIGNED').count() == 1


def test_twilio_voice_rejects_invalid_signature_when_auth_token_configured(client, db_session):
    settings = Settings(
        app_env='production',
        twilio_auth_token='secret',
        public_base_url='http://testserver',
    )
    client.app.dependency_overrides[get_settings] = lambda: settings

    response = client.post(
        '/api/twilio/voice',
        data={'CallSid': 'CA_BAD_SIG'},
        headers={'X-Twilio-Signature': 'bad-signature'},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Invalid Twilio signature'
    assert db_session.query(CallSession).filter_by(twilio_call_sid='CA_BAD_SIG').count() == 0


def test_twilio_status_rejects_production_without_auth_token(client, db_session):
    settings = Settings(app_env='production', twilio_auth_token=None)
    client.app.dependency_overrides[get_settings] = lambda: settings

    response = client.post('/api/twilio/status', data={'CallSid': 'CA_NO_TOKEN'})

    assert response.status_code == 403
    assert response.json()['detail'] == 'Twilio webhook validation is not configured'
    assert db_session.query(CallSession).filter_by(twilio_call_sid='CA_NO_TOKEN').count() == 0


def test_twilio_debug_reports_missing_config_without_secrets(client):
    settings = Settings(
        twilio_account_sid=None,
        twilio_auth_token=None,
        twilio_phone_number=None,
        public_base_url='http://localhost:8000',
    )
    client.app.dependency_overrides[get_settings] = lambda: settings

    response = client.get('/api/twilio/debug')

    assert response.status_code == 200
    data = response.json()
    assert data['twilio_account_sid_present'] is False
    assert data['twilio_auth_token_present'] is False
    assert data['twilio_phone_number_present'] is False
    assert data['public_base_url_present'] is True
    assert data['ready_for_live_testing'] is False
    assert 'TWILIO_AUTH_TOKEN' in data['missing']
    assert 'auth_token' not in data


def test_twilio_debug_reports_ready_config_without_exposing_secret(client):
    settings = Settings(
        twilio_account_sid='AC123',
        twilio_auth_token='super-secret-token',
        twilio_phone_number='+15555550123',
        public_base_url='https://example.ngrok-free.app',
    )
    client.app.dependency_overrides[get_settings] = lambda: settings

    response = client.get('/api/twilio/debug')

    assert response.status_code == 200
    data = response.json()
    assert data['ready_for_live_testing'] is True
    assert data['missing'] == []
    assert data['voice_webhook_url'] == 'https://example.ngrok-free.app/api/twilio/voice'
    assert data['status_webhook_url'] == 'https://example.ngrok-free.app/api/twilio/status'
    assert 'super-secret-token' not in response.text
