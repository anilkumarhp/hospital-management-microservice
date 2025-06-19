from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Django Admin Site
    path('admin/', admin.site.urls),

    # --- API Endpoints ---
    path('api/v1/operations/', include('apps.operations.urls')),
    path('api/v1/clinical/', include('apps.clinical.urls')),
    path('api/v1/billing/', include('apps.billing.urls')),
    path('api/v1/inventory/', include('apps.inventory.urls')),
    path('api/v1/portal/', include('apps.clinical.portal_urls')),

    # --- API Documentation ---
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/v1/schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
]

# This is for serving the Django Debug Toolbar in development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns