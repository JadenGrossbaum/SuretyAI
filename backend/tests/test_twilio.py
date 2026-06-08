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
