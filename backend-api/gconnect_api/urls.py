# urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from gconnect_api.views import landing_page

schema_view = get_schema_view(
    openapi.Info(
        title="G-Connect API",
        default_version='v1',
        description="API de la plateforme G-Connect",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.api.v1.urls')),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('', landing_page),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# def custom_404_view(request, exception):
#     return JsonResponse({
#         "success": False,
#         "message": "Page introuvable. Vérifiez l’URL.",
#     }, status=404)

# handler404 = 'gconnect_api.urls.custom_404_view'
