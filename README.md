# Breathe ESG — Emissions Ingestion Prototype

Django REST + React app that ingests emissions data from SAP, utility portals, and corporate travel platforms, normalises it, and surfaces a review dashboard for analysts.

**Demo:** analyst / password123

---

## What it does

- Ingest CSV files from 3 source types: SAP fuel exports, utility portal downloads, Concur/Navan travel exports
- Normalise units (gallons → litres, MWh → kWh, miles → km), compute CO2e
- Flag suspicious rows automatically (unknown units, duplicate billing periods, outlier quantities)
- Review dashboard: filter by scope, status, suspicious; approve / flag / reject rows
- Audit trail on every record

## Local Setup

### Backend (Django)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create a PostgreSQL database called breathe_esg
# Update settings.py DB config if needed

python manage.py migrate
python manage.py seed_demo  # creates analyst user + sample data
python manage.py runserver
```

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

App runs at http://localhost:5173. Backend at http://localhost:8000.

---

## Deployment (Render)

1. Push to GitHub
2. Go to render.com → New → Blueprint
3. Point at this repo, select `render.yaml`
4. Render will create: PostgreSQL DB, Django backend, React static site

---

## Sample Data Files

Three sample CSVs are available from the Upload page ("sample CSV" link). You can also download them from `docs/sample_data/`:
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

## Grading notes

- **Data model:** `MODEL.md` covers multi-tenancy, Scope 1/2/3, source traceability, unit normalisation, audit trail
- **Source research:** `SOURCES.md` explains what each format actually looks like in the wild
- **Decisions:** `DECISIONS.md` covers every non-obvious choice
- **Tradeoffs:** `TRADEOFFS.md` covers 3 deliberate omissions with reasoning
- **UX:** Analyst can filter, review, and action records without knowing anything about the underlying data model
