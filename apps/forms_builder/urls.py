# 
# FILE: apps/forms_builder/urls.py
# PURPOSE: URL routing for forms application
#

from django.urls import path, include
from . import views, api_views

urlpatterns = [
    # Form display and interaction
    path('', views.form_list, name='form_list'),
    path('<uuid:form_id>/', views.form_render, name='form_render'),
    path('<uuid:form_id>/submit/', views.handle_form_submission, name='form_submit'),
    path('submission/<uuid:submission_id>/', views.submission_detail, name='submission_detail'),
    
    # Lookup endpoints
    path('lookup/<str:model_name>/', views.lookup_view, name='lookup'),
    
    # API endpoints
    path('api/', include([
        path('forms/', api_views.FormListAPI.as_view(), name='api_form_list'),
        path('forms/<uuid:form_id>/', api_views.FormDetailAPI.as_view(), name='api_form_detail'),
        path('forms/<uuid:form_id>/submit/', api_views.FormSubmitAPI.as_view(), name='api_form_submit'),
        path('submissions/<uuid:submission_id>/', api_views.SubmissionDetailAPI.as_view(), name='api_submission_detail'),
        path('dashboard/stats/', api_views.DashboardStatsAPI.as_view(), name='api_dashboard_stats'),
        path('dashboard/activity/', api_views.RecentActivityAPI.as_view(), name='api_recent_activity'),
        path('dashboard/charts/', api_views.ChartDataAPI.as_view(), name='api_chart_data'),
        path('lookup/<str:model_name>/', api_views.LookupAPI.as_view(), name='api_lookup'),
    ])),
]