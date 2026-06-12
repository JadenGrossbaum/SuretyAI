# SuretyAI AI Voice Architecture

This document designs the next phase for connecting SuretyAI to an AI voice agent. It is intentionally non-implementation guidance. The current Twilio Gather flow should remain the stable fallback for live phone testing and production resilience.

## Goals

- Connect inbound Twilio phone calls to an AI voice intake agent.
- Preserve the existing safety posture: SuretyAI collects preliminary screening information only.
- Extract structured intake fields and save them to the existing Lead model.
- Keep a deterministic fallback path if AI audio, transcription, or field extraction fails.
- Ensure every completed intake is reviewed by a human surety professional.

## Recommended Architecture

Recommended high-level components:

1. Twilio Voice webhook receives the inbound call.
2. SuretyAI creates or updates a CallSession record.
3. Twilio streams call audio to SuretyAI using Twilio Media Streams over WebSocket.
4. SuretyAI opens a server-side session to the OpenAI Realtime API.
5. SuretyAI bridges audio between Twilio and the Realtime session.
6. The AI agent conducts the intake using the approved surety prompt and tool schema.
7. SuretyAI stores transcripts and extracted field updates throughout the call.
8. When intake completes, SuretyAI creates or updates a Lead record.
9. SuretyAI scores the lead using the existing preliminary review logic.
10. SuretyAI sends the internal summary email to the surety team.

Suggested backend additions:

- backend/app/api/realtime.py for WebSocket media stream handling.
- backend/app/services/realtime_bridge.py for Twilio to OpenAI audio bridging.
- backend/app/services/field_extraction.py for validated field updates.
- backend/app/services/lead_from_call.py for converting call-session data into Lead records.
- backend/app/prompts/surety_realtime_agent.md for the voice-agent prompt.
- Optional backend/app/models/call.py additions for AI session status, failure reason, and linked lead ID.

## Audio Flow

The preferred audio path is:

1. Caller dials the Twilio phone number.
2. Twilio sends POST /api/twilio/voice to SuretyAI.
3. SuretyAI returns TwiML that starts a Twilio Media Stream to a public WebSocket endpoint, for example wss://{PUBLIC_BASE_URL}/api/realtime/twilio-media.
4. Twilio sends inbound caller audio frames to the SuretyAI WebSocket.
5. SuretyAI forwards audio frames to the OpenAI Realtime API session.
6. The OpenAI Realtime API returns audio deltas for the AI assistant response.
7. SuretyAI forwards assistant audio back to Twilio.
8. Twilio plays the AI assistant audio to the caller.
9. SuretyAI stores transcript events and structured field updates as the call progresses.

The bridge service should own protocol translation. Twilio and OpenAI use different event shapes, audio encodings, timestamps, and connection lifecycle events. Keep those details out of route handlers.

## Field Extraction And Lead Persistence

The AI agent should collect the same fields as the stable Gather flow, plus any fields already supported by the Lead model:

- full_name
- company_name
- phone_number
- email
- contractor_type
- interested_in_public_work
- bond_type_needed
- estimated_contract_amount
- has_prior_bonding
- current_bonding_capacity
- credit_score_range
- bankruptcies
- foreclosures
- tax_liens
- judgments
- bond_claims
- spouse_financial_issues
- years_in_business
- annual_revenue
- working_capital
- has_financial_statements
- preferred_callback_time
- notes

Recommended persistence pattern:

1. During the call, store every user and assistant turn as TranscriptEntry rows linked to CallSession.
2. Store partial extracted fields in a structured in-memory state object during the WebSocket session.
3. After each confirmed answer, validate and normalize the field value with Pydantic or a small service-specific schema.
4. Persist confirmed fields either as call metadata or a draft Lead row.
5. At call completion, create or update a Lead record with normalized values.
6. Run existing preliminary scoring logic and save lead_score and lead_status.
7. Link the CallSession to the Lead record if the model is extended with lead_id.

Recommended extraction approach:

- Use a Realtime tool/function call such as record_intake_field with a strict JSON schema.
- Accept only known field names.
- Validate booleans, numeric amounts, email, phone, and credit-score range before saving to Lead.
- Treat unclear answers as notes or ask a clarification question.
- Do not let the AI directly write to the database. The application should validate tool calls and perform persistence.

## Stable Fallback

The current Twilio Gather flow remains the stable fallback.

Fallback should trigger when:

- OpenAI Realtime session creation fails.
- Twilio Media Stream WebSocket fails to connect.
- Audio bridge errors repeatedly.
- The AI does not respond within a configured timeout.
- Field extraction emits invalid structured data repeatedly.
- The caller asks for a non-AI or human-only path.
- Safety guardrails detect underwriting advice or prohibited decision language.

Fallback behavior:

1. Log the AI failure reason on CallSession.
2. Return or redirect to the existing Gather intake flow when possible.
3. If mid-call fallback is not technically possible, play a safe message and ask the caller to continue through keypad or speech prompts.
4. If neither AI nor Gather can continue, end with a human-review message and send the partial transcript to the internal team.
5. Never lose already captured transcript or field data.

Suggested fallback message:

> I am having trouble with the voice assistant. I can continue with a simpler intake flow, or a human surety professional can follow up. This is preliminary information only and will be reviewed by a human surety professional.

## Compliance Guardrails

The AI voice agent must follow these rules:

- Never say the bond is approved.
- Never say the bond is denied.
- Never guarantee bonding, pricing, terms, capacity, or eligibility.
- Never state that the caller is officially qualified.
- Never give underwriting advice or legal, tax, or financial advice.
- Always explain that the intake is preliminary only.
- Always say a human surety professional will review the information.
- Ask one question at a time.
- Ask permission before collecting information.
- Use plain-language clarifying questions when answers are unclear.
- Do not request highly sensitive information that is not needed for preliminary screening.
- Do not collect full Social Security numbers, bank account numbers, payment card numbers, or passwords.
- Treat spouse financial issues as optional and sensitive.
- Escalate to human review if the caller asks for a binding decision, exact terms, or underwriting judgment.

The required disclaimer for call endings and summary emails should remain:

This is a preliminary intake summary only. It is not an approval, denial, quote, or underwriting decision.

## Human Handoff Rules

A human surety professional should review every completed intake.

Immediate handoff or callback should be recommended when:

- The caller asks for approval, denial, eligibility, final terms, or a quote.
- The caller reports a bankruptcy, foreclosure, tax lien, judgment, or prior bond claim.
- The caller has a low or unclear credit score range.
- The caller is very new in business.
- The caller cannot provide financial documents.
- The caller sounds distressed, confused, or unwilling to continue with automation.
- The AI detects repeated uncertainty or conflicting answers.
- The call has a technical failure or partial transcript only.

The AI may say:

- A human surety professional will review this information.
- The team will follow up about next steps.
- The information has been recorded for review.

The AI must not say:

- You are approved.
- You are denied.
- You qualify.
- This is guaranteed.
- Here is your final quote.
- Underwriting will accept this.

## Estimated Environment Variables

Expected additions for the AI voice phase:

~~~text
OPENAI_API_KEY=
OPENAI_REALTIME_MODEL=
OPENAI_REALTIME_VOICE=
OPENAI_REALTIME_TIMEOUT_SECONDS=30
OPENAI_REALTIME_MAX_SESSION_SECONDS=900
AI_VOICE_ENABLED=false
AI_VOICE_FALLBACK_TO_GATHER=true
AI_VOICE_LOG_AUDIO_EVENTS=false
AI_VOICE_STORE_TRANSCRIPTS=true
AI_VOICE_PUBLIC_WS_URL=wss://your-domain.example.com/api/realtime/twilio-media
TWILIO_MEDIA_STREAM_PATH=/api/realtime/twilio-media
TWILIO_WEBHOOK_TIMEOUT_SECONDS=10
INTERNAL_NOTIFICATION_EMAIL=
PUBLIC_BASE_URL=https://your-public-domain.example.com
~~~

Notes:

- OPENAI_API_KEY must never be exposed to Twilio or the browser.
- PUBLIC_BASE_URL is used for HTTPS Twilio webhooks.
- AI_VOICE_PUBLIC_WS_URL must be reachable by Twilio as a secure WebSocket URL.
- Feature flags should allow the team to turn AI voice off without redeploying.

## Risks

Technical risks:

- Realtime audio latency may make the phone experience feel slow.
- Twilio and OpenAI audio formats may require careful transcoding or buffering.
- WebSocket disconnects can happen mid-call.
- Duplicate Twilio callbacks may cause duplicate transcript or email records.
- Partial transcripts may produce incomplete Lead records.
- Long calls can increase API costs.
- Local ngrok testing may behave differently than a deployed HTTPS/WSS environment.

Product and compliance risks:

- The AI could accidentally use decision language if prompts or tools are too permissive.
- Callers may interpret scoring categories as underwriting outcomes.
- Sensitive financial disclosures require careful data minimization.
- Transcript storage may create privacy and retention obligations.
- The system must avoid implying that automation replaces licensed or experienced surety review.

Operational risks:

- SMTP failure could prevent internal notification after a completed call.
- Missing environment variables could route live calls into a broken AI path.
- Human staff need a clear dashboard or inbox process for reviewing phone leads.
- Support staff need a way to identify calls that fell back from AI to Gather.

## Open Questions

- Should the AI create a Lead only at call completion, or maintain a draft Lead during the call?
- Should CallSession include a lead_id foreign key now, or should that wait until the first AI implementation?
- What retention policy should apply to transcripts and any audio-derived metadata?
- Should raw audio ever be stored, or should the system store transcripts only?
- What exact Realtime model and voice should be used for live testing?
- Should callers be told the assistant is AI before consent?
- Should the system support Spanish or other languages in the first AI phase?
- What timeout should trigger fallback to Gather?
- Should internal notifications be sent for partial or failed AI calls?
- Should there be an admin review screen before email summaries are sent?
- What deployment target will host secure WebSocket traffic for live Twilio testing?

## Recommended Phase Sequence

1. Add feature flags and environment validation for AI voice.
2. Add a Realtime/Twilio WebSocket endpoint behind AI_VOICE_ENABLED=false by default.
3. Implement transcript-only streaming in a test environment.
4. Add structured tool calls for field extraction.
5. Convert completed call fields into Lead rows.
6. Add fallback-to-Gather behavior and failure logging.
7. Add end-to-end tests with mocked Twilio and mocked Realtime events.
8. Run limited live testing with internal callers only.
9. Review transcripts and guardrail failures before exposing to external callers.

The current Twilio Gather intake should remain available throughout this sequence and should be the default fallback whenever AI voice is disabled or unhealthy.
