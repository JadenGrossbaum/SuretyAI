from app.services.call_flow import (
    CLOSING_SCRIPT,
    FALLBACK_RESPONSES,
    INTAKE_QUESTIONS,
    OPENING_SCRIPT,
    CallFlowStage,
    get_fallback_response,
    get_questions_for_stage,
    script_contains_prohibited_terms,
)


def test_call_flow_starts_with_permission_and_preliminary_screening():
    assert 'preliminary information' in OPENING_SCRIPT
    assert 'Is it okay if I ask you a few questions' in OPENING_SCRIPT
    assert 'human surety professional' in OPENING_SCRIPT


def test_intake_questions_cover_lead_fields_one_at_a_time():
    field_names = [question.field_name for question in INTAKE_QUESTIONS]

    assert field_names[:4] == ['full_name', 'company_name', 'phone_number', 'email']
    assert 'bond_type_needed' in field_names
    assert 'working_capital' in field_names
    assert 'preferred_callback_time' in field_names
    assert all('?' in question.prompt for question in INTAKE_QUESTIONS)


def test_questions_can_be_grouped_by_stage():
    identity_questions = get_questions_for_stage(CallFlowStage.CALLER_IDENTITY)

    assert [question.field_name for question in identity_questions] == [
        'full_name',
        'company_name',
        'phone_number',
        'email',
    ]


def test_fallback_responses_redirect_to_human_review():
    assert 'human surety professional' in get_fallback_response('decision_request')
    assert 'underwriting advice' in get_fallback_response('underwriting_advice')
    assert get_fallback_response('unknown-intent') == FALLBACK_RESPONSES['unclear_answer']


def test_spoken_scripts_avoid_prohibited_decision_language():
    spoken_scripts = [OPENING_SCRIPT, CLOSING_SCRIPT, *FALLBACK_RESPONSES.values()]

    assert all(not script_contains_prohibited_terms(script) for script in spoken_scripts)
