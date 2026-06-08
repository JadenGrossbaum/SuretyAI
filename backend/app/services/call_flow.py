from dataclasses import dataclass
from enum import StrEnum


PROHIBITED_AGENT_TERMS = (
    'approved',
    'denied',
    'guaranteed',
    'qualified for sure',
    'bound',
    'final rate',
    'final premium',
)


class CallFlowStage(StrEnum):
    OPENING = 'opening'
    PERMISSION = 'permission'
    CALLER_IDENTITY = 'caller_identity'
    CONTRACTOR_PROFILE = 'contractor_profile'
    BOND_NEED = 'bond_need'
    PRIOR_BONDING = 'prior_bonding'
    CREDIT_AND_PUBLIC_RECORDS = 'credit_and_public_records'
    BUSINESS_FINANCIALS = 'business_financials'
    CALLBACK_AND_NOTES = 'callback_and_notes'
    CLOSING = 'closing'


@dataclass(frozen=True)
class IntakeQuestion:
    field_name: str
    prompt: str
    stage: CallFlowStage
    required: bool = False

OPENING_SCRIPT = (
    'Thank you for calling. This is SuretyAI, an intake assistant for a surety bonding agency. '
    'I can collect preliminary information so a human surety professional can review your request. '
    'I cannot make a bond decision, bind coverage, or quote final bond terms. '
    'Is it okay if I ask you a few questions to get started?'
)

NO_PERMISSION_CLOSING = (
    'No problem. A human surety professional can follow up with you directly. Thank you for calling.'
)

CLOSING_SCRIPT = (
    'Thank you. I have collected the preliminary information. '
    'A human surety professional will review it and follow up with you. '
    'This is not a bond decision, quote, or binding commitment.'
)

INTAKE_QUESTIONS: tuple[IntakeQuestion, ...] = (
    IntakeQuestion('full_name', 'What is your full name?', CallFlowStage.CALLER_IDENTITY, required=True),
    IntakeQuestion('company_name', 'What company are you calling from, if any?', CallFlowStage.CALLER_IDENTITY),
    IntakeQuestion('phone_number', 'What is the best phone number for a callback?', CallFlowStage.CALLER_IDENTITY, required=True),
    IntakeQuestion('email', 'What is the best email address for you?', CallFlowStage.CALLER_IDENTITY, required=True),
    IntakeQuestion('contractor_type', 'What type of contractor or business are you?', CallFlowStage.CONTRACTOR_PROFILE),
    IntakeQuestion('interested_in_public_work', 'Are you interested in public or government work?', CallFlowStage.CONTRACTOR_PROFILE),
    IntakeQuestion('bond_type_needed', 'What type of bond do you need?', CallFlowStage.BOND_NEED),
    IntakeQuestion('estimated_contract_amount', 'What is the estimated contract or bond amount?', CallFlowStage.BOND_NEED),
    IntakeQuestion('deadline', 'When do you need the bond or response by?', CallFlowStage.BOND_NEED),
    IntakeQuestion('has_prior_bonding', 'Have you had surety bonding before?', CallFlowStage.PRIOR_BONDING),
    IntakeQuestion('current_bonding_capacity', 'Do you know your current single job or aggregate bonding capacity?', CallFlowStage.PRIOR_BONDING),
    IntakeQuestion('credit_score_range', 'Which credit score range best describes your current credit?', CallFlowStage.CREDIT_AND_PUBLIC_RECORDS),
    IntakeQuestion('bankruptcies', 'Have there been any bankruptcies?', CallFlowStage.CREDIT_AND_PUBLIC_RECORDS),
    IntakeQuestion('foreclosures', 'Have there been any foreclosures?', CallFlowStage.CREDIT_AND_PUBLIC_RECORDS),
    IntakeQuestion('tax_liens', 'Are there any tax liens?', CallFlowStage.CREDIT_AND_PUBLIC_RECORDS),
    IntakeQuestion('judgments', 'Are there any judgments?', CallFlowStage.CREDIT_AND_PUBLIC_RECORDS),
    IntakeQuestion('bond_claims', 'Have there been any prior bond claims?', CallFlowStage.CREDIT_AND_PUBLIC_RECORDS),
    IntakeQuestion('spouse_financial_issues', 'Are there any spouse or partner financial issues relevant to review?', CallFlowStage.CREDIT_AND_PUBLIC_RECORDS),
    IntakeQuestion('years_in_business', 'How many years has the business been operating?', CallFlowStage.BUSINESS_FINANCIALS),
    IntakeQuestion('annual_revenue', 'What is your approximate annual revenue?', CallFlowStage.BUSINESS_FINANCIALS),
    IntakeQuestion('working_capital', 'What is your approximate working capital, if known?', CallFlowStage.BUSINESS_FINANCIALS),
    IntakeQuestion('has_financial_statements', 'Do you have current financial statements?', CallFlowStage.BUSINESS_FINANCIALS),
    IntakeQuestion('preferred_callback_time', 'What is the best time for a human surety professional to call you back?', CallFlowStage.CALLBACK_AND_NOTES),
    IntakeQuestion('notes', 'Is there anything else you want the surety professional to know before review?', CallFlowStage.CALLBACK_AND_NOTES),
)

FALLBACK_RESPONSES: dict[str, str] = {
    'decision_request': 'I cannot make that decision. I can only collect preliminary information. A human surety professional will review your request and follow up.',
    'qualification_request': 'I cannot make that assessment. A human surety professional needs to review the details before giving guidance.',
    'pricing_request': 'I cannot quote final pricing or premium. I can collect the information needed for a human surety professional to review.',
    'underwriting_advice': 'I cannot provide underwriting advice. I can collect intake details and pass them to a human surety professional.',
    'unclear_answer': 'I want to make sure I captured that correctly. Could you repeat or rephrase that?',
    'unknown_answer': 'That is okay. I will mark that as unknown and continue.',
    'caller_in_hurry': 'I understand. I will keep this brief and ask only the key intake questions.',
    'human_requested': 'Of course. I will note that you would like a human surety professional to follow up as soon as possible.',
}

def get_intake_questions() -> tuple[IntakeQuestion, ...]:
    return INTAKE_QUESTIONS


def get_questions_for_stage(stage: CallFlowStage) -> tuple[IntakeQuestion, ...]:
    return tuple(question for question in INTAKE_QUESTIONS if question.stage == stage)


def get_fallback_response(intent: str) -> str:
    return FALLBACK_RESPONSES.get(intent, FALLBACK_RESPONSES['unclear_answer'])


def script_contains_prohibited_terms(script: str) -> bool:
    normalized = script.casefold()
    return any(term in normalized for term in PROHIBITED_AGENT_TERMS)
