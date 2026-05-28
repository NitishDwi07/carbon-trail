# Breathe ESG — Emissions Ingestion Prototype

Django REST + React app that ingests emissions data from SAP, utility portals, and corporate travel platforms, normalises it, and surfaces a review dashboard for analysts.

**Demo credentials:** `analyst` / `password123`

**Demo Link:**  https://breathe-esg-frontend-p3g2.onrender.com

---

## What it does

- Ingest CSV files from 3 source types: SAP fuel exports, utility portal downloads, Concur/Navan travel exports
- Normalise units (gallons → litres, MWh → kWh, miles → km), compute CO2e
- Flag suspicious rows automatically (unknown units, duplicate billing periods, outlier quantities)
- Review dashboard: filter by scope, status, suspicious; approve / flag / reject rows
- Audit trail on every record

---

## Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL

### 1. Create the database

```bash
psql -U postgres
CREATE DATABASE breathe_esg;
\q
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:

```
SECRET_KEY=django-insecure-dev-key-change-in-prod
DEBUG=True
DB_NAME=breathe_esg
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
```

Then run:

```bash
python manage.py makemigrations ingestion accounts
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### 3. Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

App → **http://localhost:5173** | API → **http://localhost:8000**

---

## Sample Data Files

Three sample CSVs are available from the Upload page ("sample CSV" link). Also in `docs/sample_data/`:
- `sample_sap.csv` — SAP MB51 fuel movements
- `sample_utility.csv` — utility portal electricity export
- `sample_travel.csv` — Concur travel extract

---

## Architecture

```
frontend/          React + Tailwind (Vite)
backend/
  breathe_esg/     Django project settings + URLs
  ingestion/       Main app
    models.py      EmissionRecord, IngestionBatch, Organisation, AuditLog
    views.py       Upload, Review, Dashboard, Batch endpoints
    serializers.py DRF serializers
    parsers/
      sap_parser.py       MB51 flat CSV
      utility_parser.py   Portal CSV export
      travel_parser.py    Concur/Navan CSV
    management/commands/seed_demo.py
  accounts/        Login, register, auth token
docs/
  MODEL.md         Data model documentation
  DECISIONS.md     Every ambiguity resolved
  TRADEOFFS.md     Three things not built and why
  SOURCES.md       Source format research
```

---

## Docs

- **`MODEL.md`** — multi-tenancy, Scope 1/2/3, source traceability, unit normalisation, audit trail
- **`DECISIONS.md`** — every non-obvious choice resolved with reasoning
- **`TRADEOFFS.md`** — 3 deliberate omissions and why
- **`SOURCES.md`** — real-world format research for each source type
