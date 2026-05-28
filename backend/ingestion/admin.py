from django.contrib import admin
from .models import Organisation, UserProfile, IngestionBatch, EmissionRecord, AuditLog


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'organisation']


@admin.register(IngestionBatch)
class IngestionBatchAdmin(admin.ModelAdmin):
    list_display = ['source_type', 'organisation', 'uploaded_by', 'uploaded_at', 'status', 'row_count', 'error_count']
    list_filter = ['source_type', 'status']


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['activity_date', 'scope', 'category', 'description', 'normalised_quantity',
                    'normalised_unit', 'co2e_kg', 'status', 'is_suspicious']
    list_filter = ['scope', 'category', 'status', 'is_suspicious']
    readonly_fields = ['raw_data', 'created_at', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['record', 'changed_by', 'changed_at', 'action']
    readonly_fields = ['record', 'changed_by', 'changed_at', 'action', 'before', 'after', 'note']
