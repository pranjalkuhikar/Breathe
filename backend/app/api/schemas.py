from rest_framework import serializers
from django.contrib.auth.models import User
from app.models import (
    Organization, PlantLookup, AirportLookup, 
    IngestionBatch, ActivityRecord, IngestionError, AuditLog
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'created_at']

class PlantLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantLookup
        fields = ['id', 'plant_code', 'friendly_name', 'location', 'electricity_grid_emission_factor']

class IngestionErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionError
        fields = ['id', 'row_index', 'raw_content', 'error_message', 'created_at']

class IngestionBatchSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    errors = IngestionErrorSerializer(many=True, read_only=True)

    class Meta:
        model = IngestionBatch
        fields = [
            'id', 'source_type', 'file_name', 'status', 
            'total_rows', 'successful_rows', 'failed_rows', 
            'uploaded_by', 'uploaded_by_name', 'created_at', 'errors'
        ]

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'user', 'user_name', 'previous_values', 'new_values', 'timestamp']

class ActivityRecordSerializer(serializers.ModelSerializer):
    batch_detail = IngestionBatchSerializer(source='batch', read_only=True)
    audit_trail = AuditLogSerializer(many=True, read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            'id', 'organization', 'batch', 'batch_detail', 'source_row_index',
            'scope', 'category', 'description', 'facility_name',
            'raw_quantity', 'raw_unit', 'normalized_quantity', 'normalized_unit',
            'co2e_kg', 'status', 'flag_reasons',
            'billing_start_date', 'billing_end_date', 'transaction_date',
            'raw_data', 'approved_by', 'approved_by_name', 'approved_at', 
            'locked_for_audit', 'audit_trail', 'created_at', 'updated_at'
        ]
