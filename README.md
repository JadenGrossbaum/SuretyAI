# SuretyAI

SuretyAI is a backend foundation for an AI phone intake system for surety bond leads.

Phase 1 provides a clean FastAPI app, configuration loading, SQLite database setup, SQLAlchemy base/session wiring, tests, and Docker support. Twilio and voice integrations are not included in this phase.

Important boundary: SuretyAI must not approve or deny surety bonds. It only collects preliminary screening information for a human surety professional to review.

## Project Layout

~~~text
backend/
  app/
    main.py
    config.py
    database.py
    models/
    schemas/
    services/
    api/
    prompts/
    scoring/
  tests/
  requirements.txt
~~~

## Local Setup

~~~bash
cd /home/jaden/Projects/SuretyAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
uvicorn app.main:app --app-dir backend --reload
~~~

Open http://127.0.0.1:8000/health.

## Local Developer Workflow

### Open The API Docs

Start the app locally:

~~~bash
cd /home/jaden/Projects/SuretyAI
source .venv/bin/activate
uvicorn app.main:app --app-dir backend --reload
~~~

Then open these URLs:

~~~text
http://127.0.0.1:8000/
http://127.0.0.1:8000/docs
~~~

The root route returns a small welcome response with links to /docs and /health.

### Seed Sample Leads

To create two sample surety leads in the local SQLite database:

~~~bash
cd /home/jaden/Projects/SuretyAI
source .venv/bin/activate
PYTHONPATH=backend python backend/scripts/seed_leads.py
~~~

The script is idempotent for its sample email addresses, so rerunning it will print the existing sample leads instead of creating duplicates.

### Create A Lead Through Swagger

1. Start the app with uvicorn app.main:app --app-dir backend --reload.
2. Open http://127.0.0.1:8000/docs.
3. Expand POST /api/leads.
4. Click Try it out.
5. Paste a JSON request body for a lead.
6. Click Execute.
7. Look for the response body. The id field is the database ID for that new lead.

### Find A Lead ID

Use one of these options:

- In Swagger, run GET /api/leads and look at the id field for each lead.
- Run the seed script and read the printed output, which starts each sample with its ID.
- After creating a lead with POST /api/leads, use the id returned in the response body.

### Why GET /api/leads/{id} Needs An Existing ID

GET /api/leads/{id} reads one saved database row by its primary key. The {id} value is not a placeholder name or a phone number; it must be a real integer ID that already exists in the SQLite database. If the app has no leads yet, or if you use an ID that does not exist, the API returns 404 Lead not found.

## Lead Intake API

Phase 2 adds lead intake persistence and read endpoints:

~~~text
POST /api/leads
GET /api/leads
GET /api/leads/{id}
~~~

Lead records capture contractor profile, bond need, financial screening, callback preference, notes, score/status defaults, and creation timestamp. The API stores intake information only and does not approve or deny bonds.

## Preliminary Lead Scoring

Phase 3 adds preliminary review scoring for intake leads. The scoring service outputs only these categories:

~~~text
Strong Candidate
Needs Review
Higher Risk / Human Review Required
~~~

These categories are triage labels for human surety review. They are not approvals, denials, quotes, or binding decisions.

## Phone Intake Agent Flow

Phase 4 adds the surety phone intake agent prompt and reusable call-flow service:

~~~text
backend/app/prompts/surety_intake_agent.md
backend/app/services/call_flow.py
~~~

The scripted flow greets the caller, explains preliminary screening, asks permission to continue, collects one field at a time, avoids underwriting advice and decision language, and closes by routing the information to human review.

## Twilio Phone Webhooks

Phase 5 adds MVP Twilio webhook support for a dedicated phone number:

~~~text
POST /api/twilio/voice
POST /api/twilio/status
~~~

Configure these environment variables in .env:

~~~text
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
PUBLIC_BASE_URL=http://localhost:8000
~~~

