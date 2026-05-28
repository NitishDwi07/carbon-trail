from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmissionRecordViewSet, BatchViewSet, DashboardView, UploadView

router = DefaultRouter()
router.register(r'records', EmissionRecordViewSet, basename='record')
router.register(r'batches', BatchViewSet, basename='batch')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view()),
    path('upload/', UploadView.as_view()),
]
