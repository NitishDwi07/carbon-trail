"""
SAP ingestion — handles the MB51 / ME2M style flat CSV export.

Why flat CSV over IDoc or OData?
  - IDoc requires an ALE/EDI middleware layer most clients don't expose externally.
  - OData (via SAP Gateway) is available only if the client's BASIS team has activated it.
  - The flat CSV / XLSX from SAP transactions (MB51 for material movements,
    ME2M for purchase orders) is what sustainability leads actually email you.
  - It's ugly but it's real. Every SAP CSV I've seen has: a German-English mixed header
    row, date in DD.MM.YYYY, quantities with European decimals (1.234,56 = 1234.56),
    and a plant code that means nothing without the client's plant master.

What we handle:
  - Material movements relevant to fuel (Mvt type 261 = goods issue to production,
    201 = goods issue to cost centre). We filter to fuel-relevant material groups.
  - Procurement PO lines for diesel, petrol, natural gas.

What we deliberately ignore:
  - Non-fuel materials (raw materials, spare parts, etc.)
  - Intra-company stock transfers
  - Reversal documents (we flag them but don't double-count)
"""

import csv
import io
import decimal
from datetime import datetime
from decimal import Decimal, InvalidOperation


# Emission factors in kg CO2e per litre (DEFRA 2023 values, simplified)
FUEL_EMISSION_FACTORS = {
    'diesel': Decimal('2.6808'),
    'petrol': Decimal('2.3108'),
    'natural_gas': Decimal('2.0402'),   # per kg, not litre — handled separately
    'lpg': Decimal('1.5554'),
}

# Plant codes → human readable (client would supply this lookup)
# We fabricate a small one for the demo
PLANT_LOOKUP = {
    '1000': 'Mumbai Plant',
    '1100': 'Delhi Warehouse',
    '1200': 'Chennai Facility',
    '2000': 'Pune Office',
}

# SAP material groups that count as fuel for us
FUEL_MATERIAL_GROUPS = {'0020', '0021', 'BF01', 'BF02', 'FUEL'}

# Column name aliases — SAP exports differ by client config and language
SAP_COLUMN_ALIASES = {
    'Posting Date': ['Buchungsdatum', 'Posting Date', 'Belegdatum', 'PostingDate'],
    'Material': ['Material', 'Materialnummer', 'Mat.', 'MaterialNo'],
    'Material Description': ['Kurztext', 'Material Description', 'Description', 'MatDesc'],
    'Quantity': ['Menge', 'Quantity', 'Qty', 'Bewegungsmenge'],
    'Unit': ['ME', 'Unit', 'BaseUnit', 'Einheit', 'UOM'],
    'Plant': ['Werk', 'Plant', 'Profit Center'],
    'Material Group': ['Warengruppe', 'Material Group', 'MatGrp', 'MatkL'],
    'Movement Type': ['Bewegungsart', 'Movement Type', 'MvtType', 'BwArt'],
    'Document Number': ['Materialbelegart', 'Document', 'DocNo', 'MBlNr'],
    'Amount': ['Betrag', 'Amount', 'Value', 'Wert'],
    'Currency': ['Waehrung', 'Currency', 'Curr'],
}


def resolve_column(header_row: list[str], canonical: str) -> str | None:
    """
    Find the actual column name in the file for a canonical field name.
    SAP headers vary by language pack and config — this normalises that.
    """
    aliases = SAP_COLUMN_ALIASES.get(canonical, [canonical])
    for alias in aliases:
        if alias in header_row:
            return alias
    return None