The voice endpoint returns TwiML that greets the caller, explains the MVP is preliminary intake for human review, logs a call session, and stores a system transcript entry. The status endpoint records Twilio call status updates. The call session and transcript models are prepared so the next phase can connect the phone call to an AI voice agent.

For live phone testing, set TWILIO_AUTH_TOKEN and PUBLIC_BASE_URL to the exact public webhook base URL configured in Twilio. In non-development environments, Twilio webhooks are rejected unless request signature validation is configured and passes.

## Internal Email Notifications

Phase 6 sends an internal email summary after a lead is created. Configure SMTP in .env:

~~~text
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
INTERNAL_NOTIFICATION_EMAIL=
~~~

The summary includes contact information, bond need, lead score, review category, key risk flags, financial fields, callback preference, and notes. If SMTP is not configured, lead creation still succeeds and notification sending is skipped.

## Run Tests

~~~bash
cd /home/jaden/Projects/SuretyAI
source .venv/bin/activate
PYTHONPATH=backend pytest backend/tests
~~~

## Docker

~~~bash
cd /home/jaden/Projects/SuretyAI
cp .env.example .env
docker compose up --build
~~~

The API listens on http://127.0.0.1:8000.

## Live Twilio Phone Testing

Use this checklist when you are ready to buy or configure a Twilio phone number and route calls to your local FastAPI server.

### 1. Configure .env

Copy .env.example to .env if needed, then set:

~~~text
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+15555550123
PUBLIC_BASE_URL=https://your-ngrok-domain.ngrok-free.app
~~~

PUBLIC_BASE_URL must be the exact HTTPS base URL that Twilio can reach. Do not include /api/twilio/voice in PUBLIC_BASE_URL.

### 2. Run FastAPI Locally

In one terminal:

~~~bash
cd /home/jaden/Projects/SuretyAI
source .venv/bin/activate
uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
~~~

Confirm the local app is running:

~~~text
http://127.0.0.1:8000/
http://127.0.0.1:8000/api/twilio/debug
~~~

The debug endpoint returns booleans for whether Twilio-related environment variables are present. It does not expose TWILIO_AUTH_TOKEN or other secret values.

### 3. Run ngrok

In a second terminal:

~~~bash
ngrok http 8000
~~~

Copy the HTTPS forwarding URL from ngrok and set it as PUBLIC_BASE_URL in .env, then restart uvicorn so the new value is loaded.

### 4. Configure Twilio Webhook URL

In Twilio Console, set the phone number voice webhook to:

~~~text
{PUBLIC_BASE_URL}/api/twilio/voice
~~~

For example:

~~~text
https://your-ngrok-domain.ngrok-free.app/api/twilio/voice
~~~

Use HTTP POST.

Optional status callback URL:

~~~text
{PUBLIC_BASE_URL}/api/twilio/status
~~~

Also use HTTP POST.

### 5. Verify Twilio Hits The Backend

Call the Twilio phone number. During a successful MVP call:

- Your phone should hear the SuretyAI MVP greeting.
- The call should end after the greeting.
- GET /api/twilio/debug should show ready_for_live_testing: true when all Twilio variables are set.
- The local SQLite database should contain a call_sessions row and a transcript_entries row for the system greeting.

### Expected Terminal Logs

In the uvicorn terminal, a successful inbound call should show lines similar to:

~~~text
Twilio voice webhook received call_sid=CA... from=+1... to=+1... status=in-progress
Twilio voice webhook logged call_session_id=1 call_sid=CA...
INFO: <twilio-ip>:0 - POST /api/twilio/voice HTTP/1.1 200 OK
~~~

A successful status callback should show lines similar to:

~~~text
Twilio status webhook received call_sid=CA... status=completed
Twilio status webhook updated call_session_id=1 call_sid=CA...
INFO: <twilio-ip>:0 - POST /api/twilio/status HTTP/1.1 200 OK
~~~

If Twilio returns 403, check that TWILIO_AUTH_TOKEN matches Twilio Console and that PUBLIC_BASE_URL exactly matches the ngrok HTTPS base URL used in the Twilio webhook configuration.
