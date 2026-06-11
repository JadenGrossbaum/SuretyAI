import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.config import Settings, get_settings
from app.database import get_db
from app.services.call_session_service import add_transcript_entry, create_or_update_call_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/twilio', tags=['twilio'])

INTRO_MESSAGE = (
    'Thank you for calling SuretyAI. I can collect preliminary surety bond intake '
    'information for review by a human surety professional. I cannot make a bond decision, '
    'bind coverage, or quote final terms.'
)
FINAL_MESSAGE = (
    'Thank you. Your preliminary information has been recorded. '
    'A human surety professional will review it and follow up with you.'
)
NO_CONSENT_MESSAGE = (
    'No problem. A human surety professional can follow up separately. Thank you for calling.'
)
NO_INPUT_MESSAGE = 'I did not catch that. Please answer after the tone.'


@dataclass(frozen=True)
class GatherStep:
    key: str
    prompt: str

INTAKE_STEPS: tuple[GatherStep, ...] = (
    GatherStep('consent', 'Is it okay if I ask you a few preliminary intake questions? Please say yes or no.'),
    GatherStep('full_name', 'What is your full name?'),
    GatherStep('company_name', 'What company are you calling from, if any?'),
    GatherStep('phone_number_confirmation', 'Is the number you are calling from the best callback number? If not, please say the best callback number.'),
    GatherStep('email', 'What is your email address?'),
    GatherStep('contractor_type', 'What type of contractor or business are you?'),
    GatherStep('bond_type_needed', 'What type of bond do you need?'),
    GatherStep('estimated_contract_amount', 'What is the estimated contract or bond amount?'),
    GatherStep('interested_in_public_work', 'Are you interested in public or government work?'),
    GatherStep('credit_score_range', 'What credit score range best describes your current credit?'),
    GatherStep('bankruptcies', 'Have there been any bankruptcies?'),
    GatherStep('foreclosures', 'Have there been any foreclosures?'),
    GatherStep('tax_liens', 'Are there any tax liens?'),
    GatherStep('judgments', 'Are there any judgments?'),
    GatherStep('bond_claims', 'Have there been any prior bond claims?'),
    GatherStep('preferred_callback_time', 'What is the best time for a human surety professional to call you back?'),
)


def build_voice_twiml(settings: Settings) -> str:
    response = VoiceResponse()
    response.say(INTRO_MESSAGE, voice='alice')
    append_gather(response, settings, step=0)
    response.redirect(build_gather_url(settings, step=0), method='POST')
    return str(response)


def build_gather_twiml(settings: Settings, step: int, repeated: bool = False) -> str:
    response = VoiceResponse()
    if repeated:
        response.say(NO_INPUT_MESSAGE, voice='alice')
    if step >= len(INTAKE_STEPS):
        response.say(FINAL_MESSAGE, voice='alice')
        response.hangup()
        return str(response)
    append_gather(response, settings, step=step)
    response.redirect(build_gather_url(settings, step=step), method='POST')
    return str(response)

def build_no_consent_twiml() -> str:
    response = VoiceResponse()
    response.say(NO_CONSENT_MESSAGE, voice='alice')
    response.hangup()
    return str(response)


def append_gather(response: VoiceResponse, settings: Settings, step: int) -> None:
    gather = Gather(
        input='speech dtmf',
        action=build_gather_url(settings, step=step),
        method='POST',
        timeout=6,
        speech_timeout='auto',
    )
    gather.say(INTAKE_STEPS[step].prompt, voice='alice')
    response.append(gather)


def build_gather_url(settings: Settings, step: int) -> str:
    base_url = settings.public_base_url.rstrip('/')
    return f'{base_url}/api/twilio/gather?step={step}'


def build_public_webhook_url(request: Request, settings: Settings) -> str:
    base_url = settings.public_base_url.rstrip('/')
    url = f'{base_url}{request.url.path}'
    if request.url.query:
        url = f'{url}?{request.url.query}'
    return url


def twilio_debug_payload(settings: Settings) -> dict[str, object]:
    public_base_url = settings.public_base_url.rstrip('/')
    voice_webhook_url = f'{public_base_url}/api/twilio/voice'
    status_webhook_url = f'{public_base_url}/api/twilio/status'
    missing = [
        key
        for key, value in {
            'TWILIO_ACCOUNT_SID': settings.twilio_account_sid,
            'TWILIO_AUTH_TOKEN': settings.twilio_auth_token,
            'TWILIO_PHONE_NUMBER': settings.twilio_phone_number,
            'PUBLIC_BASE_URL': settings.public_base_url,
        }.items()
        if not value
    ]
    return {
        'twilio_account_sid_present': bool(settings.twilio_account_sid),
        'twilio_auth_token_present': bool(settings.twilio_auth_token),
        'twilio_phone_number_present': bool(settings.twilio_phone_number),
        'public_base_url_present': bool(settings.public_base_url),
        'public_base_url': settings.public_base_url,
        'voice_webhook_url': voice_webhook_url,
        'status_webhook_url': status_webhook_url,
        'ready_for_live_testing': not missing,
        'missing': missing,
    }

