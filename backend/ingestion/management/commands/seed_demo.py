"""
Creates a demo analyst user and seeds realistic sample data across all three source types.
Run: python manage.py seed_demo
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from ingestion.models import Organisation, UserProfile, IngestionBatch, EmissionRecord
from decimal import Decimal
from datetime import date


SAP_RECORDS = [
    {'date': date(2024, 1, 5),  'desc': 'Diesel - HSD Diesel',                'qty': 2500,  'unit': 'L',   'nqty': 2500,    'nunit': 'L',  'co2e': 6702.0,    'plant': 'Mumbai Plant',    'susp': False, 'reason': ''},
    {'date': date(2024, 1, 18), 'desc': 'Diesel - HSD Diesel',                'qty': 3100,  'unit': 'L',   'nqty': 3100,    'nunit': 'L',  'co2e': 8310.4,    'plant': 'Mumbai Plant',    'susp': False, 'reason': ''},
    {'date': date(2024, 2, 3),  'desc': 'Petrol - Mogas 91',                  'qty': 1800,  'unit': 'L',   'nqty': 1800,    'nunit': 'L',  'co2e': 4159.4,    'plant': 'Delhi Warehouse', 'susp': False, 'reason': ''},
    {'date': date(2024, 2, 14), 'desc': 'LPG - Liquefied Petroleum Gas',      'qty': 500,   'unit': 'KG',  'nqty': 500,     'nunit': 'KG', 'co2e': 777.7,     'plant': 'Chennai Facility','susp': False, 'reason': ''},
    {'date': date(2024, 3, 2),  'desc': 'Diesel - HSD Diesel',                'qty': 4200,  'unit': 'L',   'nqty': 4200,    'nunit': 'L',  'co2e': 11259.3,   'plant': 'Mumbai Plant',    'susp': False, 'reason': ''},
    {'date': date(2024, 3, 20), 'desc': 'Natural Gas - CNG',                  'qty': 1200,  'unit': 'KG',  'nqty': 1200,    'nunit': 'KG', 'co2e': 2448.2,    'plant': 'Pune Office',     'susp': False, 'reason': ''},
    {'date': date(2024, 4, 7),  'desc': 'Diesel - HSD Diesel',                'qty': 2900,  'unit': 'L',   'nqty': 2900,    'nunit': 'L',  'co2e': 7774.3,    'plant': 'Delhi Warehouse', 'susp': False, 'reason': ''},
    {'date': date(2024, 4, 15), 'desc': 'Unknown Material - fuel type unclear','qty': 800,   'unit': 'GAL', 'nqty': 3028.3,  'nunit': 'L',  'co2e': 8113.3,    'plant': 'Mumbai Plant',    'susp': True,  'reason': 'Fuel type inferred by fallback - description unclear'},
    {'date': date(2024, 5, 3),  'desc': 'Diesel - HSD Diesel',                'qty': 67000, 'unit': 'L',   'nqty': 67000,   'nunit': 'L',  'co2e': 179613.6,  'plant': 'Chennai Facility','susp': True,  'reason': 'Quantity > 50,000 L in single row'},
    {'date': date(2024, 5, 20), 'desc': 'Petrol - Mogas 91',                  'qty': 2100,  'unit': 'L',   'nqty': 2100,    'nunit': 'L',  'co2e': 4852.6,    'plant': 'Pune Office',     'susp': False, 'reason': ''},
    {'date': date(2024, 6, 1),  'desc': 'Diesel - HSD Diesel',                'qty': 3300,  'unit': 'L',   'nqty': 3300,    'nunit': 'L',  'co2e': 8846.6,    'plant': 'Mumbai Plant',    'susp': False, 'reason': ''},
    {'date': date(2024, 6, 22), 'desc': 'LPG - Liquefied Petroleum Gas',      'qty': 600,   'unit': 'KG',  'nqty': 600,     'nunit': 'KG', 'co2e': 933.2,     'plant': 'Delhi Warehouse', 'susp': False, 'reason': ''},
]

UTILITY_RECORDS = [
    {'date': date(2024, 1, 1), 'desc': 'Electricity - Mumbai Plant Jan 2024 [HT Industrial]',    'qty': 185000, 'unit': 'kWh', 'nqty': 185000,    'co2e': 132460.0,   'meter': 'MTR-1001', 'facility': 'Mumbai Plant',    'susp': False, 'reason': ''},
    {'date': date(2024, 2, 1), 'desc': 'Electricity - Mumbai Plant Feb 2024 [HT Industrial]',    'qty': 178000, 'unit': 'kWh', 'nqty': 178000,    'co2e': 127448.0,   'meter': 'MTR-1001', 'facility': 'Mumbai Plant',    'susp': False, 'reason': ''},
    {'date': date(2024, 3, 1), 'desc': 'Electricity - Mumbai Plant Mar 2024 [HT Industrial]',    'qty': 192000, 'unit': 'kWh', 'nqty': 192000,    'co2e': 137472.0,   'meter': 'MTR-1001', 'facility': 'Mumbai Plant',    'susp': False, 'reason': ''},
    {'date': date(2024, 1, 1), 'desc': 'Electricity - Delhi Warehouse Jan 2024 [LT Commercial]', 'qty': 42000,  'unit': 'kWh', 'nqty': 42000,     'co2e': 30072.0,    'meter': 'DLW-2002', 'facility': 'Delhi Warehouse', 'susp': False, 'reason': ''},
    {'date': date(2024, 2, 1), 'desc': 'Electricity - Delhi Warehouse Feb 2024 [LT Commercial]', 'qty': 39500,  'unit': 'kWh', 'nqty': 39500,     'co2e': 28282.0,    'meter': 'DLW-2002', 'facility': 'Delhi Warehouse', 'susp': False, 'reason': ''},
    {'date': date(2024, 3, 1), 'desc': 'Electricity - Delhi Warehouse Mar 2024 [LT Commercial]', 'qty': 44000,  'unit': 'kWh', 'nqty': 44000,     'co2e': 31504.0,    'meter': 'DLW-2002', 'facility': 'Delhi Warehouse', 'susp': False, 'reason': ''},
    {'date': date(2024, 1, 1), 'desc': 'Electricity - Chennai Facility Jan 2024 [HT Industrial]','qty': 98000,  'unit': 'kWh', 'nqty': 98000,     'co2e': 70168.0,    'meter': 'CHN-3003', 'facility': 'Chennai Facility','susp': False, 'reason': ''},
    {'date': date(2024, 2, 1), 'desc': 'Electricity - Chennai Facility Feb 2024 [HT Industrial]','qty': 95000,  'unit': 'kWh', 'nqty': 95000,     'co2e': 68020.0,    'meter': 'CHN-3003', 'facility': 'Chennai Facility','susp': False, 'reason': ''},
    {'date': date(2024, 1, 5), 'desc': 'Electricity - Pune Office Jan 2024 [LT Commercial]',     'qty': 21000,  'unit': 'kWh', 'nqty': 21000,     'co2e': 15036.0,    'meter': 'PNQ-4004', 'facility': 'Pune Office',     'susp': True,  'reason': 'Overlapping billing period with another row'},
    {'date': date(2024, 4, 1), 'desc': 'Electricity - Mumbai Plant Apr 2024 [HT Industrial]',    'qty': 201000, 'unit': 'MWh', 'nqty': 201000000, 'co2e': 143916000.0,'meter': 'MTR-1001', 'facility': 'Mumbai Plant',    'susp': True,  'reason': 'Consumption > 1,000,000 kWh - verify this is correct'},
]

TRAVEL_RECORDS = [
    {'date': date(2024, 1, 10), 'desc': 'Flight BOM to DEL (economy) - Ananya Sharma',  'qty': 1148,  'unit': 'km',     'nqty': 1148,  'nunit': 'km',    'co2e': 337.3,   'cat': 'flight',           'susp': False, 'reason': ''},
    {'date': date(2024, 1, 15), 'desc': 'Flight DEL to LHR (business) - Rohan Mehta',   'qty': 6730,  'unit': 'km',     'nqty': 6730,  'nunit': 'km',    'co2e': 5462.1,  'cat': 'flight',           'susp': False, 'reason': ''},
    {'date': date(2024, 1, 20), 'desc': 'Hotel London 2 nights - Rohan Mehta',           'qty': 2,     'unit': 'nights', 'nqty': 2,     'nunit': 'nights','co2e': 40.0,    'cat': 'hotel',            'susp': False, 'reason': ''},
    {'date': date(2024, 2, 3),  'desc': 'Flight BOM to SIN (economy) - Priya Nair',      'qty': 4358,  'unit': 'km',     'nqty': 4358,  'nunit': 'km',    'co2e': 1280.7,  'cat': 'flight',           'susp': False, 'reason': ''},
    {'date': date(2024, 2, 5),  'desc': 'Hotel Singapore 3 nights - Priya Nair',         'qty': 3,     'unit': 'nights', 'nqty': 3,     'nunit': 'nights','co2e': 60.0,    'cat': 'hotel',            'susp': False, 'reason': ''},
    {'date': date(2024, 2, 12), 'desc': 'Taxi Mumbai to Airport - Amit Kumar',           'qty': 0,     'unit': 'km',     'nqty': 0,     'nunit': 'km',    'co2e': 0.0,     'cat': 'ground_transport', 'susp': True,  'reason': 'Distance estimated from cost - not reliable'},
    {'date': date(2024, 3, 1),  'desc': 'Flight BOM to DEL (economy) - Sneha Patel',     'qty': 1148,  'unit': 'km',     'nqty': 1148,  'nunit': 'km',    'co2e': 337.3,   'cat': 'flight',           'susp': False, 'reason': ''},
    {'date': date(2024, 3, 8),  'desc': 'Flight DEL to JFK (business) - Vikram Singh',   'qty': 11753, 'unit': 'km',     'nqty': 11753, 'nunit': 'km',    'co2e': 9541.7,  'cat': 'flight',           'susp': False, 'reason': ''},
    {'date': date(2024, 3, 10), 'desc': 'Hotel New York 4 nights - Vikram Singh',        'qty': 4,     'unit': 'nights', 'nqty': 4,     'nunit': 'nights','co2e': 80.0,    'cat': 'hotel',            'susp': False, 'reason': ''},
    {'date': date(2024, 3, 18), 'desc': 'Train Mumbai to Pune - Kavya Reddy',            'qty': 312,   'unit': 'km',     'nqty': 312,   'nunit': 'km',    'co2e': 11.5,    'cat': 'ground_transport', 'susp': False, 'reason': ''},
    {'date': date(2024, 4, 5),  'desc': 'Flight BOM to DXB (economy) - Ananya Sharma',  'qty': 1931,  'unit': 'km',     'nqty': 1931,  'nunit': 'km',    'co2e': 567.4,   'cat': 'flight',           'susp': False, 'reason': ''},
    {'date': date(2024, 4, 7),  'desc': 'Hotel Dubai 2 nights - Ananya Sharma',          'qty': 2,     'unit': 'nights', 'nqty': 2,     'nunit': 'nights','co2e': 40.0,    'cat': 'hotel',            'susp': False, 'reason': ''},
    {'date': date(2024, 5, 14), 'desc': 'Car Mumbai to Pune - Rohan Mehta',              'qty': 148,   'unit': 'km',     'nqty': 148,   'nunit': 'km',    'co2e': 28.4,    'cat': 'ground_transport', 'susp': False, 'reason': ''},
    {'date': date(2024, 5, 22), 'desc': 'Flight DEL to BLR (economy) - Priya Nair',     'qty': 1732,  'unit': 'km',     'nqty': 1732,  'nunit': 'km',    'co2e': 509.1,   'cat': 'flight',           'susp': False, 'reason': ''},
]


class Command(BaseCommand):
    help = 'Seed demo user and realistic emission records'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding demo data...')

        # Idempotency - skip if already seeded
        if IngestionBatch.objects.filter(original_filename='MB51_fuel_2024.csv').exists():
            self.stdout.write(self.style.WARNING('Demo data already seeded, skipping.'))
            return

        # Create org
        org, _ = Organisation.objects.get_or_create(
            slug='acme-corp',
            defaults={'name': 'Acme Corp'}
        )

        # Create analyst user
        user, created = User.objects.get_or_create(username='analyst')
        if created:
            user.set_password('password123')
            user.save()
        Token.objects.get_or_create(user=user)

        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user, organisation=org)

        self.stdout.write(f'  User: analyst / password123 | Org: {org.name}')

        # SAP batch
        sap_batch = IngestionBatch.objects.create(
            organisation=org, source_type='sap',
            uploaded_by=user, original_filename='MB51_fuel_2024.csv',
            status='done', row_count=len(SAP_RECORDS), error_count=0,
        )
        for r in SAP_RECORDS:
            EmissionRecord.objects.create(
                organisation=org, batch=sap_batch,
                scope='1', category='fuel',
                activity_date=r['date'], description=r['desc'],
                quantity=Decimal(str(r['qty'])), original_unit=r['unit'],
                normalised_quantity=Decimal(str(r['nqty'])), normalised_unit=r['nunit'],
                co2e_kg=Decimal(str(r['co2e'])),
                source_plant_code=r['plant'],
                is_suspicious=r['susp'], suspicion_reason=r['reason'],
                status='flagged' if r['susp'] else 'pending',
                raw_data={},
            )

        # Utility batch
        util_batch = IngestionBatch.objects.create(
            organisation=org, source_type='utility',
            uploaded_by=user, original_filename='BESCOM_portal_export_Q1_2024.csv',
            status='done', row_count=len(UTILITY_RECORDS), error_count=0,
        )
        for r in UTILITY_RECORDS:
            EmissionRecord.objects.create(
                organisation=org, batch=util_batch,
                scope='2', category='electricity',
                activity_date=r['date'], description=r['desc'],
                quantity=Decimal(str(r['qty'])), original_unit=r['unit'],
                normalised_quantity=Decimal(str(r['nqty'])), normalised_unit='kWh',
                co2e_kg=Decimal(str(r['co2e'])),
                source_meter_id=r['meter'], source_plant_code=r['facility'],
                is_suspicious=r['susp'], suspicion_reason=r['reason'],
                status='flagged' if r['susp'] else 'pending',
                raw_data={},
            )

        # Travel batch
        travel_batch = IngestionBatch.objects.create(
            organisation=org, source_type='travel',
            uploaded_by=user, original_filename='concur_travel_extract_2024_Q1Q2.csv',
            status='done', row_count=len(TRAVEL_RECORDS), error_count=0,
        )
        for r in TRAVEL_RECORDS:
            EmissionRecord.objects.create(
                organisation=org, batch=travel_batch,
                scope='3', category=r['cat'],
                activity_date=r['date'], description=r['desc'],
                quantity=Decimal(str(r['qty'])), original_unit=r['unit'],
                normalised_quantity=Decimal(str(r['nqty'])), normalised_unit=r['nunit'],
                co2e_kg=Decimal(str(r['co2e'])),
                is_suspicious=r['susp'], suspicion_reason=r['reason'],
                status='flagged' if r['susp'] else 'pending',
                raw_data={},
            )

        total = len(SAP_RECORDS) + len(UTILITY_RECORDS) + len(TRAVEL_RECORDS)
        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {total} records across 3 batches.'
        ))
        self.stdout.write('Login: analyst / password123')