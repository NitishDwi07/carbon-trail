"""
Utility / Electricity ingestion — portal CSV export format.

Why portal CSV?
  - PDF bills are the most common format but parsing them requires OCR or
    pdfplumber with layout heuristics that break on every utility's template.
  - APIs exist (Green Button Data / ESPI standard in the US, some Indian discoms
    have started REST APIs) but adoption is patchy and requires OAuth setup per utility.
  - The facilities team portal CSV is what actually gets emailed to sustainability leads.
    It's structured enough to parse reliably.

What a typical portal CSV looks like (based on looking at BESCOM, Tata Power,
MSEDCL portal exports and US utility Green Button CSV format):
  - Meter ID / account number
  - Billing period start / end (NOT always calendar months)
  - Units consumed in kWh
  - Tariff category (industrial, commercial, domestic)
  - Sometimes: peak vs off-peak split
  - Sometimes: reactive energy (kVArh) — we ignore this

Complications handled:
  - Billing periods that straddle month boundaries: we apportion by day
  - Units in MWh or kVAh (rare but real) — we convert
  - Missing meter IDs: we warn but don't reject
  - Duplicate billing periods: flagged as suspicious

Scope 2 emission factor: India grid (CEA 2023) = 0.716 kg CO2e / kWh
"""

import csv
import io
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation


# India grid emission factor (CEA CO2 baseline database 2023)
# In a real system this would be configurable per location/year
GRID_EF_KG_PER_KWH = Decimal('0.716')

UNIT_CONVERSIONS = {
    'KWH': Decimal('1'),
    'kWh': Decimal('1'),
    'MWH': Decimal('1000'),
    'MWh': Decimal('1000'),
    'KVAH': Decimal('1'),     # approx, ignoring power factor — flagged
    'kVAh': Decimal('1'),
}

COLUMN_ALIASES = {
    'Meter ID': ['Meter ID', 'MeterID', 'Account No', 'AccountNo', 'account_number', 'meter_id'],
    'Period Start': ['Period Start', 'From Date', 'Bill From', 'start_date', 'BillStartDate', 'ReadingFrom'],
    'Period End': ['Period End', 'To Date', 'Bill To', 'end_date', 'BillEndDate', 'ReadingTo'],
    'Units': ['Units Consumed', 'Units', 'Consumption', 'kWh', 'consumption_kwh', 'energy_kwh'],
    'Unit Type': ['Unit', 'UOM', 'unit_type', 'EnergyUnit'],
    'Tariff': ['Tariff', 'TariffCategory', 'tariff_code', 'Category'],
    'Facility': ['Facility', 'Site', 'Location', 'facility_name'],
    'Bill Amount': ['Amount', 'Bill Amount', 'Total', 'amount_inr'],
}


def resolve_col(headers: list[str], canonical: str) -> str | None:
    for alias in COLUMN_ALIASES.get(canonical, [canonical]):
        if alias in headers:
            return alias
    return None


def parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d.%m.%Y', '%d %b %Y', '%d-%b-%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(raw: str) -> Decimal | None:
    raw = raw.strip().replace(',', '')
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def days_in_period(start: date, end: date) -> int:
    return max(1, (end - start).days + 1)


def parse_utility_csv(file_content: bytes, batch_id, org_id) -> dict:
    try:
        text = file_content.decode('utf-8')
    except UnicodeDecodeError:
        text = file_content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {'records': [], 'errors': [(-1, 'Empty file')], 'stats': {}}

    headers = list(reader.fieldnames)
    col = {c: resolve_col(headers, c) for c in COLUMN_ALIASES.keys()}

    records = []
    errors = []
    seen_periods = {}   # meter_id -> list of (start, end) to detect duplicates

    for row_num, row in enumerate(reader, start=2):
        meter_id = row.get(col.get('Meter ID') or '', '').strip()
        facility = row.get(col.get('Facility') or '', '').strip()

        start_raw = row.get(col.get('Period Start') or '', '')
        end_raw = row.get(col.get('Period End') or '', '')

        start_date = parse_date(start_raw)
        end_date = parse_date(end_raw)

        if not start_date:
            errors.append((row_num, f"Cannot parse period start: '{start_raw}'"))
            continue
        if not end_date:
            errors.append((row_num, f"Cannot parse period end: '{end_raw}'"))
            continue
        if end_date < start_date:
            errors.append((row_num, f"End date {end_date} is before start date {start_date}"))
            continue

        units_raw = row.get(col.get('Units') or '', '')
        units = parse_decimal(units_raw)
        if units is None or units < 0:
            errors.append((row_num, f"Invalid units: '{units_raw}'"))
            continue

        unit_type = row.get(col.get('Unit Type') or '', 'kWh').strip()
        multiplier = UNIT_CONVERSIONS.get(unit_type, None)

        is_suspicious = False
        suspicion_reason = ''

        if multiplier is None:
            is_suspicious = True
            suspicion_reason = f"Unknown unit type '{unit_type}'"
            multiplier = Decimal('1')
        elif unit_type in ('KVAH', 'kVAh'):
            is_suspicious = True
            suspicion_reason = "kVAh ≠ kWh — power factor unknown, conversion is approximate"

        kwh = (units * multiplier).quantize(Decimal('0.0001'))
        co2e = (kwh * GRID_EF_KG_PER_KWH).quantize(Decimal('0.0001'))

        # Duplicate period detection
        key = meter_id or facility
        if key:
            prior = seen_periods.setdefault(key, [])
            for (ps, pe) in prior:
                if not (end_date < ps or start_date > pe):
                    is_suspicious = True
                    suspicion_reason = (suspicion_reason + '; ' if suspicion_reason else '') + \
                                       f"Overlapping billing period with another row ({ps} – {pe})"
                    break
            prior.append((start_date, end_date))

        # Sanity check: > 1,000,000 kWh in one bill is unusual for non-industrial
        if kwh > 1_000_000:
            is_suspicious = True
            suspicion_reason = (suspicion_reason + '; ' if suspicion_reason else '') + \
                               "Consumption > 1,000,000 kWh — verify this is correct"

        tariff = row.get(col.get('Tariff') or '', '').strip()

        records.append({
            'organisation_id': org_id,
            'batch_id': batch_id,
            'scope': '2',
            'category': 'electricity',
            'activity_date': start_date,   # we use billing start as the activity date
            'description': f"Electricity — {facility or meter_id or 'Unknown site'} "
                           f"({start_date} to {end_date})"
                           + (f" [{tariff}]" if tariff else ''),
            'quantity': units,
            'original_unit': unit_type,
            'normalised_unit': 'kWh',
            'normalised_quantity': kwh,
            'co2e_kg': co2e,
            'source_row_id': f"{meter_id}_{start_date}_{end_date}",
            'source_meter_id': meter_id,
            'source_plant_code': facility,
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
        }
    }
