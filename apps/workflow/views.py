# 
# FILE: apps/workflow/views.py
# PURPOSE: Views for workflow management and approval processes
#

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import WorkflowTemplate, WorkflowInstance, WorkflowStep, WorkflowAction, WorkflowHistory
from .utils import handle_workflow_action, get_next_step
from apps.forms_builder.models import FormSubmission

@login_required
def workflow_list(request):
    """List all workflows user has access to"""
    workflows = WorkflowTemplate.objects.filter(is_active=True)
    
    # Filter based on user permissions
    if not request.user.is_superuser:
        workflows = workflows.filter(
            Q(steps__assigned_to_user=request.user) |
            Q(steps__assigned_to_group__in=request.user.groups.all())
        ).distinct()
    
    context = {
        'workflows': workflows,
        'title': 'Workflows'
    }
    return render(request, 'workflow/workflow_list.html', context)

@login_required
def workflow_detail(request, workflow_id):
    """Display workflow details and instances"""
    workflow = get_object_or_404(WorkflowTemplate, id=workflow_id)
    
    # Get workflow instances
    instances = WorkflowInstance.objects.filter(workflow=workflow).order_by('-started_at')
    
    # Pagination
    paginator = Paginator(instances, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'workflow': workflow,
        'page_obj': page_obj,
        'title': f'Workflow: {workflow.name}'
    }
    return render(request, 'workflow/workflow_detail.html', context)

@login_required
def workflow_instance_detail(request, instance_id):
    """Display workflow instance details with history"""
    instance = get_object_or_404(WorkflowInstance, id=instance_id)
    
    # Check permissions
    if not (request.user == instance.submission.submitted_by or 
            request.user == instance.current_step.assigned_to_user or
            request.user.groups.filter(id=instance.current_step.assigned_to_group_id).exists() or
            request.user.is_superuser):
        messages.error(request, 'You do not have permission to view this workflow.')
        return redirect('workflow_list')
    
    # Get workflow history
    history = instance.history.all().order_by('-timestamp')
    
    # Get available actions for current user
    available_actions = []
    if instance.is_active and instance.current_step:
        if (request.user == instance.current_step.assigned_to_user or
            request.user.groups.filter(id=instance.current_step.assigned_to_group_id).exists()):
            available_actions = instance.current_step.actions.all()
    
    context = {
        'instance': instance,
        'history': history,
        'available_actions': available_actions,
        'title': f'Workflow Instance: {instance.workflow.name}'
    }
    return render(request, 'workflow/workflow_instance_detail.html', context)

