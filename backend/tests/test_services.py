import csv
import io
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from app.models import Organization, PlantLookup, AirportLookup, IngestionBatch, ActivityRecord, AuditLog
from app.services.ingestion import calculate_haversine_distance, EsgIngestionService

class EsgInfrastuctureTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.admin = User.objects.create_superuser(username="admin", password="password", email="admin@test.com")
        
        # Seed Plant Code
        self.plant = PlantLookup.objects.create(
            organization=self.org,
            plant_code="DE01",
            friendly_name="Frankfurt Hub",
            location="Frankfurt, Germany",
            electricity_grid_emission_factor=Decimal("0.3500")
        )
        
        # Seed Airport Coordinates
        self.jfk = AirportLookup.objects.create(
            iata_code="JFK",
            airport_name="John F. Kennedy",
            city="New York",
            country="USA",
            latitude=Decimal("40.639751"),
            longitude=Decimal("-73.778925")
        )
        
        self.lax = AirportLookup.objects.create(
            iata_code="LAX",
            airport_name="Los Angeles Airport",
            city="Los Angeles",
            country="USA",
            latitude=Decimal("33.941589"),
            longitude=Decimal("-118.408530")
        )

    def test_haversine_distance(self):
        # JFK to LAX distance is roughly 3970-3980 km.
        dist = calculate_haversine_distance(
            self.jfk.latitude, self.jfk.longitude,
            self.lax.latitude, self.lax.longitude
        )
        self.assertGreater(dist, 3900)
        self.assertLess(dist, 4000)

    def test_sap_ingestion_and_normalization(self):
        # Create a batch
        batch = IngestionBatch.objects.create(
            organization=self.org,
            source_type="SAP",
            file_name="sap_test.csv"
        )
        
        csv_data = (
            "WERKS,MATNR,MENGE,MEINS,BUDAT\n"
            "DE01,Diesel fuel,100,GAL,2026-05-15\n"  # 100 Gallons Diesel
            "DE01,Erdgas (Gas),50,M3,2026-05-16\n"    # 50 M3 Natural Gas
        )
        csv_file = io.StringIO(csv_data)
        csv_reader = csv.DictReader(csv_file)
        
        success, failure = EsgIngestionService.process_sap_batch(batch, csv_reader)
        
        self.assertEqual(success, 2)
        self.assertEqual(failure, 0)
        self.assertEqual(ActivityRecord.objects.count(), 2)
        
        # Verify Diesel Normalization (100 gal * 3.78541 = 378.541 L)
        diesel_rec = ActivityRecord.objects.get(category="Diesel Combustion")
        self.assertEqual(diesel_rec.scope, "1")
        self.assertAlmostEqual(float(diesel_rec.normalized_quantity), 378.541, places=2)
        self.assertEqual(diesel_rec.normalized_unit, "L")
        # 378.541 L * 2.68 kg/L = 1014.49 kg CO2e
        self.assertAlmostEqual(float(diesel_rec.co2e_kg), 378.541 * 2.68, places=2)
        
        # Verify natural gas (50 M3 * 2.02 = 101 kg CO2e)
        gas_rec = ActivityRecord.objects.get(category="Natural Gas Combustion")
        self.assertEqual(float(gas_rec.normalized_quantity), 50.0)
        self.assertEqual(gas_rec.normalized_unit, "M3")
        self.assertEqual(float(gas_rec.co2e_kg), 50.0 * 2.02)

    def test_utility_ingestion_and_billing_periods(self):
        batch = IngestionBatch.objects.create(
            organization=self.org,
            source_type="UTILITY",
            file_name="utility_test.csv"
        )
        
        csv_data = (
            "Facility,Start Date,End Date,Usage,Unit\n"
            "Frankfurt Hub,2026-04-01,2026-05-01,1.5,MWh\n"  # 1.5 MWh = 1500 kWh
        )
        csv_file = io.StringIO(csv_data)
        csv_reader = csv.DictReader(csv_file)
        
        success, failure = EsgIngestionService.process_utility_batch(batch, csv_reader)
        
        self.assertEqual(success, 1)
        self.assertEqual(ActivityRecord.objects.count(), 1)
        
        rec = ActivityRecord.objects.first()
        self.assertEqual(rec.scope, "2")
        self.assertEqual(rec.category, "Electricity Grid Consumption")
        self.assertEqual(float(rec.normalized_quantity), 1500.0)
        self.assertEqual(rec.normalized_unit, "kWh")
        # 1500 kWh * 0.35 kg/kWh = 525 kg CO2e
        self.assertEqual(float(rec.co2e_kg), 1500.0 * 0.35)

    def test_travel_ingestion_airport_distance(self):
        batch = IngestionBatch.objects.create(
            organization=self.org,
            source_type="TRAVEL",
            file_name="travel_test.csv"
        )
        
        csv_data = (
            "Category,Quantity,Unit,Origin,Destination,Date,Class,Details\n"
            "Flight,1,trip,JFK,LAX,2026-05-15,Economy,NYC to LA flight\n"  # Dynamic distance
            "Hotel,3,nights,,,2026-05-15,Economy,Hotel stay\n"              # 3 nights hotel
        )
        csv_file = io.StringIO(csv_data)
        csv_reader = csv.DictReader(csv_file)
        
        success, failure = EsgIngestionService.process_travel_batch(batch, csv_reader)
        
        self.assertEqual(success, 2)
        self.assertEqual(failure, 0)
        
        flight_rec = ActivityRecord.objects.get(category="Business Travel (Flights)")
        self.assertEqual(flight_rec.scope, "3")
        self.assertEqual(flight_rec.normalized_unit, "km")
        # Distance JFK-LAX is > 3900 km. It is a long-haul flight (>= 500 km) and economy (factor 0.10)
        self.assertGreater(float(flight_rec.normalized_quantity), 3900)
        self.assertAlmostEqual(float(flight_rec.co2e_kg), float(flight_rec.normalized_quantity) * 0.10, places=2)
        
        hotel_rec = ActivityRecord.objects.get(category="Business Travel (Hotels)")
        self.assertEqual(float(hotel_rec.normalized_quantity), 3.0)
        self.assertEqual(hotel_rec.normalized_unit, "nights")
        # 3 nights * 20.4 kg/night = 61.2 kg CO2e
        self.assertAlmostEqual(float(hotel_rec.co2e_kg), 61.2)

    def test_outlier_flagging_engine(self):
        # Inject historic average data (e.g. historic is 100 L)
        for i in range(5):
            ActivityRecord.objects.create(
                organization=self.org,
                batch=IngestionBatch.objects.create(organization=self.org, source_type="SAP"),
                source_row_index=1,
                scope="1",
                category="Diesel Combustion",
                facility_name="Frankfurt Hub",
                raw_quantity=Decimal("100.00"),
                raw_unit="L",
                normalized_quantity=Decimal("100.00"),
                normalized_unit="L",
                co2e_kg=Decimal("268.00"),
                transaction_date=date(2026, 4, 1),
                raw_data={}
            )
            
        # Ingest a huge spike (1000 L diesel, which is 10x the historic average of 100 L)
        batch = IngestionBatch.objects.create(
            organization=self.org,
            source_type="SAP",
            file_name="sap_outlier.csv"
        )
        csv_data = (
            "WERKS,MATNR,MENGE,MEINS,BUDAT\n"
            "DE01,Diesel fuel,1000,L,2026-05-15\n"
        )
        csv_file = io.StringIO(csv_data)
        csv_reader = csv.DictReader(csv_file)
        
        EsgIngestionService.process_sap_batch(batch, csv_reader)
        
        rec = ActivityRecord.objects.filter(batch=batch).first()
        self.assertEqual(rec.status, "FLAGGED")
        self.assertTrue(any("3x higher" in reason for reason in rec.flag_reasons))

    def test_audit_trail_creation(self):
        batch = IngestionBatch.objects.create(
            organization=self.org,
            source_type="SAP",
            file_name="sap_audit.csv"
        )
        csv_data = (
            "WERKS,MATNR,MENGE,MEINS,BUDAT\n"
            "DE01,Diesel fuel,100,L,2026-05-15\n"
        )
        csv_file = io.StringIO(csv_data)
        csv_reader = csv.DictReader(csv_file)
        
        EsgIngestionService.process_sap_batch(batch, csv_reader)
        
        rec = ActivityRecord.objects.filter(batch=batch).first()
        self.assertTrue(AuditLog.objects.filter(activity_record=rec, action="CREATE").exists())
