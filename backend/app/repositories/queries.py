from decimal import Decimal
from django.utils import timezone
from app.models import ActivityRecord, AuditLog, IngestionError, PlantLookup

class ActivityRepository:
    @staticmethod
    def create_record(organization, batch, row_index, scope, category, description, 
                      facility_name, raw_quantity, raw_unit, normalized_quantity, 
                      normalized_unit, co2e_kg, status, flag_reasons, transaction_date, raw_data):
        """Creates an ActivityRecord and writes its CREATE AuditLog entry."""
        rec = ActivityRecord.objects.create(
            organization=organization,
            batch=batch,
            source_row_index=row_index,
            scope=scope,
            category=category,
            description=description,
            facility_name=facility_name,
            raw_quantity=raw_quantity,
            raw_unit=raw_unit,
            normalized_quantity=normalized_quantity,
            normalized_unit=normalized_unit,
            co2e_kg=co2e_kg,
            status=status,
            flag_reasons=flag_reasons,
            transaction_date=transaction_date,
            raw_data=raw_data
        )

        AuditLog.objects.create(
            activity_record=rec,
            action='CREATE',
            new_values={
                'scope': scope,
                'category': category,
                'normalized_quantity': str(normalized_quantity),
                'normalized_unit': normalized_unit,
                'co2e_kg': str(co2e_kg),
                'status': status,
                'flag_reasons': flag_reasons
            }
        )
        return rec

    @staticmethod
    def create_error(batch, row_index, raw_content, error_message):
        """Creates an IngestionError entry for debugging."""
        return IngestionError.objects.create(
            batch=batch,
            row_index=row_index,
            raw_content=raw_content,
            error_message=error_message
        )

    @staticmethod
    def update_record(record_id, qty_val, category_val, user):
        """Updates record values, triggers recalculations, and writes an UPDATE AuditLog."""
        instance = ActivityRecord.objects.get(id=record_id)
        
        if instance.locked_for_audit:
            raise ValueError('This record is approved & locked for audit. It cannot be modified.')

        previous_data = {
            'normalized_quantity': str(instance.normalized_quantity),
            'co2e_kg': str(instance.co2e_kg),
            'status': instance.status,
            'category': instance.category,
        }

        if qty_val is not None:
            instance.normalized_quantity = Decimal(str(qty_val))
        if category_val:
            instance.category = category_val

        # Recalculate carbon intensity
        factor = Decimal("0.0")
        if instance.category == "Diesel Combustion":
            factor = Decimal("2.68")
        elif instance.category == "Natural Gas Combustion":
            if instance.normalized_unit == "kWh":
                factor = Decimal("0.18")
            else:
                factor = Decimal("2.02")
        elif instance.category == "Fuel Oil Combustion":
            factor = Decimal("2.96")
        elif instance.category == "Electricity Grid Consumption":
            plant_lookup = PlantLookup.objects.filter(
                organization=instance.organization,
                friendly_name=instance.facility_name
            ).first()
            factor = plant_lookup.electricity_grid_emission_factor if plant_lookup else Decimal("0.40")
        elif instance.category == "Business Travel (Flights)":
            is_short = instance.normalized_quantity < Decimal("500")
            cabin = instance.raw_data.get('class', 'Economy') if instance.raw_data else 'Economy'
            is_biz = "business" in cabin.lower() or "first" in cabin.lower()
            if is_short:
                factor = Decimal("0.22") if is_biz else Decimal("0.15")
            else:
                factor = Decimal("0.29") if is_biz else Decimal("0.10")
        elif instance.category == "Business Travel (Hotels)":
            factor = Decimal("20.4")
        elif instance.category == "Business Travel (Ground)":
            factor = Decimal("0.17")

        instance.co2e_kg = instance.normalized_quantity * factor
        
        # Remove flagged status if corrected to positive
        if instance.normalized_quantity > 0:
            instance.flag_reasons = [r for r in instance.flag_reasons if "positive" not in r.lower()]
            if not instance.flag_reasons and instance.status == 'FLAGGED':
                instance.status = 'PENDING'

        instance.save()

        # Write diff to Audit Log
        AuditLog.objects.create(
            activity_record=instance,
            user=user,
            action='UPDATE',
            previous_values=previous_data,
            new_values={
                'normalized_quantity': str(instance.normalized_quantity),
                'co2e_kg': str(instance.co2e_kg),
                'status': instance.status,
                'category': instance.category,
            }
        )
        return instance

    @staticmethod
    def approve_record(record_id, user):
        """Signs off and locks a record for audit compliance."""
        instance = ActivityRecord.objects.get(id=record_id)
        if instance.locked_for_audit:
            raise ValueError('Record already locked')

        previous_status = instance.status
        instance.status = 'APPROVED'
        instance.locked_for_audit = True
        instance.approved_at = timezone.now()
        instance.approved_by = user
        instance.save()

        AuditLog.objects.create(
            activity_record=instance,
            user=user,
            action='APPROVE',
            previous_values={'status': previous_status, 'locked_for_audit': False},
            new_values={'status': 'APPROVED', 'locked_for_audit': True}
        )
        return instance

    @staticmethod
    def flag_record(record_id, reason, user):
        """Flags record with custom reason."""
        instance = ActivityRecord.objects.get(id=record_id)
        if instance.locked_for_audit:
            raise ValueError('Locked records cannot be flagged')

        previous_status = instance.status
        instance.status = 'FLAGGED'
        if reason not in instance.flag_reasons:
            instance.flag_reasons.append(reason)
        instance.save()

        AuditLog.objects.create(
            activity_record=instance,
            user=user,
            action='FLAG',
            previous_values={'status': previous_status, 'flag_reasons': instance.flag_reasons[:-1] if len(instance.flag_reasons) > 1 else []},
            new_values={'status': 'FLAGGED', 'flag_reasons': instance.flag_reasons}
        )
        return instance

    @staticmethod
    def reject_record(record_id, user):
        """Rejects record."""
        instance = ActivityRecord.objects.get(id=record_id)
        if instance.locked_for_audit:
            raise ValueError('Locked records cannot be rejected')

        previous_status = instance.status
        instance.status = 'REJECTED'
        instance.save()

        AuditLog.objects.create(
            activity_record=instance,
            user=user,
            action='REJECT',
            previous_values={'status': previous_status},
            new_values={'status': 'REJECTED'}
        )
        return instance
