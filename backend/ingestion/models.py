from django.db import models
from django.contrib.auth.models import User
import uuid


class Organisation(models.Model):
    """
    Multi-tenancy root. Every piece of data belongs to an org.
    Analysts only see their own org's data.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Ties a Django user to an org."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='members')

    def __str__(self):
        return f"{self.user.username} @ {self.organisation.name}"


class IngestionBatch(models.Model):
    """
    One upload session = one batch. Lets us track what came in together,
    retry failed rows, and give analysts a clean review surface.
    """
    SOURCE_SAP = 'sap'
    SOURCE_UTILITY = 'utility'
    SOURCE_TRAVEL = 'travel'
    SOURCE_CHOICES = [
        (SOURCE_SAP, 'SAP Fuel & Procurement'),
        (SOURCE_UTILITY, 'Utility / Electricity'),
        (SOURCE_TRAVEL, 'Corporate Travel'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_DONE, 'Done'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='batches')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=500, blank=True)
    raw_file = models.FileField(upload_to='uploads/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.source_type} batch @ {self.uploaded_at:%Y-%m-%d %H:%M} ({self.status})"


class EmissionRecord(models.Model):
    """
    The normalised single source of truth for every activity row.
    All three sources collapse into this table.

    Scope categorisation:
      Scope 1 = direct combustion (SAP fuel)
      Scope 2 = purchased electricity (utility data)
      Scope 3 = everything else (travel, procurement)
    """
    SCOPE_1 = '1'
    SCOPE_2 = '2'
    SCOPE_3 = '3'
    SCOPE_CHOICES = [(SCOPE_1, 'Scope 1'), (SCOPE_2, 'Scope 2'), (SCOPE_3, 'Scope 3')]

    CATEGORY_FUEL = 'fuel'
    CATEGORY_ELECTRICITY = 'electricity'
    CATEGORY_FLIGHT = 'flight'
    CATEGORY_HOTEL = 'hotel'
    CATEGORY_GROUND = 'ground_transport'
    CATEGORY_PROCUREMENT = 'procurement'
    CATEGORY_CHOICES = [
        (CATEGORY_FUEL, 'Fuel'),
        (CATEGORY_ELECTRICITY, 'Electricity'),
        (CATEGORY_FLIGHT, 'Flight'),
        (CATEGORY_HOTEL, 'Hotel'),
        (CATEGORY_GROUND, 'Ground Transport'),
        (CATEGORY_PROCUREMENT, 'Procurement'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_FLAGGED = 'flagged'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_FLAGGED, 'Flagged / Suspicious'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='records')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='records')

    # -- Classification --
    scope = models.CharField(max_length=1, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)

    # -- Activity data (normalised) --
    activity_date = models.DateField()
    description = models.CharField(max_length=500, blank=True)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)

    # Original unit as it came in (L, kWh, km, nights, etc.)
    original_unit = models.CharField(max_length=50)
    # Normalised unit (always kWh for energy, km for distance, L for liquid fuel, kg for mass)
    normalised_unit = models.CharField(max_length=50)
    normalised_quantity = models.DecimalField(max_digits=18, decimal_places=4)

    # CO2e in kg — may be null if emission factor not applied yet
    co2e_kg = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    # -- Source traceability --
    source_row_id = models.CharField(max_length=200, blank=True, help_text="Row ID / doc number from source system")
    source_plant_code = models.CharField(max_length=100, blank=True, help_text="SAP plant/cost centre")
    source_meter_id = models.CharField(max_length=100, blank=True, help_text="Utility meter reference")
    source_vendor = models.CharField(max_length=200, blank=True)

    # -- Review workflow --
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_note = models.TextField(blank=True)

    # -- Flags set during ingestion --
    is_suspicious = models.BooleanField(default=False)
    suspicion_reason = models.CharField(max_length=500, blank=True)

    # -- Audit trail --
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Locked once approved and sent to auditors — no edits allowed after this
    locked = models.BooleanField(default=False)

    # Raw original row stored as JSON for traceability
    raw_data = models.JSONField(default=dict)

    class Meta:
        ordering = ['-activity_date']
        indexes = [
            models.Index(fields=['organisation', 'scope']),
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['batch']),
            models.Index(fields=['activity_date']),
        ]

    def __str__(self):
        return f"{self.category} | {self.activity_date} | {self.normalised_quantity} {self.normalised_unit}"


class AuditLog(models.Model):
    """
    Immutable log of every state change on an EmissionRecord.
    Written by signals — never directly by views.
    """
    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_logs')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100)  # e.g. "status_change", "field_edit"
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.action} on {self.record_id} by {self.changed_by}"
