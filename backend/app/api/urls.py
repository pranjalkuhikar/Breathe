from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.api.controllers import (
    EsgUploadView, ActivityRecordViewSet, 
    DashboardStatsView, BatchViewSet
)

router = DefaultRouter()
router.register(r'records', ActivityRecordViewSet, basename='record')
router.register(r'batches', BatchViewSet, basename='batch')

urlpatterns = [
    path('ingest/', EsgUploadView.as_view(), name='esg_ingest_upload'),
    path('dashboard-stats/', DashboardStatsView.as_view(), name='esg_dashboard_stats'),
    path('', include(router.urls)),
]
