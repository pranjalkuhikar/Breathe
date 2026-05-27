import math
import csv
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.db.models import Avg
from app.models import PlantLookup, AirportLookup, ActivityRecord
from app.repositories.queries import ActivityRepository

# Pure Haversine formula
def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers

    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c

# Pure Date Parser
def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d.%m.%Y', '%m/%d/%Y', '%Y%m%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    try:
        return datetime.fromtimestamp(float(date_str)).date()
    except (ValueError, TypeError):
        pass
        
    raise ValueError(f"Could not parse date string: '{date_str}'")

class EsgIngestionService:
    @staticmethod
    def process_sap_batch(batch, csv_reader):
        headers = [h.strip() for h in csv_reader.fieldnames]
        
        def find_col(aliases):
            for alias in aliases:
                for h in headers:
                    if h.lower() == alias.lower():
                        return h
            return None

        col_plant = find_col(['werks', 'werk', 'plant', 'plant_code', 'plant code'])
        col_material = find_col(['matnr', 'material', 'materialnummer', 'material_name', 'item'])
        col_qty = find_col(['menge', 'menge/quantity', 'quantity', 'qty', 'menge_qty'])
        col_unit = find_col(['meins', 'einheit', 'unit', 'meins_unit', 'uom'])
        col_date = find_col(['budat', 'buchungsdatum', 'posting_date', 'date', 'posting date', 'belegdatum'])

        if not all([col_plant, col_material, col_qty, col_unit, col_date]):
            missing = [k for k, v in {
                'Plant (WERKS)': col_plant,
                'Material (MATNR)': col_material,
                'Quantity (MENGE)': col_qty,
                'Unit (MEINS)': col_unit,
                'Date (BUDAT)': col_date
            }.items() if not v]
            raise ValueError(f"Missing required columns in SAP file: {', '.join(missing)}")

        success_count = 0
        failure_count = 0

        for idx, row in enumerate(csv_reader, start=1):
            raw_row = dict(row)
            try:
                plant_code = raw_row[col_plant].strip()
                material = raw_row[col_material].strip()
                qty_str = raw_row[col_qty].replace(',', '').strip()
                unit = raw_row[col_unit].strip()
                date_str = raw_row[col_date].strip()

                if not plant_code or not material or not qty_str or not unit or not date_str:
                    raise ValueError("Empty required field(s) in SAP record.")

                try:
                    qty = Decimal(qty_str)
                except Exception:
                    raise ValueError(f"Invalid numeric quantity: '{qty_str}'")

                parsed_date = parse_date(date_str)

                mat_lower = material.lower()
                category = "Unknown SAP Material"
                scope = "1"
                factor = Decimal("0.0")
                std_unit = ""

                if "diesel" in mat_lower or "dieselkraftstoff" in mat_lower:
                    category = "Diesel Combustion"
                    factor = Decimal("2.68")
                    std_unit = "L"
                elif "gas" in mat_lower or "erdgas" in mat_lower or "natural gas" in mat_lower:
                    category = "Natural Gas Combustion"
                    factor = Decimal("2.02")
                    std_unit = "M3"
                elif "oil" in mat_lower or "heizöl" in mat_lower or "fuel oil" in mat_lower:
                    category = "Fuel Oil Combustion"
                    factor = Decimal("2.96")
                    std_unit = "L"
                else:
                    raise ValueError(f"Unrecognized fuel material type: '{material}'")

                # Normalize volumetric units
                norm_qty = qty
                unit_lower = unit.lower()
                flag_reasons = []

                if std_unit == "L":
                    if unit_lower in ('gal', 'usg', 'gallon', 'gallons'):
                        norm_qty = qty * Decimal("3.78541")
                        flag_reasons.append(f"Converted unit {unit} to Liters")
                    elif unit_lower in ('m3', 'cubic meter', 'cubic meters'):
                        norm_qty = qty * Decimal("1000")
                        flag_reasons.append(f"Converted unit {unit} to Liters")
                    elif unit_lower in ('l', 'lit', 'litre', 'liters', 'lts'):
                        pass
                    else:
                        flag_reasons.append(f"Unexpected unit '{unit}' for volumetric fuel. Kept as-is.")
                elif std_unit == "M3":
                    if unit_lower in ('l', 'lit', 'litre', 'liters'):
                        norm_qty = qty / Decimal("1000")
                        flag_reasons.append(f"Converted unit {unit} to Cubic Meters")
                    elif unit_lower in ('kwh', 'kilowatt hours'):
                        norm_qty = qty
                        std_unit = "kWh"
                        factor = Decimal("0.18")
                        flag_reasons.append(f"Using kWh energy equivalence for natural gas")
                    elif unit_lower in ('m3', 'm³'):
                        pass
                    else:
                        flag_reasons.append(f"Unexpected unit '{unit}' for gas fuel. Kept as-is.")

                # Plant code Lookup
                try:
                    plant_lookup = PlantLookup.objects.get(
                        organization=batch.organization, 
                        plant_code=plant_code
                    )
                    facility_name = plant_lookup.friendly_name
                except PlantLookup.DoesNotExist:
                    facility_name = f"Unknown SAP Plant ({plant_code})"
                    flag_reasons.append(f"Plant code '{plant_code}' not found in organization lookup")

                # Carbon Calculation
                co2e_kg = norm_qty * factor

                # Outlier validation checks
                if norm_qty <= 0:
                    flag_reasons.append("Non-positive quantity detected.")
                
                six_months_ago = parsed_date - timedelta(days=180)
                historic_avg = ActivityRecord.objects.filter(
                    organization=batch.organization,
                    facility_name=facility_name,
                    category=category,
                    transaction_date__gte=six_months_ago
                ).aggregate(avg_qty=Avg('normalized_quantity'))['avg_qty']

                if historic_avg and norm_qty > Decimal(str(historic_avg)) * Decimal("3.0"):
                    flag_reasons.append(f"Quantity is 3x higher than historic 6-month average ({historic_avg:.2f} {std_unit})")

                status = 'FLAGGED' if flag_reasons else 'PENDING'

                # Delegate database saving to the Repository Layer
                ActivityRepository.create_record(
                    organization=batch.organization,
                    batch=batch,
                    row_index=idx,
                    scope=scope,
                    category=category,
                    description=f"Ingested from SAP Export (Material: {material})",
                    facility_name=facility_name,
                    raw_quantity=qty,
                    raw_unit=unit,
                    normalized_quantity=norm_qty,
                    normalized_unit=std_unit,
                    co2e_kg=co2e_kg,
                    status=status,
                    flag_reasons=flag_reasons,
                    transaction_date=parsed_date,
                    raw_data=raw_row
                )
                success_count += 1
            except Exception as e:
                # Delegate logging database error to Repository Layer
                ActivityRepository.create_error(batch, idx, raw_row, str(e))
                failure_count += 1

        batch.total_rows = idx
        batch.successful_rows = success_count
        batch.failed_rows = failure_count
        batch.status = 'PROCESSED' if failure_count == 0 else 'FAILED'
        batch.save()
        return success_count, failure_count

    @staticmethod
    def process_utility_batch(batch, csv_reader):
        headers = [h.strip() for h in csv_reader.fieldnames]

        def find_col(aliases):
            for alias in aliases:
                for h in headers:
                    if h.lower() == alias.lower():
                        return h
            return None

        col_facility = find_col(['facility', 'facility_name', 'facility name', 'meter', 'meter_id', 'plant'])
        col_start = find_col(['start_date', 'billing_start', 'billing start', 'start date', 'from_date'])
        col_end = find_col(['end_date', 'billing_end', 'billing end', 'end date', 'to_date'])
        col_consumption = find_col(['consumption', 'kwh', 'mwh', 'usage', 'quantity'])
        col_unit = find_col(['unit', 'uom', 'einheit'])

        if not all([col_facility, col_start, col_end, col_consumption, col_unit]):
            missing = [k for k, v in {
                'Facility/Meter': col_facility,
                'Start Date': col_start,
                'End Date': col_end,
                'Consumption': col_consumption,
                'Unit': col_unit
            }.items() if not v]
            raise ValueError(f"Missing required columns in Utility file: {', '.join(missing)}")

        success_count = 0
        failure_count = 0

        for idx, row in enumerate(csv_reader, start=1):
            raw_row = dict(row)
            try:
                facility_name = raw_row[col_facility].strip()
                start_str = raw_row[col_start].strip()
                end_str = raw_row[col_end].strip()
                usage_str = raw_row[col_consumption].replace(',', '').strip()
                unit = raw_row[col_unit].strip()

                if not facility_name or not start_str or not end_str or not usage_str or not unit:
                    raise ValueError("Empty required field(s) in Utility record.")

                try:
                    usage = Decimal(usage_str)
                except Exception:
                    raise ValueError(f"Invalid numeric usage: '{usage_str}'")

                parsed_start = parse_date(start_str)
                parsed_end = parse_date(end_str)

                if parsed_start >= parsed_end:
                    raise ValueError(f"Start date ({parsed_start}) cannot be on or after End date ({parsed_end})")

                # Resolve grid factor
                grid_factor = Decimal("0.40")
                plant_lookup = None
                
                plants = PlantLookup.objects.filter(organization=batch.organization)
                for p in plants:
                    if p.plant_code.lower() in facility_name.lower() or p.friendly_name.lower() in facility_name.lower():
                        plant_lookup = p
                        grid_factor = p.electricity_grid_emission_factor
                        break

                # Normalize energy units
                norm_qty = usage
                unit_lower = unit.lower()
                flag_reasons = []

                if unit_lower in ('mwh', 'megawatt hours'):
                    norm_qty = usage * Decimal("1000")
                    flag_reasons.append(f"Normalized {unit} to kWh")
                elif unit_lower in ('kwh', 'kilowatt hours', 'units'):
                    pass
                else:
                    flag_reasons.append(f"Unexpected unit '{unit}' for electricity. Treated as kWh.")

                co2e_kg = norm_qty * grid_factor
                std_unit = "kWh"
                category = "Electricity Grid Consumption"
                scope = "2"

                # Outliers checks
                if norm_qty <= 0:
                    flag_reasons.append("Electricity usage is non-positive.")

                days_diff = (parsed_end - parsed_start).days
                if days_diff > 45:
                    flag_reasons.append(f"Billing period is unusually long ({days_diff} days)")

                if not plant_lookup:
                    flag_reasons.append("No matching organization facility code; applied default global grid factor.")

                six_months_ago = parsed_end - timedelta(days=180)
                historic_avg = ActivityRecord.objects.filter(
                    organization=batch.organization,
                    facility_name=facility_name,
                    category=category,
                    transaction_date__gte=six_months_ago
                ).aggregate(avg_qty=Avg('normalized_quantity'))['avg_qty']

                if historic_avg and norm_qty > Decimal(str(historic_avg)) * Decimal("3.0"):
                    flag_reasons.append(f"Usage is 3x higher than historic 6-month average ({historic_avg:.2f} kWh)")

                status = 'FLAGGED' if flag_reasons else 'PENDING'

                # Delegate saving record to Repository Layer
                ActivityRepository.create_record(
                    organization=batch.organization,
                    batch=batch,
                    row_index=idx,
                    scope=scope,
                    category=category,
                    description=f"Ingested Utility Bill (Meter: {facility_name})",
                    facility_name=plant_lookup.friendly_name if plant_lookup else facility_name,
                    raw_quantity=usage,
                    raw_unit=unit,
                    normalized_quantity=norm_qty,
                    normalized_unit=std_unit,
                    co2e_kg=co2e_kg,
                    status=status,
                    flag_reasons=flag_reasons,
                    transaction_date=parsed_end,
                    raw_data=raw_row
                )
                
                # Ingest billing periods dates in the newly created record
                rec = ActivityRecord.objects.filter(batch=batch, source_row_index=idx).first()
                if rec:
                    rec.billing_start_date = parsed_start
                    rec.billing_end_date = parsed_end
                    rec.save()

                success_count += 1
            except Exception as e:
                ActivityRepository.create_error(batch, idx, raw_row, str(e))
                failure_count += 1

        batch.total_rows = idx
        batch.successful_rows = success_count
        batch.failed_rows = failure_count
        batch.status = 'PROCESSED' if failure_count == 0 else 'FAILED'
        batch.save()
        return success_count, failure_count

    @staticmethod
    def process_travel_batch(batch, csv_reader):
        headers = [h.strip() for h in csv_reader.fieldnames]

        def find_col(aliases):
            for alias in aliases:
                for h in headers:
                    if h.lower() == alias.lower():
                        return h
            return None

        col_category = find_col(['category', 'travel_type', 'type', 'booking_type'])
        col_qty = find_col(['quantity', 'amount', 'nights', 'distance', 'value'])
        col_unit = find_col(['unit', 'uom'])
        col_origin = find_col(['origin', 'departure', 'from', 'airport_from'])
        col_dest = find_col(['destination', 'arrival', 'to', 'airport_to'])
        col_date = find_col(['date', 'booking_date', 'transaction_date', 'travel_date'])
        col_class = find_col(['class', 'cabin_class', 'cabin', 'tier'])
        col_details = find_col(['details', 'hotel_name', 'description'])

        if not all([col_category, col_qty, col_unit, col_date]):
            missing = [k for k, v in {
                'Category': col_category,
                'Quantity': col_qty,
                'Unit': col_unit,
                'Date': col_date
            }.items() if not v]
            raise ValueError(f"Missing required columns in Travel file: {', '.join(missing)}")

        success_count = 0
        failure_count = 0

        for idx, row in enumerate(csv_reader, start=1):
            raw_row = dict(row)
            try:
                travel_type = raw_row[col_category].strip().lower()
                qty_str = raw_row[col_qty].replace(',', '').strip()
                unit = raw_row[col_unit].strip()
                date_str = raw_row[col_date].strip()

                if not travel_type or not qty_str or not unit or not date_str:
                    raise ValueError("Empty required field(s) in Travel record.")

                try:
                    qty = Decimal(qty_str)
                except Exception:
                    raise ValueError(f"Invalid numeric quantity: '{qty_str}'")

                parsed_date = parse_date(date_str)
                cabin_class = raw_row[col_class].strip() if col_class else "Economy"
                detail_desc = raw_row[col_details].strip() if col_details else ""

                flag_reasons = []
                scope = "3"
                category = "Business Travel - Other"
                norm_qty = qty
                std_unit = ""
                co2e_kg = Decimal("0")

                if qty <= 0:
                    flag_reasons.append("Quantity is non-positive.")

                if "flight" in travel_type or "air" in travel_type:
                    category = "Business Travel (Flights)"
                    std_unit = "km"
                    
                    origin_iata = raw_row[col_origin].strip().upper() if col_origin else ""
                    destination_iata = raw_row[col_dest].strip().upper() if col_dest else ""
                    
                    calculated_distance = False
                    
                    if origin_iata and destination_iata:
                        try:
                            orig_ap = AirportLookup.objects.get(iata_code=origin_iata)
                            dest_ap = AirportLookup.objects.get(iata_code=destination_iata)
                            
                            dist_km = calculate_haversine_distance(
                                orig_ap.latitude, orig_ap.longitude,
                                dest_ap.latitude, dest_ap.longitude
                            )
                            norm_qty = Decimal(str(round(dist_km, 2)))
                            calculated_distance = True
                            flag_reasons.append(f"Computed flight distance dynamically ({origin_iata} to {destination_iata}: {norm_qty} km)")
                        except AirportLookup.DoesNotExist:
                            flag_reasons.append(f"Airport lookup failed for {origin_iata} or {destination_iata}")

                    if not calculated_distance:
                        if unit.lower() in ('mi', 'mile', 'miles'):
                            norm_qty = qty * Decimal("1.60934")
                            flag_reasons.append(f"Normalized flight distance from Miles to km")
                        elif unit.lower() in ('km', 'kilometers'):
                            norm_qty = qty
                        else:
                            norm_qty = qty
                            flag_reasons.append(f"Flight distance has unknown unit '{unit}'. Defaulted to km.")
                    
                    is_short = norm_qty < Decimal("500")
                    is_biz = "business" in cabin_class.lower() or "first" in cabin_class.lower()
                    
                    if is_short:
                        factor = Decimal("0.22") if is_biz else Decimal("0.15")
                    else:
                        factor = Decimal("0.29") if is_biz else Decimal("0.10")
                        
                    co2e_kg = norm_qty * factor
                    
                elif "hotel" in travel_type or "stay" in travel_type or "lodging" in travel_type:
                    category = "Business Travel (Hotels)"
                    std_unit = "nights"
                    
                    if unit.lower() not in ('night', 'nights', 'days'):
                        flag_reasons.append(f"Unexpected hotel unit '{unit}' normalized to nights.")
                    
                    factor = Decimal("20.4")
                    co2e_kg = norm_qty * factor
                    
                elif any(g in travel_type for g in ('car', 'rental', 'taxi', 'ground', 'train')):
                    category = "Business Travel (Ground)"
                    std_unit = "km"
                    
                    if unit.lower() in ('mi', 'mile', 'miles'):
                        norm_qty = qty * Decimal("1.60934")
                        flag_reasons.append(f"Normalized ground travel from Miles to km")
                    elif unit.lower() in ('km', 'kilometers'):
                        norm_qty = qty
                    elif unit.lower() in ('l', 'lit', 'gal', 'gallons'):
                        norm_qty = qty * Decimal("12.5")
                        flag_reasons.append(f"Converted fuel volume to estimated kilometers")
                    else:
                        flag_reasons.append(f"Unknown ground travel unit '{unit}'")
                    
                    factor = Decimal("0.17")
                    co2e_kg = norm_qty * factor
                else:
                    raise ValueError(f"Unrecognized travel type category: '{travel_type}'")

                if norm_qty > Decimal("5000") and std_unit == "km":
                    flag_reasons.append("Unusually long single travel leg (> 5000 km)")

                status = 'FLAGGED' if flag_reasons else 'PENDING'

                # Delegate saving record to Repository Layer
                ActivityRepository.create_record(
                    organization=batch.organization,
                    batch=batch,
                    row_index=idx,
                    scope=scope,
                    category=category,
                    description=detail_desc or f"Business Travel ({travel_type.capitalize()})",
                    facility_name="Corporate Travel",
                    raw_quantity=qty,
                    raw_unit=unit,
                    normalized_quantity=norm_qty,
                    normalized_unit=std_unit,
                    co2e_kg=co2e_kg,
                    status=status,
                    flag_reasons=flag_reasons,
                    transaction_date=parsed_date,
                    raw_data=raw_row
                )
                success_count += 1
            except Exception as e:
                ActivityRepository.create_error(batch, idx, raw_row, str(e))
                failure_count += 1

        batch.total_rows = idx
        batch.successful_rows = success_count
        batch.failed_rows = failure_count
        batch.status = 'PROCESSED' if failure_count == 0 else 'FAILED'
        batch.save()
        return success_count, failure_count