@login_required
@require_POST
def workflow_action(request, instance_id):
    """Handle workflow actions (approve, reject, etc.)"""
    instance = get_object_or_404(WorkflowInstance, id=instance_id)
    
    # Check permissions
    if not (request.user == instance.current_step.assigned_to_user or
            request.user.groups.filter(id=instance.current_step.assigned_to_group_id).exists()):
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to perform this action.'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        action_id = data.get('action_id')
        comment = data.get('comment', '')
        delegate_to_id = data.get('delegate_to')
        
        action = get_object_or_404(WorkflowAction, id=action_id)
        
        # Handle delegation if specified
        delegate_to = None
        if delegate_to_id:
            from apps.users.models import User
            delegate_to = get_object_or_404(User, id=delegate_to_id)
        
        # Process the workflow action
        result = handle_workflow_action(
            instance=instance,
            action=action,
            user=request.user,
            comment=comment,
            delegate_to=delegate_to
        )
        
        if result['success']:
            # Log the action
            WorkflowHistory.objects.create(
                instance=instance,
                step=instance.current_step,
                action=action,
                actor=request.user,
                comment=comment,
                data_before=instance.submission.data,
                data_after=instance.submission.data  # Could be modified by workflow
            )
            
            # Update submission status if needed
            if action.action_type == 'approve':
                instance.submission.status = 'approved'
            elif action.action_type == 'reject':
                instance.submission.status = 'rejected'
            elif action.action_type == 'request_info':
                instance.submission.status = 'pending_info'
            
            instance.submission.save()
            
            messages.success(request, f'Action "{action.name}" completed successfully.')
            
            return JsonResponse({
                'success': True,
                'message': result.get('message', 'Action completed successfully'),
                'redirect_url': request.META.get('HTTP_REFERER', '/workflow/')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Action failed')
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def approval_dashboard(request):
    """Dashboard for approval management"""
    user = request.user
    
    # Get pending approvals assigned to user
    pending_approvals = WorkflowInstance.objects.filter(
        is_active=True,
        current_step__assigned_to_user=user
    ).count()
    
    # Get pending approvals for user's groups
    group_approvals = WorkflowInstance.objects.filter(
        is_active=True,
        current_step__assigned_to_group__in=user.groups.all()
    ).count()
    
    # Get completed approvals by user in last 30 days
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    completed_approvals = WorkflowHistory.objects.filter(
        actor=user,
        timestamp__gte=thirty_days_ago,
        action__action_type__in=['approve', 'reject']
    ).count()
    
    # Get recent activity
    recent_activity = WorkflowHistory.objects.filter(
        Q(actor=user) | 
        Q(instance__current_step__assigned_to_user=user) |
        Q(instance__current_step__assigned_to_group__in=user.groups.all())
    ).select_related(
        'instance', 'step', 'action', 'actor'
    ).order_by('-timestamp')[:10]
    
    context = {
        'pending_approvals': pending_approvals,
        'group_approvals': group_approvals,
        'completed_approvals': completed_approvals,
        'recent_activity': recent_activity,
        'title': 'Approval Dashboard'
    }
    return render(request, 'workflow/approval_dashboard.html', context)

@login_required
def pending_approvals(request):
    """List of pending approvals for the user"""
    user = request.user
    
@login_required
def pending_approvals(request):
    """List of pending approvals for the user"""
    user = request.user
    
    # Get pending instances assigned to user or user's groups
    instances = WorkflowInstance.objects.filter(
        is_active=True
    ).filter(
        Q(current_step__assigned_to_user=user) |
        Q(current_step__assigned_to_group__in=user.groups.all())
    ).select_related(
        'workflow', 'submission', 'submission__form', 'submission__submitted_by', 'current_step'
    ).order_by('-started_at')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        instances = instances.filter(submission__status=status_filter)
    
    # Filter by workflow
    workflow_filter = request.GET.get('workflow')
    if workflow_filter:
        instances = instances.filter(workflow_id=workflow_filter)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        instances = instances.filter(
            Q(submission__form__name__icontains=search) |
            Q(submission__submitted_by__first_name__icontains=search) |
            Q(submission__submitted_by__last_name__icontains=search) |
            Q(submission__submitted_by__email__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(instances, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get workflows for filter dropdown
    workflows = WorkflowTemplate.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'workflows': workflows,
        'status_filter': status_filter,
        'workflow_filter': workflow_filter,
        'search': search,
        'title': 'Pending Approvals'
    }
    return render(request, 'workflow/pending_approvals.html', context)

@login_required
def approval_history(request):
    """History of user's approval actions"""
    user = request.user
    
    # Get user's approval history
    history = WorkflowHistory.objects.filter(
        actor=user
    ).select_related(
        'instance', 'instance__submission', 'instance__submission__form',
        'step', 'action'
    ).order_by('-timestamp')
    
    # Filter by action type
    action_filter = request.GET.get('action', 'all')
    if action_filter != 'all':
        history = history.filter(action__action_type=action_filter)
    
    # Filter by date range
    date_filter = request.GET.get('date_range', '30')
    if date_filter != 'all':
        from datetime import datetime, timedelta
        days = int(date_filter)
        start_date = datetime.now() - timedelta(days=days)
        history = history.filter(timestamp__gte=start_date)
    
    # Pagination
    paginator = Paginator(history, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'action_filter': action_filter,
        'date_filter': date_filter,
        'title': 'Approval History'
    }
    return render(request, 'workflow/approval_history.html', context)