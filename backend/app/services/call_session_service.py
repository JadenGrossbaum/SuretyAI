from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CallSession, TranscriptEntry


def create_or_update_call_session(
    db: Session,
    *,
    twilio_call_sid: str,
    from_number: Optional[str] = None,
    to_number: Optional[str] = None,
    call_status: Optional[str] = None,
    direction: Optional[str] = None,
) -> CallSession:
    call_session = db.scalar(
        select(CallSession).where(CallSession.twilio_call_sid == twilio_call_sid)
    )
    if call_session is None:
        call_session = CallSession(twilio_call_sid=twilio_call_sid)

    call_session.from_number = from_number or call_session.from_number
    call_session.to_number = to_number or call_session.to_number
    call_session.call_status = call_status or call_session.call_status
    call_session.direction = direction or call_session.direction

    db.add(call_session)
    db.commit()
    db.refresh(call_session)
    return call_session


def add_transcript_entry(
    db: Session,
    *,
    call_session: CallSession,
    speaker: str,
    text: str,
) -> TranscriptEntry:
    transcript = TranscriptEntry(call_session=call_session, speaker=speaker, text=text)
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript
