import csv
import io
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.generic import TemplateView

from django.contrib.auth.models import User
from app.models import (
    Organization, PlantLookup, IngestionBatch, 
    ActivityRecord, IngestionError, AuditLog
)
from app.api.schemas import (
    OrganizationSerializer, PlantLookupSerializer, 
    IngestionBatchSerializer, ActivityRecordSerializer, 
    IngestionErrorSerializer, AuditLogSerializer
)
from app.services.ingestion import EsgIngestionService
from app.repositories.queries import ActivityRepository

class EsgUploadView(views.APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        source_type = request.data.get('source_type')
        org_id = request.data.get('organization_id')

        if not file_obj:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        if not source_type or source_type not in ('SAP', 'UTILITY', 'TRAVEL'):
            return Response({'error': 'Invalid or missing source_type.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not org_id:
            org = Organization.objects.first()
            if not org:
                org = Organization.objects.create(name="Breathe ESG Client Corp")
        else:
            try:
                org = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()
        
        batch = IngestionBatch.objects.create(
            organization=org,
            source_type=source_type,
            file_name=file_obj.name,
            uploaded_by=user
        )

        try:
            file_content = file_obj.read().decode('utf-8')
            csv_file = io.StringIO(file_content)
            
            sample = file_content[:1024]
            if ';' in sample and ',' not in sample:
                csv_reader = csv.DictReader(csv_file, delimiter=';')
            else:
                csv_reader = csv.DictReader(csv_file)

            if not csv_reader.fieldnames:
                raise ValueError("CSV file is empty or headers are unreadable.")

            if source_type == 'SAP':
                success, failure = EsgIngestionService.process_sap_batch(batch, csv_reader)
            elif source_type == 'UTILITY':
                success, failure = EsgIngestionService.process_utility_batch(batch, csv_reader)
            elif source_type == 'TRAVEL':
                success, failure = EsgIngestionService.process_travel_batch(batch, csv_reader)

            return Response({
                'message': 'File processed successfully',
                'batch_id': batch.id,
                'source_type': source_type,
                'total_rows': batch.total_rows,
                'successful_rows': success,
                'failed_rows': failure,
                'status': batch.status
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            batch.status = 'FAILED'
            batch.save()
            ActivityRepository.create_error(batch, 0, {'file_name': file_obj.name}, f"Critical: {str(e)}")
            return Response({'error': f'Failed: {str(e)}', 'batch_id': batch.id}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

class ActivityRecordViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityRecordSerializer
    queryset = ActivityRecord.objects.all().order_by('-transaction_date', '-id')

    def get_queryset(self):
        queryset = super().get_queryset()
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        scope_param = self.request.query_params.get('scope')
        if scope_param:
            queryset = queryset.filter(scope=scope_param)
        source_param = self.request.query_params.get('source_type')
        if source_param:
            queryset = queryset.filter(batch__source_type=source_param)
        search_query = self.request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(facility_name__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        return queryset

    def update(self, request, *args, **kwargs):
        """Delegates the manual correction updates to the Repository Layer."""
        instance = self.get_object()
        user = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()
        
        try:
            qty_val = request.data.get('normalized_quantity')
            category_val = request.data.get('category')
            
            # Call data repository for transaction safety and logging
            updated_instance = ActivityRepository.update_record(instance.id, qty_val, category_val, user)
            serializer = self.get_serializer(updated_instance)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Delegates the sign-off action to the Repository Layer."""
        user = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()
        try:
            updated_instance = ActivityRepository.approve_record(pk, user)
            serializer = self.get_serializer(updated_instance)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        """Delegates the flagging action to the Repository Layer."""
        user = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()
        reason = request.data.get('reason', 'Flagged by analyst')
        try:
            updated_instance = ActivityRepository.flag_record(pk, reason, user)
            serializer = self.get_serializer(updated_instance)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Delegates the reject action to the Repository Layer."""
        user = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()
        try:
            updated_instance = ActivityRepository.reject_record(pk, user)
            serializer = self.get_serializer(updated_instance)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DashboardStatsView(views.APIView):
    def get(self, request, *args, **kwargs):
        org_id = request.query_params.get('organization_id')
        
        records = ActivityRecord.objects.all()
        batches = IngestionBatch.objects.all()
        
        if org_id:
            records = records.filter(organization_id=org_id)
            batches = batches.filter(organization_id=org_id)

        totals = records.aggregate(
            total_co2e=Sum('co2e_kg'),
            approved_co2e=Sum('co2e_kg', filter=Q(status='APPROVED')),
            pending_co2e=Sum('co2e_kg', filter=Q(status='PENDING')),
            flagged_co2e=Sum('co2e_kg', filter=Q(status='FLAGGED'))
        )
        
        total_co2e = totals['total_co2e'] or Decimal("0")
        approved_co2e = totals['approved_co2e'] or Decimal("0")
        pending_co2e = totals['pending_co2e'] or Decimal("0")
        flagged_co2e = totals['flagged_co2e'] or Decimal("0")

        status_counts = records.values('status').annotate(count=Count('id'))
        status_dict = {s['status']: s['count'] for s in status_counts}
        total_records = sum(status_dict.values())
        
        flagged_rate = (status_dict.get('FLAGGED', 0) / total_records * 100) if total_records else 0
        approval_rate = (status_dict.get('APPROVED', 0) / total_records * 100) if total_records else 0

        scope_aggregates = records.values('scope').annotate(co2e=Sum('co2e_kg'), count=Count('id'))
        scope_breakdown = {
            'Scope 1': {'co2e': 0.0, 'count': 0, 'percentage': 0.0},
            'Scope 2': {'co2e': 0.0, 'count': 0, 'percentage': 0.0},
            'Scope 3': {'co2e': 0.0, 'count': 0, 'percentage': 0.0}
        }
        
        for sa in scope_aggregates:
            scope_key = f"Scope {sa['scope']}"
            if scope_key in scope_breakdown:
                co2e_val = float(sa['co2e'] or 0)
                scope_breakdown[scope_key]['co2e'] = co2e_val
                scope_breakdown[scope_key]['count'] = sa['count']
                if total_co2e > 0:
                    scope_breakdown[scope_key]['percentage'] = round((co2e_val / float(total_co2e)) * 100, 2)

        source_aggregates = records.values('batch__source_type').annotate(co2e=Sum('co2e_kg'), count=Count('id'))
        source_breakdown = []
        for sga in source_aggregates:
            stype = sga['batch__source_type'] or "MANUAL"
            co2e_val = float(sga['co2e'] or 0)
            source_breakdown.append({
                'source': stype,
                'co2e': co2e_val,
                'count': sga['count'],
                'percentage': round((co2e_val / float(total_co2e)) * 100, 2) if total_co2e > 0 else 0.0
            })

        batch_counts = batches.values('status').annotate(count=Count('id'))
        batch_summary = {bc['status']: bc['count'] for bc in batch_counts}

        monthly_data = records.annotate(month=TruncMonth('transaction_date')).values('month').annotate(co2e=Sum('co2e_kg')).order_by('month')
        monthly_trends = []
        for md in monthly_data:
            if md['month']:
                monthly_trends.append({
                    'month': md['month'].strftime('%b %Y'),
                    'co2e': float(md['co2e'] or 0)
                })

        top_facilities = records.values('facility_name').annotate(co2e=Sum('co2e_kg')).order_by('-co2e')[:5]
        top_centers = [{'facility': tf['facility_name'], 'co2e': float(tf['co2e'] or 0)} for tf in top_facilities]

        return Response({
            'total_co2e_kg': float(total_co2e),
            'approved_co2e_kg': float(approved_co2e),
            'pending_co2e_kg': float(pending_co2e),
            'flagged_co2e_kg': float(flagged_co2e),
            'total_records': total_records,
            'flagged_records_count': status_dict.get('FLAGGED', 0),
            'approved_records_count': status_dict.get('APPROVED', 0),
            'flagged_rate_pct': round(flagged_rate, 2),
            'approval_rate_pct': round(approval_rate, 2),
            'scopes': scope_breakdown,
            'sources': source_breakdown,
            'batches': batch_summary,
            'monthly_trends': monthly_trends,
            'top_facilities': top_centers
        })

class BatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionBatchSerializer
    queryset = IngestionBatch.objects.all().order_by('-created_at')

    def get_queryset(self):
        queryset = super().get_queryset()
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        return queryset

class IndexView(TemplateView):
    template_name = "index.html"
