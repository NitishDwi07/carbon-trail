# MODEL.md — Data Model

## Core Design Principle

Everything collapses into one table: `EmissionRecord`. The three sources (SAP, utility, travel) are very different in shape but identical in what we ultimately need: a dated activity, a quantity, a unit, and a CO2e estimate. Keeping one normalised table makes the review dashboard and audit export simple.

---

## Tables

### `Organisation`
The multi-tenancy root. Every query starts with `WHERE organisation_id = ?`. Simple slug-based lookup. In a real deployment you'd add a plan/subscription field and enforce row-level security at the DB layer (PostgreSQL RLS policies). For the prototype, we filter in the Django ORM.

```
Organisation
  id          UUID PK
  name        varchar
  slug        varchar UNIQUE
  created_at  timestamptz
```

### `UserProfile`
A one-to-one extension of Django's built-in `User`. We don't touch the User model itself — that's asking for trouble with migrations. This just associates a user with their org.

```
UserProfile
  user         FK → User (OneToOne)
  organisation FK → Organisation
```

### `IngestionBatch`
One upload = one batch. This exists so we can:
1. Show analysts "what came in together"
2. Retry or delete a failed upload cleanly (cascade deletes all its records)
3. Track who uploaded what and when

```
IngestionBatch
  id               UUID PK
  organisation     FK → Organisation
  source_type      enum: sap | utility | travel
  uploaded_by      FK → User (nullable, SET NULL on delete)
  uploaded_at      timestamptz
  original_filename varchar
  raw_file         FileField (stored in /media/uploads/)
  status           enum: pending | processing | done | failed
  row_count        int
  error_count      int
  notes            text
```

### `EmissionRecord` — the main table
Every activity row from every source lives here after normalisation.

```
EmissionRecord
  id                  UUID PK
  organisation        FK → Organisation
  batch               FK → IngestionBatch

  -- Classification
  scope               enum: 1 | 2 | 3
  category            enum: fuel | electricity | flight | hotel | ground_transport | procurement

  -- Activity
  activity_date       date
  description         varchar(500)
  quantity            decimal(18,4)    -- original quantity as-ingested
  original_unit       varchar(50)      -- L, GAL, kWh, MWh, km, nights, KG
  normalised_unit     varchar(50)      -- L, kWh, km, nights, KG (post-conversion)
  normalised_quantity decimal(18,4)
  co2e_kg             decimal(18,4) nullable  -- null if EF not applied

  -- Source traceability
  source_row_id       varchar(200)   -- SAP doc number, meter+period key, trip ID
  source_plant_code   varchar(100)   -- SAP plant / utility facility
  source_meter_id     varchar(100)   -- utility meter reference
  source_vendor       varchar(200)   -- travel: employee name

  -- Review workflow
  status              enum: pending | approved | flagged | rejected
  reviewed_by         FK → User nullable
  reviewed_at         timestamptz nullable
  reviewer_note       text

  -- Flags
  is_suspicious       bool
  suspicion_reason    varchar(500)

  -- Audit
  created_at          timestamptz
  updated_at          timestamptz
  locked              bool  -- true once approved → sent to auditors
  raw_data            jsonb -- full original row for traceability
```

### `AuditLog`
Immutable log of every status change. Written by view logic, never by the user directly. Django signals would be cleaner in a larger codebase; here I write it explicitly in the review endpoint so it's obvious what's happening.

```
AuditLog
  id          bigint PK (auto)
  record      FK → EmissionRecord
  changed_by  FK → User nullable
  changed_at  timestamptz
  action      varchar(100)   -- "status_change", "field_edit"
  before      jsonb
  after       jsonb
  note        text
```

---

## Design Decisions

**Why UUID PKs?** Batch IDs and record IDs get exposed in API responses and URLs. Integer PKs leak row counts ("batch 4" tells someone this is a small operation). UUIDs are also safe to generate client-side if needed.

**Why `locked` as a bool?** Once a record is approved and sent to auditors it must not change. A `locked` flag is explicit and queryable. An alternative would be a separate `AuditLockedRecord` table but that's overkill for a prototype.

**Why store `raw_data` as JSONB?** Every row keeps its original source data. When an analyst disputes a number, they can see exactly what came in from the source system. Also helps with re-ingestion if the emission factor changes — you can recompute CO2e from raw data without re-uploading.

**Why `original_unit` AND `normalised_unit`?** A SAP row comes in as `GAL`. We convert to litres and store both. The analyst can see the original and verify the conversion. Trust but verify.

**Scope assignment:**
- Scope 1: SAP fuel rows (direct combustion by the company)
- Scope 2: Utility electricity rows (purchased electricity)
- Scope 3: All travel rows (employee business travel = Scope 3 category 6)

**Multi-tenancy enforcement:** Every model has `organisation` FK. The ORM always filters `filter(organisation=org)`. No cross-tenant data leakage. In production you'd add a DB-level constraint or use Django Guardian for more granular permissions.

---

## What's Missing (deliberately, see TRADEOFFS.md)

- Emission factor versioning table (right now EFs are hardcoded constants)
- Reporting periods / fiscal year alignment
- Multi-user roles within an org (admin vs read-only analyst)
