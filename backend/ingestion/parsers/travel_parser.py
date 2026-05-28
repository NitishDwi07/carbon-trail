"""
Corporate Travel ingestion — Concur / Navan CSV export format.

Why CSV export over API?
  - Concur's Travel API (SAP Concur v4) requires OAuth and a registered app —
    enterprise clients often haven't provisioned this for third parties.
  - Navan (formerly TripActions) has a similar OAuth flow.
  - Both platforms reliably offer a manual CSV export from their reporting module,
    which is what travel managers actually send you.
  - In a production system you'd do OAuth + webhook; for the prototype CSV is correct.

What a Concur expense/travel export looks like (from their Report Extract docs):
  - Trip ID / Expense Report ID
  - Employee name + employee ID
  - Travel date
  - Category: Air, Hotel, Car Rental, Taxi/Rideshare, Train, Mileage
  - Origin / Destination (city or airport code for flights)
  - Amount + Currency
  - Sometimes: distance (for car/mileage); sometimes you only get cost
  - For flights: cabin class (Economy, Business, First)

Emission factors used:
  - Flights: DEFRA 2023 kg CO2e per km per passenger, by cabin
  - Hotel: HCMI methodology ~20 kg CO2e per room-night (approximate)
  - Car rental: 0.192 kg/km (avg petrol car)
  - Taxi/ride-share: 0.149 kg/km (DEFRA, average)
  - Train: 0.037 kg/km (Indian Railways average)

Airport distance: We use the haversine formula with hardcoded coords for common airports.
In production you'd call an airport API.
"""

import csv
import io
import math
from decimal import Decimal, InvalidOperation
from datetime import datetime


# Emission factors kg CO2e per km per passenger
FLIGHT_EF = {
    'economy':  Decimal('0.1551'),
    'premium':  Decimal('0.2330'),
    'business': Decimal('0.4286'),
    'first':    Decimal('0.5765'),
}
HOTEL_EF_PER_NIGHT = Decimal('20.0')
CAR_EF_PER_KM = Decimal('0.192')
TAXI_EF_PER_KM = Decimal('0.149')
TRAIN_EF_PER_KM = Decimal('0.037')

# Hardcoded airport coords — common ones to make demo work
# lat, lon in degrees
AIRPORT_COORDS = {
    'BOM': (19.0896, 72.8656),
    'DEL': (28.5562, 77.1000),
    'MAA': (12.9941, 80.1709),
    'BLR': (13.1986, 77.7066),
    'HYD': (17.2313, 78.4298),
    'CCU': (22.6520, 88.4463),
    'AMD': (23.0771, 72.6347),
    'PNQ': (18.5822, 73.9197),
    'GOI': (15.3808, 73.8314),
    'LHR': (51.4775, -0.4614),
    'JFK': (40.6413, -73.7781),
    'CDG': (49.0097, 2.5479),
    'DXB': (25.2528, 55.3644),
    'SIN': (1.3644, 103.9915),
    'FRA': (50.0379, 8.5622),
    'NRT': (35.7720, 140.3929),
    'SFO': (37.6213, -122.3790),
    'ORD': (41.9742, -87.9073),
}


def haversine_km(coord1, coord2) -> Decimal:
    """Great-circle distance between two (lat, lon) pairs in km."""
    R = 6371.0
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return Decimal(str(round(R * c, 2)))


def parse_date(raw: str):
    raw = raw.strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d %b %Y'):
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


def normalise_category(raw: str) -> str:
    raw = raw.lower().strip()
    if any(k in raw for k in ['air', 'flight', 'airline', 'fly']):
        return 'flight'
    if any(k in raw for k in ['hotel', 'accommodation', 'lodg']):
        return 'hotel'
    if any(k in raw for k in ['taxi', 'ride', 'uber', 'ola', 'cab', 'lyft']):
        return 'ground_transport'
    if any(k in raw for k in ['car', 'rental', 'hire', 'mileage', 'driving']):
        return 'ground_transport'
    if any(k in raw for k in ['train', 'rail', 'metro', 'bus', 'transit']):
        return 'ground_transport'
    return 'ground_transport'   # fallback


def normalise_cabin(raw: str) -> str:
    raw = (raw or '').lower()
    if 'first' in raw:
        return 'first'
    if any(k in raw for k in ['biz', 'business', 'club', 'j']):
        return 'business'
    if any(k in raw for k in ['prem', 'plus', 'comfort']):
        return 'premium'
    return 'economy'


COLUMN_ALIASES = {
    'Trip ID': ['Trip ID', 'TripID', 'Report ID', 'expense_report_id', 'BookingRef'],
    'Date': ['Travel Date', 'Date', 'trip_date', 'departure_date', 'Expense Date'],
    'Employee': ['Employee', 'Traveler', 'traveller_name', 'Name', 'employee_name'],
    'Category': ['Category', 'ExpenseType', 'expense_type', 'travel_type', 'Type'],
    'Origin': ['Origin', 'From', 'origin_airport', 'DepartureCity', 'departure'],
    'Destination': ['Destination', 'To', 'dest_airport', 'ArrivalCity', 'arrival'],
    'Distance': ['Distance', 'distance_km', 'Miles', 'km', 'Kilometers'],
    'Distance Unit': ['Distance Unit', 'dist_unit', 'DistUnit'],
    'Nights': ['Nights', 'nights_stayed', 'Duration', 'NightCount'],
    'Cabin': ['Cabin', 'class', 'CabinClass', 'travel_class', 'FlightClass'],
    'Amount': ['Amount', 'Cost', 'Total', 'amount_usd', 'expense_amount'],
    'Currency': ['Currency', 'CCY', 'currency_code'],
}


def resolve_col(headers, canonical):
    for alias in COLUMN_ALIASES.get(canonical, [canonical]):
        if alias in headers:
            return alias
    return None


def parse_travel_csv(file_content: bytes, batch_id, org_id) -> dict:
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

    for row_num, row in enumerate(reader, start=2):
        date_raw = row.get(col.get('Date') or '', '')
        travel_date = parse_date(date_raw)
        if not travel_date:
            errors.append((row_num, f"Cannot parse date: '{date_raw}'"))
            continue

        category_raw = row.get(col.get('Category') or '', 'ground_transport')
        category = normalise_category(category_raw)

        is_suspicious = False
        suspicion_reason = ''

        trip_id = row.get(col.get('Trip ID') or '', '').strip()
        employee = row.get(col.get('Employee') or '', '').strip()
        origin = row.get(col.get('Origin') or '', '').strip().upper()
        destination = row.get(col.get('Destination') or '', '').strip().upper()
        cabin_raw = row.get(col.get('Cabin') or '', 'economy').strip()
        cabin = normalise_cabin(cabin_raw)

        qty = Decimal('0')
        normalised_qty = Decimal('0')
        original_unit = ''
        normalised_unit = ''
        co2e = Decimal('0')
        description = ''

        if category == 'flight':
            # Try to get distance; if not, compute from airport codes
            dist_raw = row.get(col.get('Distance') or '', '').strip()
            dist_unit = row.get(col.get('Distance Unit') or '', 'km').strip().lower()
            distance_km = parse_decimal(dist_raw)

            if distance_km is None or distance_km <= 0:
                # Try computing from airport codes
                if origin in AIRPORT_COORDS and destination in AIRPORT_COORDS:
                    distance_km = haversine_km(AIRPORT_COORDS[origin], AIRPORT_COORDS[destination])
                else:
                    is_suspicious = True
                    suspicion_reason = f"No distance and unknown airport codes '{origin}' / '{destination}'"
                    distance_km = Decimal('1000')  # placeholder

            if dist_unit == 'miles':
                distance_km = (distance_km * Decimal('1.60934')).quantize(Decimal('0.01'))

            ef = FLIGHT_EF.get(cabin, FLIGHT_EF['economy'])
            # DEFRA radiative forcing uplift factor for flights: 1.891
            co2e = (distance_km * ef * Decimal('1.891')).quantize(Decimal('0.0001'))

            qty = distance_km
            normalised_qty = distance_km
            original_unit = dist_unit or 'km'
            normalised_unit = 'km'
            description = f"Flight {origin} → {destination} ({cabin})"

        elif category == 'hotel':
            nights_raw = row.get(col.get('Nights') or '', '1').strip()
            nights = parse_decimal(nights_raw) or Decimal('1')
            co2e = (nights * HOTEL_EF_PER_NIGHT).quantize(Decimal('0.0001'))
            qty = nights
            normalised_qty = nights
            original_unit = 'nights'
            normalised_unit = 'nights'
            description = f"Hotel — {destination or 'unknown city'} ({int(nights)} night{'s' if nights != 1 else ''})"

        elif category == 'ground_transport':
            dist_raw = row.get(col.get('Distance') or '', '').strip()
            dist_unit = row.get(col.get('Distance Unit') or '', 'km').strip().lower()
            distance_km = parse_decimal(dist_raw)

            sub_type = (category_raw or '').lower()
            if any(k in sub_type for k in ['train', 'rail', 'metro']):
                ef = TRAIN_EF_PER_KM
                desc_prefix = 'Rail'
            elif any(k in sub_type for k in ['car', 'rental', 'hire', 'mileage']):
                ef = CAR_EF_PER_KM
                desc_prefix = 'Car'
            else:
                ef = TAXI_EF_PER_KM
                desc_prefix = 'Taxi/Rideshare'

            if distance_km is None or distance_km <= 0:
                # Fallback: try to estimate from amount (rough proxy)
                amount_raw = row.get(col.get('Amount') or '', '').strip()
                amount = parse_decimal(amount_raw)
                if amount and amount > 0:
                    # ~₹15/km for taxi in India — rough
                    distance_km = (amount / Decimal('15')).quantize(Decimal('0.01'))
                    is_suspicious = True
                    suspicion_reason = "Distance estimated from cost — not reliable"
                else:
                    is_suspicious = True
                    suspicion_reason = "No distance data"
                    distance_km = Decimal('0')

            if dist_unit == 'miles':
                distance_km = (distance_km * Decimal('1.60934')).quantize(Decimal('0.01'))

            co2e = (distance_km * ef).quantize(Decimal('0.0001'))
            qty = distance_km
            normalised_qty = distance_km
            original_unit = dist_unit or 'km'
            normalised_unit = 'km'
            description = f"{desc_prefix} — {origin or ''} to {destination or 'unknown'}"

        if employee:
            description = f"{description} ({employee})"

        records.append({
            'organisation_id': org_id,
            'batch_id': batch_id,
            'scope': '3',
            'category': category,
            'activity_date': travel_date,
            'description': description,
            'quantity': qty,
            'original_unit': original_unit,
            'normalised_unit': normalised_unit,
            'normalised_quantity': normalised_qty,
            'co2e_kg': co2e,
            'source_row_id': trip_id,
            'source_plant_code': '',
            'source_vendor': employee,
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