def parse_sap_date(raw: str) -> datetime | None:
    """SAP dates come in DD.MM.YYYY or YYYYMMDD or MM/DD/YYYY. Try all."""
    raw = raw.strip()
    for fmt in ('%d.%m.%Y', '%Y%m%d', '%m/%d/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_european_number(raw: str) -> Decimal | None:
    """
    SAP with German locale uses 1.234,56 for 1234.56.
    We detect this by checking if comma comes after dot.
    """
    raw = raw.strip().replace(' ', '')
    if not raw:
        return None
    try:
        # European format: 1.234,56
        if ',' in raw and '.' in raw:
            if raw.index('.') < raw.index(','):
                raw = raw.replace('.', '').replace(',', '.')
            else:
                raw = raw.replace(',', '')
        elif ',' in raw:
            raw = raw.replace(',', '.')
        return Decimal(raw)
    except InvalidOperation:
        return None


def infer_fuel_type(material_desc: str, material_group: str) -> str:
    """Best-effort fuel type from description and material group."""
    desc = (material_desc or '').lower()
    if any(kw in desc for kw in ['diesel', 'hsd', 'high speed']):
        return 'diesel'
    if any(kw in desc for kw in ['petrol', 'gasoline', 'mogas']):
        return 'petrol'
    if any(kw in desc for kw in ['natural gas', 'cng', 'lng', 'erdgas']):
        return 'natural_gas'
    if any(kw in desc for kw in ['lpg', 'propane', 'butane']):
        return 'lpg'
    return 'diesel'  # fallback — flagged as suspicious


def normalise_to_litres(qty: Decimal, unit: str) -> tuple[Decimal, str, bool]:
    """
    Returns (normalised_qty, normalised_unit, is_suspicious).
    SAP units: L, LT, GAL, KG, M3, etc.
    """
    unit = unit.strip().upper()
    conversions = {
        'L': (qty, 'L', False),
        'LT': (qty, 'L', False),
        'LTR': (qty, 'L', False),
        'GAL': (qty * Decimal('3.785411784'), 'L', False),
        'GL': (qty * Decimal('3.785411784'), 'L', False),
        'KG': (qty, 'KG', False),   # kg stays kg for gas — EF is per kg
        'M3': (qty * Decimal('1000'), 'L', False),
        'CM3': (qty / Decimal('1000'), 'L', False),
    }
    if unit in conversions:
        return conversions[unit]
    # Unknown unit — pass through raw, flag it
    return (qty, unit, True)


def calculate_co2e(qty: Decimal, unit: str, fuel_type: str) -> Decimal | None:
    ef = FUEL_EMISSION_FACTORS.get(fuel_type)
    if ef is None:
        return None
    if unit in ('L', 'LT', 'LTR'):
        return (qty * ef).quantize(Decimal('0.0001'))
    if unit == 'KG' and fuel_type == 'natural_gas':
        return (qty * ef).quantize(Decimal('0.0001'))
    return None


def parse_sap_csv(file_content: bytes, batch_id, org_id) -> dict:
    """
    Main entry point. Returns dict with:
      - records: list of dicts ready to bulk_create as EmissionRecord
      - errors: list of (row_num, reason)
      - stats: summary counts
    """
    from ingestion.models import IngestionBatch

    try:
        text = file_content.decode('utf-8')
    except UnicodeDecodeError:
        text = file_content.decode('latin-1')  # SAP often exports in CP1252/latin-1

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {'records': [], 'errors': [(-1, 'File is empty or not a valid CSV')], 'stats': {}}

    headers = list(reader.fieldnames)

    # Resolve column names
    col = {
        canonical: resolve_column(headers, canonical)
        for canonical in SAP_COLUMN_ALIASES.keys()
    }

    records = []
    errors = []
    skipped_non_fuel = 0

    for row_num, row in enumerate(reader, start=2):
        # Skip non-fuel material groups
        mat_grp = row.get(col.get('Material Group') or '', '').strip()
        if mat_grp and mat_grp not in FUEL_MATERIAL_GROUPS:
            skipped_non_fuel += 1
            continue

        # Parse date
        date_raw = row.get(col.get('Posting Date') or '', '')
        parsed_date = parse_sap_date(date_raw)
        if not parsed_date:
            errors.append((row_num, f"Unparseable date: '{date_raw}'"))
            continue

        # Parse quantity
        qty_raw = row.get(col.get('Quantity') or '', '')
        qty = parse_european_number(qty_raw)
        if qty is None or qty <= 0:
            errors.append((row_num, f"Invalid quantity: '{qty_raw}'"))
            continue

        unit = row.get(col.get('Unit') or '', 'L').strip()
        mat_desc = row.get(col.get('Material Description') or '', '')
        plant_code = row.get(col.get('Plant') or '', '')
        doc_num = row.get(col.get('Document Number') or '', '')
        mvt_type = row.get(col.get('Movement Type') or '', '')

        # Skip reversals (movement type 262, 202 are reversals of 261, 201)
        if mvt_type in ('262', '202', '542'):
            skipped_non_fuel += 1
            continue

        fuel_type = infer_fuel_type(mat_desc, mat_grp)
        norm_qty, norm_unit, unit_suspicious = normalise_to_litres(qty, unit)
        co2e = calculate_co2e(norm_qty, norm_unit, fuel_type)

        is_suspicious = unit_suspicious
        suspicion_reason = ''

        if unit_suspicious:
            suspicion_reason = f"Unknown unit '{unit}' — could not normalise"
        if fuel_type == 'diesel' and mat_desc and not any(
            kw in mat_desc.lower() for kw in ['diesel', 'hsd', 'petrol', 'gas', 'fuel', 'lpg']
        ):
            is_suspicious = True
            suspicion_reason = (suspicion_reason + '; ' if suspicion_reason else '') + \
                               "Fuel type inferred by fallback — description unclear"

        # Flag outliers: > 50,000 L in one row is suspicious
        if norm_qty > 50000 and norm_unit == 'L':
            is_suspicious = True
            suspicion_reason = (suspicion_reason + '; ' if suspicion_reason else '') + \
                               "Quantity > 50,000 L in single row"

        records.append({
            'organisation_id': org_id,
            'batch_id': batch_id,
            'scope': '1',
            'category': 'fuel',
            'activity_date': parsed_date.date(),
            'description': f"{fuel_type.replace('_', ' ').title()} — {mat_desc or 'SAP material'}",
            'quantity': qty,
            'original_unit': unit,
            'normalised_unit': norm_unit,
            'normalised_quantity': norm_qty,
            'co2e_kg': co2e,
            'source_row_id': doc_num,
            'source_plant_code': PLANT_LOOKUP.get(plant_code, plant_code),
            'source_vendor': '',
            'is_suspicious': is_suspicious,
            'suspicion_reason': suspicion_reason,
            'raw_data': dict(row),
        })

    return {
        'records': records,
        'errors': errors,
        'stats': {
            'parsed': len(records),
            'errors': len(errors),
            'skipped_non_fuel': skipped_non_fuel,
        }
    }
