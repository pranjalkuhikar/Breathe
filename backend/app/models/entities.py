from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PlantLookup(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='plants')
    plant_code = models.CharField(max_length=50)
    friendly_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    electricity_grid_emission_factor = models.DecimalField(max_digits=8, decimal_places=4)

    class Meta:
        unique_together = ('organization', 'plant_code')

    def __str__(self):
        return f"{self.plant_code} - {self.friendly_name} ({self.location})"

class AirportLookup(models.Model):
    iata_code = models.CharField(max_length=3, unique=True)
    airport_name = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    def __str__(self):
        return f"{self.iata_code} - {self.airport_name}"

class IngestionBatch(models.Model):
    SOURCE_TYPES = [
        ('SAP', 'SAP Fuel and Procurement'),
        ('UTILITY', 'Utility Electricity Data'),
        ('TRAVEL', 'Corporate Travel Data'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Processing'),
        ('PROCESSED', 'Processed Successfully'),
        ('FAILED', 'Failed Processing'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='batches')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_type} Batch - {self.file_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class ActivityRecord(models.Model):
    SCOPE_CHOICES = [
        ('1', 'Scope 1 - Direct Emissions'),
        ('2', 'Scope 2 - Indirect Emissions'),
        ('3', 'Scope 3 - Value Chain Emissions'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved & Locked'),
        ('FLAGGED', 'Flagged as Suspicious'),
        ('REJECTED', 'Rejected'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='records')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='records')
    source_row_index = models.IntegerField()
    
    scope = models.CharField(max_length=2, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    facility_name = models.CharField(max_length=255)
    
    raw_quantity = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    raw_unit = models.CharField(max_length=50, blank=True)
    normalized_quantity = models.DecimalField(max_digits=18, decimal_places=4)
    normalized_unit = models.CharField(max_length=50)
    
    co2e_kg = models.DecimalField(max_digits=18, decimal_places=4)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    flag_reasons = models.JSONField(default=list, blank=True)
    
    billing_start_date = models.DateField(null=True, blank=True)
    billing_end_date = models.DateField(null=True, blank=True)
    transaction_date = models.DateField()
    
    raw_data = models.JSONField()
    
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_records')
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_for_audit = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} - {self.normalized_quantity} {self.normalized_unit} ({self.co2e_kg:.2f} kg CO2e)"

class IngestionError(models.Model):
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='errors')
    row_index = models.IntegerField()
    raw_content = models.JSONField()
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.batch.id} Row {self.row_index} Error: {self.error_message[:50]}"

class AuditLog(models.Model):
    activity_record = models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name='audit_trail')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    previous_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on Record {self.activity_record.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
