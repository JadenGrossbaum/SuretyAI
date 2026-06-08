from typing import Optional

from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import VoiceResponse

from app.config import Settings, get_settings
from app.database import get_db
from app.services.call_session_service import add_transcript_entry, create_or_update_call_session

router = APIRouter(prefix='/api/twilio', tags=['twilio'])

MVP_GREETING = (
    'Thank you for calling SuretyAI. This MVP can collect preliminary surety bond intake '
    'information for review by a human surety professional. It cannot make a bond decision, '
    'bind coverage, or quote final terms. Voice agent connection is coming in the next phase.'
)


def build_voice_twiml(settings: Settings) -> str:
    response = VoiceResponse()
    response.say(MVP_GREETING, voice='alice')
    response.pause(length=1)
    response.say(
        'A human surety professional will review any information collected and follow up.',
        voice='alice',
    )
    response.hangup()
    return str(response)


@router.post('/voice')
def inbound_voice(
    CallSid: str = Form(...),
    From: Optional[str] = Form(default=None),
    To: Optional[str] = Form(default=None),
    CallStatus: Optional[str] = Form(default=None),
    Direction: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    call_session = create_or_update_call_session(
        db,
        twilio_call_sid=CallSid,
        from_number=From,
        to_number=To,
        call_status=CallStatus or 'in-progress',
        direction=Direction,
    )
    add_transcript_entry(db, call_session=call_session, speaker='system', text=MVP_GREETING)
    return Response(content=build_voice_twiml(settings), media_type='application/xml')


@router.post('/status')
def call_status(
    CallSid: str = Form(...),
    CallStatus: Optional[str] = Form(default=None),
    From: Optional[str] = Form(default=None),
    To: Optional[str] = Form(default=None),
    Direction: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    call_session = create_or_update_call_session(
        db,
        twilio_call_sid=CallSid,
        from_number=From,
        to_number=To,
        call_status=CallStatus,
        direction=Direction,
    )
    return {
        'call_session_id': call_session.id,
        'twilio_call_sid': call_session.twilio_call_sid,
        'call_status': call_session.call_status,
    }
