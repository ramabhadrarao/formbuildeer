# apps/workflow/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from .models import WorkflowInstance, WorkflowStep


@shared_task
def send_reminder_emails():
    """Send reminder emails for pending workflow tasks"""
    # Find workflow instances that have been pending for more than 24 hours
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    pending_instances = WorkflowInstance.objects.filter(
        is_active=True,
        current_step__isnull=False,
        current_step__step_type='approval'
    ).select_related('current_step', 'submission')
    
    reminders_sent = 0
    
    for instance in pending_instances:
        # Check if reminder already sent recently
        if instance.history.filter(
            step=instance.current_step,
            timestamp__gte=cutoff_time
        ).exists():
            continue
            
        # Send reminder
        if instance.current_step.assigned_to_user:
            send_mail(
                subject=f'Reminder: Pending approval for {instance.submission.form.name}',
                message=f'You have a pending approval task for {instance.submission.form.name}',
                from_email='noreply@dynamicforms.com',
                recipient_list=[instance.current_step.assigned_to_user.email],
            )
            reminders_sent += 1
            
    return f"Sent {reminders_sent} reminder emails"


@shared_task
def auto_approve_workflows():
    """Auto-approve workflows that have exceeded their timeout"""
    auto_approved = 0
    
    workflows = WorkflowInstance.objects.filter(
        is_active=True,
        current_step__auto_approve_after__isnull=False
    ).select_related('current_step')
    
    for workflow in workflows:
        step = workflow.current_step
        timeout = timezone.now() - timedelta(hours=step.auto_approve_after)
        
        # Check if step has been active longer than timeout
        last_action = workflow.history.filter(step=step).order_by('-timestamp').first()
        
        if last_action and last_action.timestamp < timeout:
            # Auto-approve
            from .utils import handle_workflow_action
            
            # Find the approve action
            approve_action = step.actions.filter(action_type='approve').first()
            if approve_action:
                handle_workflow_action(
                    workflow,
                    approve_action,
                    user=None,  # System auto-approval
                    comment='Auto-approved due to timeout'
                )
                auto_approved += 1
                
    return f"Auto-approved {auto_approved} workflows"