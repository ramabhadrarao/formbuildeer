# dynamic_forms_project/context_processors.py
from apps.forms_builder.models import FormTemplate

def global_settings(request):
    """Add global settings to all templates"""
    context = {
        'site_name': 'Dynamic Forms',
        'site_description': 'Powerful Dynamic Form Builder',
    }
    
    if request.user.is_authenticated:
        context.update({
            'user_forms_count': FormTemplate.objects.filter(created_by=request.user).count(),
            'pending_approvals': request.user.assigned_submissions.filter(status='pending').count(),
        })
    
    return context