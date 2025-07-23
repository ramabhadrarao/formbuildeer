from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse
from .models import FormTemplate, FormField, FormSubmission, FormFile
from .utils import FormRenderer, FormValidator
from apps.workflow.utils import trigger_workflow
from apps.users.models import User, Department, Project
import json

@login_required
def form_list(request):
    """List all available forms for the user"""
    forms = FormTemplate.objects.filter(is_active=True)
    
    # Filter based on user permissions
    if not request.user.is_superuser:
        forms = forms.filter(
            Q(created_by=request.user) |
            Q(permissions__user=request.user) |
            Q(permissions__group__in=request.user.groups.all())
        ).distinct()
    
    context = {
        'forms': forms,
        'title': 'Available Forms'
    }
    return render(request, 'forms/form_list.html', context)

@login_required
def form_render(request, form_id):
    """Render a dynamic form"""
    form_template = get_object_or_404(FormTemplate, id=form_id, is_active=True)
    
    # Check permissions
    if not request.user.has_perm('view_formtemplate', form_template):
        messages.error(request, 'You do not have permission to view this form.')
        return redirect('form_list')
    
    if request.method == 'POST':
        # Handle form submission
        return handle_form_submission(request, form_template)
    
    # Get fields with permissions
    fields = form_template.fields.all()
    field_data = []
    
    for field in fields:
        # Check field-level permissions
        if has_field_permission(request.user, field, 'view'):
            field_dict = {
                'name': field.name,
                'label': field.label,
                'field_type': field.field_type,
                'required': field.required and has_field_permission(request.user, field, 'required'),
                'placeholder': field.placeholder,
                'help_text': field.help_text,
                'default_value': field.default_value,
                'show_if': field.show_if,
                'choices': field.choices,
                'validation_rules': get_field_validation_rules(field),
                'can_edit': has_field_permission(request.user, field, 'edit'),
            }
            
            if field.field_type == 'nested':
                field_dict['nested_form'] = field.nested_form
                field_dict['allow_multiple'] = field.allow_multiple
            
            field_data.append(field_dict)
    
    context = {
        'form_template': form_template,
        'fields': field_data,
        'title': form_template.name
    }
    
    return render(request, 'forms/form_render.html', context)

def handle_form_submission(request, form_template):
    """Handle form submission with validation"""
    form_data = {}
    files = {}
    errors = {}
    
    # Validate each field
    for field in form_template.fields.all():
        field_name = field.name
        value = request.POST.get(field_name)
        
        # Check permissions
        if not has_field_permission(request.user, field, 'edit'):
            continue
        
        # Validate field
        validator = FormValidator(field)
        is_valid, error_message = validator.validate(value, request.POST)
        
        if not is_valid:
            errors[field_name] = error_message
        else:
            form_data[field_name] = value
        
        # Handle file uploads
        if field.field_type in ['file', 'image']:
            file = request.FILES.get(field_name)
            if file:
                files[field_name] = file
    
    if errors:
        messages.error(request, 'Please correct the errors below.')
        return JsonResponse({'success': False, 'errors': errors}, status=400)
    
    # Create submission
    submission = FormSubmission.objects.create(
        form=form_template,
        submitted_by=request.user,
        data=form_data,
        status='pending'
    )
    
    # Save files
    for field_name, file in files.items():
        FormFile.objects.create(
            submission=submission,
            field_name=field_name,
            file=file
        )
    
    # Trigger workflow
    trigger_workflow(submission)
    
    messages.success(request, 'Form submitted successfully!')
    return JsonResponse({
        'success': True,
        'submission_id': str(submission.id),
        'redirect_url': reverse('submission_detail', args=[submission.id])
    })

def has_field_permission(user, field, permission_type):
    """Check if user has specific permission on field"""
    if user.is_superuser:
        return True
    
    # Check user-specific permissions
    if field.permissions.filter(user=user, permission_type=permission_type).exists():
        return True
    
    # Check group permissions
    user_groups = user.groups.all()
    if field.permissions.filter(group__in=user_groups, permission_type=permission_type).exists():
        return True
    
    # Default permissions
    if permission_type == 'view':
        return True
    elif permission_type == 'edit':
        return not field.required
    elif permission_type == 'required':
        return field.required
    
    return False

def get_field_validation_rules(field):
    """Get validation rules for a field"""
    rules = {
        'required': field.required,
    }
    
    if field.min_value:
        rules['min'] = field.min_value
    if field.max_value:
        rules['max'] = field.max_value
    if field.min_length:
        rules['minLength'] = field.min_length
    if field.max_length:
        rules['maxLength'] = field.max_length
    if field.regex_pattern:
        rules['pattern'] = field.regex_pattern
    
    # Add custom validation rules
    for rule in field.validation_rules.all():
        if rule.rule_type == 'required_if':
            rules['requiredIf'] = rule.condition
            rules['requiredMessage'] = rule.error_message
    
    return rules

@login_required
def lookup_view(request, model_name):
    """Handle lookup field queries"""
    query = request.GET.get('q', '')
    
    # Map model names to actual models
    model_map = {
        'user': User,
        'department': Department,
        'project': Project,
        # Add more models as needed
    }
    
    model = model_map.get(model_name)
    if not model:
        return JsonResponse({'results': []})
    
    # Perform search
    results = model.objects.filter(
        Q(name__icontains=query) | Q(title__icontains=query)
    )[:20]
    
    # Format results
    data = {
        'results': [
            {
                'id': str(obj.id),
                'label': str(obj),
                'value': getattr(obj, 'name', str(obj))
            }
            for obj in results
        ]
    }
    
    return JsonResponse(data)

@login_required
def submission_detail(request, submission_id):
    """View submission details"""
    submission = get_object_or_404(FormSubmission, id=submission_id)
    
    # Check permissions
    if not (request.user == submission.submitted_by or 
            request.user.has_perm('view_formsubmission', submission)):
        messages.error(request, 'You do not have permission to view this submission.')
        return redirect('form_list')
    
    context = {
        'submission': submission,
        'form_template': submission.form,
        'files': submission.files.all(),
        'workflow': getattr(submission, 'workflow_instance', None),
        'title': f'Submission - {submission.form.name}'
    }
    
    return render(request, 'forms/submission_detail.html', context)