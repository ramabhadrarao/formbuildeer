# 
# FILE: apps/workflow/urls.py
# PURPOSE: URL routing for workflow management
#

from django.urls import path
from . import views

urlpatterns = [
    # Workflow management
    path('', views.workflow_list, name='workflow_list'),
    path('<uuid:workflow_id>/', views.workflow_detail, name='workflow_detail'),
    path('instance/<uuid:instance_id>/', views.workflow_instance_detail, name='workflow_instance_detail'),
    path('instance/<uuid:instance_id>/action/', views.workflow_action, name='workflow_action'),
    
    # Approval dashboard
    path('approvals/', views.approval_dashboard, name='approval_dashboard'),
    path('approvals/pending/', views.pending_approvals, name='pending_approvals'),
    path('approvals/history/', views.approval_history, name='approval_history'),
]