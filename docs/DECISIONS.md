# DECISIONS.md — Ambiguity Resolution

Every non-obvious choice I made and why.

---

## SAP: Which export format?

**Ambiguity:** SAP exposes data as IDocs, OData services, BAPIs, or flat file exports. Pick one.

**Decision:** Flat CSV from transaction reports (MB51 for material movements, ME2M for POs).

**Why:** 
- IDocs require ALE/EDI middleware. Most clients haven't configured this for external parties.
- OData (SAP Gateway) requires the BASIS team to have activated the relevant services. Not always the case, and needs OAuth setup.
- The flat CSV is what the client's sustainability lead actually exports and emails. It's the format that exists in every SAP installation without any additional setup.
- Yes it's ugly (German column names, European decimal format, DD.MM.YYYY dates) but it's real.

**What I'd ask the PM:** "Does the client have a BASIS consultant who can activate SAP Gateway? If yes, OData is cleaner and we can schedule pulls. If not, file upload is the right call."

---

## SAP: Which material movements to ingest?

**Ambiguity:** SAP has hundreds of movement types. We can't treat all material movements as fuel.

**Decision:** Filter to movement types 261 (goods issue to production order) and 201 (goods issue to cost centre), AND filter to fuel-relevant material groups (hardcoded set: `0020`, `0021`, `BF01`, `BF02`, `FUEL`).

**Why:**
- 261 and 201 are the standard ways fuel gets consumed in SAP.
- Material group is the client-side filter — the client's MM team assigns material groups. Fuel typically gets `BF01` or a similar prefix. We document this assumption.
- We explicitly skip reversal documents (262, 202) to avoid double-counting.

**What I'd ask the PM:** "Can you get the client's list of material groups that correspond to fuel? Our hardcoded set is approximate."

---

## Utility: PDF vs CSV vs API?

**Ambiguity:** Utility data comes as PDFs, portal CSV exports, or APIs.

**Decision:** Portal CSV export.

**Why:**
- PDFs require layout-specific parsing. Every utility has a different template. `pdfplumber` gets you 80% of the way and the last 20% is a nightmare.
- Green Button Data (ESPI) API is standard in the US but adoption in India is minimal. BESCOM, MSEDCL, Tata Power — none of them have a documented REST API for third parties.
- The facilities team can download a CSV from the portal in 2 clicks. This is what they already do for their own records.

**What I'd ask the PM:** "Is this client US-based or India? If US and on a smart meter, Green Button Data is worth implementing. For India, CSV is the right call for now."

---

## Utility: How to handle billing periods that don't align with calendar months?

**Ambiguity:** Utility bills often cover 28-35 day periods, not calendar months. Some meters read on the 15th, some on the 5th.

**Decision:** Use the billing period start date as `activity_date`. Store the full period in `description`. Do NOT prorate to calendar months.

**Why:**
- Proration is lossy and introduces artificial precision.
- The auditor cares about which bill covered which consumption, not about calendar month alignment.
- If month-level reporting is needed, it can be done in the analytics layer (GROUP BY month of activity_date), which is close enough for most purposes.

---

## Travel: Concur vs Navan vs generic CSV?

**Ambiguity:** Different clients use different travel platforms.

**Decision:** Generic CSV with documented column names. Provide Concur-aligned defaults.

**Why:**
- Building Concur OAuth is a week of work on its own. The assignment says 4 days.
- Both Concur and Navan offer "Report Extract" CSV downloads. The columns differ slightly but are the same data.
- Our column alias system (`COLUMN_ALIASES` in `travel_parser.py`) handles both platform's naming conventions.

---

## Travel: What to do when distance isn't given?

**Ambiguity:** Travel exports often give origin/destination airport codes but no distance. Sometimes you only have a city name.

**Decision:** 
1. If airport codes match our hardcoded dictionary → compute haversine distance
2. If city names only → flag as suspicious, use cost-based estimate for ground transport
3. If neither → flag with 0 km, analyst must review

**Why:**
- Haversine on airport coordinates is accurate enough for emissions purposes (within 5% of actual flight path).
- Cost-based estimates for taxis are rough (₹15/km assumption) but better than dropping the row. The suspicious flag ensures the analyst sees it.

**What I'd ask the PM:** "Can we subscribe to an airport distance API (e.g. Aviation Edge)? Our hardcoded table covers 17 airports. A real client might have flights to 200+ airports."

---

## Review workflow: Approve → Lock immediately?

**Ambiguity:** Should approval lock the record, or should there be a separate "send to auditor" step?

**Decision:** Approve → locked immediately.

**Why:**
- For a prototype, one step is clearer than two.
- The assignment says "approve rows before they go to auditors" — I interpreted "approve" as the final step.
- In production I'd probably add a separate "Export to audit" action that locks a batch at once.

---

## What subset of each source did we handle?

**SAP:** Fuel-relevant material movements only (MB51-style export). We ignore procurement POs, service entries, and non-fuel materials. We handle the European number format and German column headers.

**Utility:** Grid electricity consumption only. We handle kWh and MWh. We ignore reactive energy (kVArh), demand charges, and solar/renewable generation credits.

**Travel:** Flights, hotels, taxis, car rentals, trains. We ignore meals, conference registrations, and miscellaneous expenses (these are Scope 3 category 1, not category 6, and need different EFs).
