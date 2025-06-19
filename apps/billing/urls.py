from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ServiceViewSet, GenerateInvoiceView

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')

urlpatterns = router.urls

urlpatterns += [
    path('generate-invoice/', GenerateInvoiceView.as_view(), name='generate-invoice'),
]