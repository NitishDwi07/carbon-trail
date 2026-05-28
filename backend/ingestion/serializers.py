from rest_framework import serializers
from .models import EmissionRecord, IngestionBatch, Organisation, AuditLog


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'slug']


class IngestionBatchSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = IngestionBatch
        fields = [
            'id', 'source_type', 'source_type_display', 'uploaded_by_name',
            'uploaded_at', 'original_filename', 'status', 'status_display',
            'row_count', 'error_count', 'notes',
        ]


class EmissionRecordSerializer(serializers.ModelSerializer):
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    batch_source = serializers.CharField(source='batch.source_type', read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'batch_id', 'batch_source',
            'scope', 'scope_display', 'category', 'category_display',
            'activity_date', 'description',
            'quantity', 'original_unit',
            'normalised_quantity', 'normalised_unit',
            'co2e_kg',
            'source_row_id', 'source_plant_code', 'source_meter_id', 'source_vendor',
            'status', 'status_display',
            'reviewed_by_name', 'reviewed_at', 'reviewer_note',
            'is_suspicious', 'suspicion_reason',
            'created_at', 'updated_at', 'locked',
            'raw_data',
        ]
        read_only_fields = [
            'id', 'batch_id', 'scope', 'category', 'activity_date', 'created_at',
            'normalised_quantity', 'normalised_unit', 'co2e_kg', 'is_suspicious',
            'suspicion_reason', 'raw_data', 'locked',
        ]


class ReviewActionSerializer(serializers.Serializer):
    """Used to approve / flag / reject a record."""
    action = serializers.ChoiceField(choices=['approve', 'flag', 'reject'])
    note = serializers.CharField(required=False, allow_blank=True)


class AuditLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'changed_by_name', 'changed_at', 'action', 'before', 'after', 'note']


class DashboardStatsSerializer(serializers.Serializer):
    total_records = serializers.IntegerField()
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    flagged = serializers.IntegerField()
    rejected = serializers.IntegerField()
    total_co2e_kg = serializers.DecimalField(max_digits=18, decimal_places=2)
    by_scope = serializers.DictField()
    by_category = serializers.DictField()
    recent_batches = IngestionBatchSerializer(many=True)
