from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from .models import EmissionRecord, IngestionBatch, Organisation, AuditLog
from .serializers import (
    EmissionRecordSerializer, IngestionBatchSerializer,
    ReviewActionSerializer, AuditLogSerializer, DashboardStatsSerializer,
    OrganisationSerializer,
)
from .parsers.sap_parser import parse_sap_csv
from .parsers.utility_parser import parse_utility_csv
from .parsers.travel_parser import parse_travel_csv


def get_user_org(request):
    """Helper — get org from user profile. Falls back to first org for demo."""
    try:
        return request.user.profile.organisation
    except Exception:
        return Organisation.objects.first()


class DashboardView(APIView):
    def get(self, request):
        org = get_user_org(request)
        if not org:
            return Response({'error': 'No organisation found'}, status=400)

        qs = EmissionRecord.objects.filter(organisation=org)

        totals = qs.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            approved=Count('id', filter=Q(status='approved')),
            flagged=Count('id', filter=Q(status='flagged')),
            rejected=Count('id', filter=Q(status='rejected')),
            total_co2e=Sum('co2e_kg'),
        )

        by_scope = list(
            qs.values('scope').annotate(
                count=Count('id'),
                co2e=Sum('co2e_kg')
            )
        )

        by_category = list(
            qs.values('category').annotate(
                count=Count('id'),
                co2e=Sum('co2e_kg')
            )
        )

        recent_batches = IngestionBatch.objects.filter(organisation=org).order_by('-uploaded_at')[:5]

        return Response({
            'total_records': totals['total'],
            'pending': totals['pending'],
            'approved': totals['approved'],
            'flagged': totals['flagged'],
            'rejected': totals['rejected'],
            'total_co2e_kg': totals['total_co2e'] or 0,
            'by_scope': {item['scope']: {'count': item['count'], 'co2e': str(item['co2e'] or 0)} for item in by_scope},
            'by_category': {item['category']: {'count': item['count'], 'co2e': str(item['co2e'] or 0)} for item in by_category},
            'recent_batches': IngestionBatchSerializer(recent_batches, many=True).data,
        })


class UploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def post(self, request):
        org = get_user_org(request)
        if not org:
            return Response({'error': 'No organisation found'}, status=400)

        source_type = request.data.get('source_type')
        if source_type not in ('sap', 'utility', 'travel'):
            return Response({'error': 'source_type must be sap, utility, or travel'}, status=400)

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        # Read content BEFORE saving — saving the FileField consumes the pointer
        content = file.read()
        file.seek(0)

        batch = IngestionBatch.objects.create(
            organisation=org,
            source_type=source_type,
            uploaded_by=request.user,
            original_filename=file.name,
            raw_file=file,
            status=IngestionBatch.STATUS_PROCESSING,
        )

        try:
            if source_type == 'sap':
                result = parse_sap_csv(content, batch.id, org.id)
            elif source_type == 'utility':
                result = parse_utility_csv(content, batch.id, org.id)
            else:
                result = parse_travel_csv(content, batch.id, org.id)
        except Exception as e:
            batch.status = IngestionBatch.STATUS_FAILED
            batch.notes = str(e)
            batch.save()
            return Response({'error': f'Parsing failed: {str(e)}'}, status=500)

        records_to_create = [
            EmissionRecord(
                organisation_id=r['organisation_id'],
                batch_id=r['batch_id'],
                scope=r['scope'],
                category=r['category'],
                activity_date=r['activity_date'],
                description=r['description'],
                quantity=r['quantity'],
                original_unit=r['original_unit'],
                normalised_unit=r['normalised_unit'],
                normalised_quantity=r['normalised_quantity'],
                co2e_kg=r['co2e_kg'],
                source_row_id=r.get('source_row_id', ''),
                source_plant_code=r.get('source_plant_code', ''),
                source_meter_id=r.get('source_meter_id', ''),
                source_vendor=r.get('source_vendor', ''),
                is_suspicious=r['is_suspicious'],
                suspicion_reason=r['suspicion_reason'],
                raw_data=r['raw_data'],
                status='flagged' if r['is_suspicious'] else 'pending',
            )
            for r in result['records']
        ]

        EmissionRecord.objects.bulk_create(records_to_create)

        batch.row_count = len(records_to_create)
        batch.error_count = len(result['errors'])
        batch.status = IngestionBatch.STATUS_DONE
        batch.notes = f"Errors: {result['errors'][:5]}" if result['errors'] else ''
        batch.save()

        return Response({
            'batch_id': str(batch.id),
            'parsed': len(records_to_create),
            'errors': len(result['errors']),
            'error_details': result['errors'][:10],
            'stats': result.get('stats', {}),
        }, status=201)


class EmissionRecordViewSet(viewsets.ModelViewSet):
    serializer_class = EmissionRecordSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        org = get_user_org(self.request)
        qs = EmissionRecord.objects.filter(organisation=org).select_related('batch', 'reviewed_by')

        # Filters
        scope = self.request.query_params.get('scope')
        category = self.request.query_params.get('category')
        status_filter = self.request.query_params.get('status')
        suspicious = self.request.query_params.get('suspicious')
        batch_id = self.request.query_params.get('batch_id')

        if scope:
            qs = qs.filter(scope=scope)
        if category:
            qs = qs.filter(category=category)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if suspicious == 'true':
            qs = qs.filter(is_suspicious=True)
        if batch_id:
            qs = qs.filter(batch_id=batch_id)

        return qs

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        record = self.get_object()

        if record.locked:
            return Response({'error': 'Record is locked — it has been sent to auditors'}, status=400)

        serializer = ReviewActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        action_map = {
            'approve': EmissionRecord.STATUS_APPROVED,
            'flag': EmissionRecord.STATUS_FLAGGED,
            'reject': EmissionRecord.STATUS_REJECTED,
        }

        old_status = record.status
        new_status = action_map[serializer.validated_data['action']]
        note = serializer.validated_data.get('note', '')

        record.status = new_status
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.reviewer_note = note

        # Lock if approving
        if new_status == EmissionRecord.STATUS_APPROVED:
            record.locked = True

        record.save()

        # Write to audit log
        AuditLog.objects.create(
            record=record,
            changed_by=request.user,
            action='status_change',
            before={'status': old_status},
            after={'status': new_status},
            note=note,
        )

        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['get'])
    def audit_trail(self, request, pk=None):
        record = self.get_object()
        logs = AuditLog.objects.filter(record=record)
        return Response(AuditLogSerializer(logs, many=True).data)


class BatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionBatchSerializer

    def get_queryset(self):
        org = get_user_org(self.request)
        return IngestionBatch.objects.filter(organisation=org)