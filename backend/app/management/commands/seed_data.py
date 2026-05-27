from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from app.models import Organization, PlantLookup, AirportLookup

class Command(BaseCommand):
    help = "Seeds initial database lookup values for ESG Ingest"

    def handle(self, *args, **options):
        self.stdout.write("Seeding data...")

        # 1. Create Organization
        org, created = Organization.objects.get_or_create(
            name="Breathe ESG Client Corp"
        )
        if created:
            self.stdout.write(f"Created Organization: '{org.name}'")
        else:
            self.stdout.write(f"Organization '{org.name}' already exists.")

        # 2. Create Plant Codes
        plants = [
            {
                'plant_code': 'DE01',
                'friendly_name': 'Frankfurt Manufacturing Hub',
                'location': 'Frankfurt, Germany',
                'electricity_grid_emission_factor': Decimal('0.3500')
            },
            {
                'plant_code': 'US03',
                'friendly_name': 'Houston Assembly Plant',
                'location': 'Houston, Texas, USA',
                'electricity_grid_emission_factor': Decimal('0.3800')
            },
            {
                'plant_code': 'IN12',
                'friendly_name': 'Bangalore Logistics Center',
                'location': 'Bangalore, India',
                'electricity_grid_emission_factor': Decimal('0.7100')
            }
        ]

        for p in plants:
            plant_obj, created = PlantLookup.objects.get_or_create(
                organization=org,
                plant_code=p['plant_code'],
                defaults={
                    'friendly_name': p['friendly_name'],
                    'location': p['location'],
                    'electricity_grid_emission_factor': p['electricity_grid_emission_factor']
                }
            )
            if created:
                self.stdout.write(f"Created Plant Lookup: {p['plant_code']}")

        # 3. Create Airport Coordinates
        airports = [
            {
                'iata_code': 'JFK',
                'airport_name': 'John F. Kennedy International Airport',
                'city': 'New York',
                'country': 'USA',
                'latitude': Decimal('40.639751'),
                'longitude': Decimal('-73.778925')
            },
            {
                'iata_code': 'LAX',
                'airport_name': 'Los Angeles International Airport',
                'city': 'Los Angeles',
                'country': 'USA',
                'latitude': Decimal('33.941589'),
                'longitude': Decimal('-118.408530')
            },
            {
                'iata_code': 'LHR',
                'airport_name': 'London Heathrow Airport',
                'city': 'London',
                'country': 'UK',
                'latitude': Decimal('51.470022'),
                'longitude': Decimal('-0.454295')
            },
            {
                'iata_code': 'CDG',
                'airport_name': 'Charles de Gaulle Airport',
                'city': 'Paris',
                'country': 'France',
                'latitude': Decimal('49.009724'),
                'longitude': Decimal('2.547900')
            },
            {
                'iata_code': 'FRA',
                'airport_name': 'Frankfurt Airport',
                'city': 'Frankfurt',
                'country': 'Germany',
                'latitude': Decimal('50.037903'),
                'longitude': Decimal('8.562152')
            },
            {
                'iata_code': 'DEL',
                'airport_name': 'Indira Gandhi International Airport',
                'city': 'Delhi',
                'country': 'India',
                'latitude': Decimal('28.556162'),
                'longitude': Decimal('77.100281')
            },
            {
                'iata_code': 'BOM',
                'airport_name': 'Chhatrapati Shivaji Maharaj Airport',
                'city': 'Mumbai',
                'country': 'India',
                'latitude': Decimal('19.089560'),
                'longitude': Decimal('72.865614')
            },
            {
                'iata_code': 'SIN',
                'airport_name': 'Changi Airport',
                'city': 'Singapore',
                'country': 'Singapore',
                'latitude': Decimal('1.364420'),
                'longitude': Decimal('103.991107')
            },
            {
                'iata_code': 'DXB',
                'airport_name': 'Dubai International Airport',
                'city': 'Dubai',
                'country': 'UAE',
                'latitude': Decimal('25.253200'),
                'longitude': Decimal('55.365700')
            }
        ]

        for ap in airports:
            ap_obj, created = AirportLookup.objects.get_or_create(
                iata_code=ap['iata_code'],
                defaults={
                    'airport_name': ap['airport_name'],
                    'city': ap['city'],
                    'country': ap['country'],
                    'latitude': ap['latitude'],
                    'longitude': ap['longitude']
                }
            )
            if created:
                self.stdout.write(f"Created Airport Lookup: {ap['iata_code']}")

        # 4. Create Superuser
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@breatheesg.com',
                password='admin123'
            )
            self.stdout.write("Created superuser: admin (password: admin123)")
        else:
            self.stdout.write("Superuser 'admin' already exists.")

        self.stdout.write(self.style.SUCCESS("Database seeding completed!"))
