from rest_framework.routers import DefaultRouter, path
from .views import MedicationViewSet, MedicationStockViewSet, StockCheckView

router = DefaultRouter()
router.register(r'medications', MedicationViewSet, basename='medication')
router.register(r'stocks', MedicationStockViewSet, basename='medicationstock')

urlpatterns = router.urls

urlpatterns += [
    path('stock-check/', StockCheckView.as_view(), name='stock-check'),
]
