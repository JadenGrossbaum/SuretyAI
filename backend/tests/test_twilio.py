from twilio.request_validator import RequestValidator

from app.config import Settings, get_settings
from app.models import CallSession, TranscriptEntry


def test_twilio_voice_returns_twiml_and_logs_call(client, db_session):
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
    assert 'Thank you for calling SuretyAI' in response.text
    assert 'human surety professional' in response.text
    assert 'Voice agent connection is coming in the next phase' in response.text

    call_session = db_session.query(CallSession).filter_by(twilio_call_sid='CA123').one()
    assert call_session.from_number == '+15555550123'
    assert call_session.to_number == '+15555550999'
    assert call_session.call_status == 'ringing'
    assert call_session.direction == 'inbound'

    transcript = db_session.query(TranscriptEntry).filter_by(call_session_id=call_session.id).one()
    assert transcript.speaker == 'system'
    assert 'preliminary surety bond intake' in transcript.text


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
