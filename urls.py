# dynamic_forms_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.forms_builder.views import dashboard

admin.site.site_header = "Dynamic Forms Administration"
admin.site.site_title = "Dynamic Forms Admin"
admin.site.index_title = "Welcome to Dynamic Forms Administration"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('auth/', include('apps.users.urls')),
    path('forms/', include('apps.forms_builder.urls')),
    path('workflow/', include('apps.workflow.urls')),
    path('api/', include('apps.forms_builder.api_views')),
    path('nested_admin/', include('nested_admin.urls')),
    path('tinymce/', include('tinymce.urls')),
    path('select2/', include('django_select2.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)