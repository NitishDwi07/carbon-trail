# TRADEOFFS.md — Three Things I Didn't Build

---

## 1. Emission Factor Management

**What it would be:** A database table for emission factors (EFs) with versioning — `EmissionFactor(source_type, fuel_type, year, value, unit, reference)`. Analysts could update DEFRA values when new guidance drops. Re-computing CO2e for existing records when an EF changes.

**Why I didn't build it:**
EFs are currently hardcoded constants in the parsers. This is technically wrong — DEFRA releases new values every June, and India's CEA grid factor changes annually. But building EF management correctly is non-trivial: you need to decide whether historical records re-compute when EFs change (usually no — you want a snapshot of what the calculation was at the time of ingestion) or whether you store EF versions alongside each record. That design decision deserves a separate conversation with the PM and auditors. For the prototype, hardcoded constants with citations (DEFRA 2023, CEA 2023) is honest and auditable. I've left the architecture obvious — EF is computed in one function per parser, easy to swap out.

---

## 2. Multi-user Roles Within an Organisation

**What it would be:** Role-based access control (RBAC) — `admin` can upload and approve; `analyst` can review but not upload; `auditor` can only read locked records. Django Guardian or a simple `UserRole` table.

**Why I didn't build it:**
The assignment says "let analysts review and sign off." That implies one role. Building a full RBAC system adds model complexity (another table, permission checks in every view, frontend conditionals everywhere) without demonstrating anything new about the core problem. The current system correctly enforces org-level isolation (users only see their org's data). Role granularity is a product decision that depends on how many people use the system per org. I'd raise it in the post-submission conversation.

---

## 3. Scheduled/Automatic Data Pulls

**What it would be:** A Celery + Redis task queue with periodic jobs: pull SAP OData every night, poll the utility portal API (if one exists), sync Concur via OAuth. Beat scheduler to run these on a cron. Error alerting when a pull fails.

**Why I didn't build it:**
File upload is the right ingestion mechanism for a prototype when you're still learning the client's data. Automatic pulls require stable API credentials, error handling for API downtime, idempotency (don't double-ingest if you pull the same data twice), and the EF versioning problem above. The upload-based approach is actually the correct starting point — it forces the client to be intentional about what data they're sending, and it surfaces data quality issues before you automate around them. Automation makes sense after you've ingested manually 3-4 times and you understand the data's shape. The current architecture (batch model, parser functions) makes it straightforward to add a Celery task that calls `parse_sap_csv()` on a downloaded file — the plumbing is all there.