async def verify_twilio_request(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.twilio_auth_token:
        if settings.app_env == 'development':
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Twilio webhook validation is not configured',
        )

    signature = request.headers.get('X-Twilio-Signature', '')
    form = await request.form()
    webhook_url = build_public_webhook_url(request, settings)
    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(webhook_url, dict(form), signature):
        logger.warning('Rejected Twilio webhook with invalid signature path=%s', request.url.path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid Twilio signature',
        )


@router.get('/debug')
def twilio_debug(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return twilio_debug_payload(settings)


@router.post('/voice', dependencies=[Depends(verify_twilio_request)])
def inbound_voice(
    CallSid: str = Form(...),
    From: Optional[str] = Form(default=None),
    To: Optional[str] = Form(default=None),
    CallStatus: Optional[str] = Form(default=None),
    Direction: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    logger.info('Twilio voice webhook received call_sid=%s from=%s to=%s status=%s', CallSid, From, To, CallStatus or 'in-progress')
    call_session = create_or_update_call_session(
        db,
        twilio_call_sid=CallSid,
        from_number=From,
        to_number=To,
        call_status=CallStatus or 'in-progress',
        direction=Direction,
    )
    add_transcript_entry(db, call_session=call_session, speaker='system', text=INTRO_MESSAGE)
    logger.info('Twilio voice webhook started gather flow call_session_id=%s call_sid=%s', call_session.id, CallSid)
    return Response(content=build_voice_twiml(settings), media_type='application/xml')

@router.post('/gather', dependencies=[Depends(verify_twilio_request)])
def gather_step(
    step: int = Query(..., ge=0),
    CallSid: str = Form(...),
    SpeechResult: Optional[str] = Form(default=None),
    Digits: Optional[str] = Form(default=None),
    From: Optional[str] = Form(default=None),
    To: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    call_session = create_or_update_call_session(
        db,
        twilio_call_sid=CallSid,
        from_number=From,
        to_number=To,
        call_status='in-progress',
    )
    caller_response = normalize_gather_response(SpeechResult, Digits)
    if not caller_response:
        return Response(content=build_gather_twiml(settings, step=step, repeated=True), media_type='application/xml')

    if step < len(INTAKE_STEPS):
        field_name = INTAKE_STEPS[step].key
        add_transcript_entry(db, call_session=call_session, speaker=f'caller:{field_name}', text=caller_response)
        logger.info('Twilio gather stored call_sid=%s step=%s field=%s', CallSid, step, field_name)
        if field_name == 'consent' and is_negative_response(caller_response):
            add_transcript_entry(db, call_session=call_session, speaker='system', text=NO_CONSENT_MESSAGE)
            return Response(content=build_no_consent_twiml(), media_type='application/xml')

    next_step = step + 1
    if next_step >= len(INTAKE_STEPS):
        add_transcript_entry(db, call_session=call_session, speaker='system', text=FINAL_MESSAGE)
    return Response(content=build_gather_twiml(settings, step=next_step), media_type='application/xml')


def normalize_gather_response(speech_result: Optional[str], digits: Optional[str]) -> str:
    if speech_result and speech_result.strip():
        return speech_result.strip()
    if digits and digits.strip():
        return digits.strip()
    return ''


def is_negative_response(value: str) -> bool:
    normalized = value.casefold().strip()
    return normalized in {'no', 'nope', 'nah', 'not now', 'do not', 'do not continue'}



@router.post('/status', dependencies=[Depends(verify_twilio_request)])
def call_status(
    CallSid: str = Form(...),
    CallStatus: Optional[str] = Form(default=None),
    From: Optional[str] = Form(default=None),
    To: Optional[str] = Form(default=None),
    Direction: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    logger.info('Twilio status webhook received call_sid=%s status=%s', CallSid, CallStatus)
    call_session = create_or_update_call_session(
        db,
        twilio_call_sid=CallSid,
        from_number=From,
        to_number=To,
        call_status=CallStatus,
        direction=Direction,
    )
    logger.info('Twilio status webhook updated call_session_id=%s call_sid=%s', call_session.id, CallSid)
    return {
        'call_session_id': call_session.id,
        'twilio_call_sid': call_session.twilio_call_sid,
        'call_status': call_session.call_status,
    }

