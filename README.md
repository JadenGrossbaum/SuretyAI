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

## Lead Intake API

Phase 2 adds lead intake persistence and read endpoints:

~~~text
POST /api/leads
GET /api/leads
GET /api/leads/{id}
~~~

Lead records capture contractor profile, bond need, financial screening, callback preference, notes, score/status defaults, and creation timestamp. The API stores intake information only and does not approve or deny bonds.

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
