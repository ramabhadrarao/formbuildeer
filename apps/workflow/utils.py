# 
# FILE: apps/workflow/utils.py
# PURPOSE: Utility functions for workflow processing and management
#

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from .models import WorkflowTemplate, WorkflowInstance, WorkflowStep, WorkflowAction, WorkflowHistory
import logging

logger = logging.getLogger(__name__)

def trigger_workflow(submission):
    """
    Trigger workflow for a form submission
    """
    try:
        # Find workflows for this form
        workflows = WorkflowTemplate.objects.filter(
            form=submission.form,
            is_active=True
        )
        
        if not workflows.exists():
            logger.info(f"No active workflows found for form {submission.form.name}")
            return None
        
        # Use the first active workflow (could be enhanced to support multiple workflows)
        workflow = workflows.first()
        
        # Create workflow instance
        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            submission=submission,
            current_step=None,
            is_active=True
        )
        
        # Start the workflow
        start_workflow(instance)
        
        logger.info(f"Workflow {workflow.name} triggered for submission {submission.id}")
        return instance
        
    except Exception as e:
        logger.error(f"Error triggering workflow for submission {submission.id}: {str(e)}")
        return None

def start_workflow(instance):
    """
    Start a workflow instance by moving to the first step
    """
    try:
        # Get the first step (lowest order)
        first_step = instance.workflow.steps.filter(
            order__gte=0
        ).order_by('order').first()
        
        if not first_step:
            logger.warning(f"No steps found for workflow {instance.workflow.name}")
            return False
        
        # Check if step conditions are met
        if not evaluate_step_conditions(first_step, instance.submission):
            # Find next eligible step
            first_step = get_next_eligible_step(instance.workflow, instance.submission, 0)
        
        if first_step:
            # Move to first step
            instance.current_step = first_step
            instance.save()
            
            # Update submission status
            instance.submission.status = 'pending'
            if first_step.assigned_to_user:
                instance.submission.assigned_to = first_step.assigned_to_user
            instance.submission.save()
            
            # Send notifications
            send_step_notifications(instance, first_step)
            
            # Handle auto-approval if configured
            handle_auto_approval(instance, first_step)
            
            logger.info(f"Workflow instance {instance.id} started at step {first_step.name}")
            return True
        else:
            logger.warning(f"No eligible first step found for workflow {instance.workflow.name}")
            return False
            
    except Exception as e:
        logger.error(f"Error starting workflow instance {instance.id}: {str(e)}")
        return False

def handle_workflow_action(instance, action, user, comment="", delegate_to=None):
    """
    Handle a workflow action (approve, reject, request info, etc.)
    """
    try:
        current_step = instance.current_step
        
        if not current_step:
            return {
                'success': False,
                'error': 'No current step found'
            }
        
        # Validate user permissions
        if not can_user_perform_action(user, current_step, action):
            return {
                'success': False,
                'error': 'User does not have permission to perform this action'
            }
        
        # Handle delegation
        if action.action_type == 'delegate' and delegate_to:
            current_step.assigned_to_user = delegate_to
            current_step.save()
            
            # Send notification to delegate
            send_delegation_notification(instance, delegate_to, user, comment)
            
            return {
                'success': True,
                'message': f'Task delegated to {delegate_to.get_full_name()}'
            }
        
        # Handle other actions
        if action.action_type == 'approve':
            return handle_approval(instance, action, user, comment)
        elif action.action_type == 'reject':
            return handle_rejection(instance, action, user, comment)
        elif action.action_type == 'request_info':
            return handle_info_request(instance, action, user, comment)
        else:
            return {
                'success': False,
                'error': f'Unknown action type: {action.action_type}'
            }
            
    except Exception as e:
        logger.error(f"Error handling workflow action: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def handle_approval(instance, action, user, comment):
    """Handle approval action"""
    try:
        current_step = instance.current_step
        
        # Check if this step requires all approvals
        if current_step.require_all_approvals:
            # Mark this user's approval
            # TODO: Implement multi-user approval tracking
            pass
        
        # Get next step
        next_step = get_next_step(instance, action)
        
        if next_step:
            # Move to next step
            instance.current_step = next_step
            instance.save()
            
            # Update assignment
            if next_step.assigned_to_user:
                instance.submission.assigned_to = next_step.assigned_to_user
                instance.submission.save()
            
            # Send notifications for new step
            send_step_notifications(instance, next_step)
            
            return {
                'success': True,
                'message': f'Approved and moved to {next_step.name}'
            }
        else:
            # Workflow completed
            complete_workflow(instance, 'approved')
            
            return {
                'success': True,
                'message': 'Workflow completed - approved'
            }
            
    except Exception as e:
        logger.error(f"Error handling approval: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def handle_rejection(instance, action, user, comment):
    """Handle rejection action"""
    try:
        # Complete workflow with rejection
        complete_workflow(instance, 'rejected')
        
        # Send rejection notification
        send_rejection_notification(instance, user, comment)
        
        return {
            'success': True,
            'message': 'Request rejected'
        }
        
    except Exception as e:
        logger.error(f"Error handling rejection: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def handle_info_request(instance, action, user, comment):
    """Handle information request action"""
    try:
        # Send info request notification to submitter
        send_info_request_notification(instance, user, comment)
        
        # Update submission status
        instance.submission.status = 'pending_info'
        instance.submission.save()
        
        return {
            'success': True,
            'message': 'Information requested from submitter'
        }
        
    except Exception as e:
        logger.error(f"Error handling info request: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_next_step(instance, action):
    """Get the next step in the workflow"""
    try:
        current_step = instance.current_step
        
        # Check if action specifies next step
        if action.next_step:
            return action.next_step
        
        # Get next step by order
        next_step = instance.workflow.steps.filter(
            order__gt=current_step.order
        ).order_by('order').first()
        
        # Check conditions for next step
        if next_step and not evaluate_step_conditions(next_step, instance.submission):
            # Find next eligible step
            return get_next_eligible_step(instance.workflow, instance.submission, current_step.order)
        
        return next_step
        
    except Exception as e:
        logger.error(f"Error getting next step: {str(e)}")
        return None

def get_next_eligible_step(workflow, submission, current_order):
    """Find the next eligible step based on conditions"""
    try:
        steps = workflow.steps.filter(
            order__gt=current_order
        ).order_by('order')
        
        for step in steps:
            if evaluate_step_conditions(step, submission):
                return step
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding next eligible step: {str(e)}")
        return None

def evaluate_step_conditions(step, submission):
    """Evaluate if step conditions are met"""
    try:
        if not step.condition:
            return True
        
        # Simple condition evaluation
        # Can be enhanced to support complex conditions
        condition = step.condition
        
        if 'field' in condition and 'value' in condition:
            field_name = condition['field']
            expected_value = condition['value']
            operator = condition.get('operator', 'equals')
            
            actual_value = submission.data.get(field_name)
            
            if operator == 'equals':
                return str(actual_value) == str(expected_value)
            elif operator == 'not_equals':
                return str(actual_value) != str(expected_value)
            elif operator == 'greater_than':
                return float(actual_value) > float(expected_value)
            elif operator == 'less_than':
                return float(actual_value) < float(expected_value)
            elif operator == 'contains':
                return expected_value in str(actual_value)
        
        return True
        
    except Exception as e:
        logger.error(f"Error evaluating step conditions: {str(e)}")
        return True  # Default to allowing step

def can_user_perform_action(user, step, action):
    """Check if user can perform the action on this step"""
    try:
        # Check if user is assigned to step
        if step.assigned_to_user == user:
            return True
        
        # Check if user is in assigned group
        if step.assigned_to_group and user.groups.filter(id=step.assigned_to_group.id).exists():
            return True
        
        # Check if user has specific role
        if step.assigned_to_role and hasattr(user, 'role') and user.role == step.assigned_to_role:
            return True
        
        # Superusers can perform any action
        if user.is_superuser:
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking user permissions: {str(e)}")
        return False

def complete_workflow(instance, status):
    """Complete a workflow instance"""
    try:
        instance.is_active = False
        instance.completed_at = timezone.now()
        instance.current_step = None
        instance.save()
        
        # Update submission status
        instance.submission.status = status
        instance.submission.save()
        
        # Send completion notification
        send_completion_notification(instance, status)
        
        logger.info(f"Workflow instance {instance.id} completed with status {status}")
        
    except Exception as e:
        logger.error(f"Error completing workflow: {str(e)}")

def handle_auto_approval(instance, step):
    """Handle automatic approval if conditions are met"""
    try:
        if not step.auto_approve_after:
            return
        
        # Schedule auto-approval task
        from .tasks import auto_approve_workflows
        auto_approve_workflows.apply_async(
            args=[instance.id],
            countdown=step.auto_approve_after * 3600  # Convert hours to seconds
        )
        
    except Exception as e:
        logger.error(f"Error setting up auto-approval: {str(e)}")

# Notification functions
def send_step_notifications(instance, step):
    """Send notifications for a new workflow step"""
    try:
        # Get recipients
        recipients = []
        
        if step.assigned_to_user:
            recipients.append(step.assigned_to_user.email)
        
        if step.assigned_to_group:
            group_emails = step.assigned_to_group.user_set.values_list('email', flat=True)
            recipients.extend(group_emails)
        
        if not recipients:
            return
        
        # Prepare email context
        context = {
            'instance': instance,
            'step': step,
            'submission': instance.submission,
            'form': instance.submission.form,
        }
        
        # Render email template
        subject = f'New approval required: {instance.submission.form.name}'
        html_message = render_to_string('emails/workflow_notification.html', context)
        plain_message = render_to_string('emails/workflow_notification.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=True
        )
        
        logger.info(f"Step notification sent to {len(recipients)} recipients")
        
    except Exception as e:
        logger.error(f"Error sending step notifications: {str(e)}")

def send_completion_notification(instance, status):
    """Send notification when workflow is completed"""
    try:
        # Notify submitter
        context = {
            'instance': instance,
            'submission': instance.submission,
            'form': instance.submission.form,
            'status': status,
        }
        
        subject = f'Form submission {status}: {instance.submission.form.name}'
        html_message = render_to_string('emails/workflow_completed.html', context)
        plain_message = render_to_string('emails/workflow_completed.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.submission.submitted_by.email],
            html_message=html_message,
            fail_silently=True
        )
        
        logger.info(f"Completion notification sent for workflow {instance.id}")
        
    except Exception as e:
        logger.error(f"Error sending completion notification: {str(e)}")

def send_delegation_notification(instance, delegate_to, delegated_by, comment):
    """Send notification when task is delegated"""
    try:
        context = {
            'instance': instance,
            'delegate_to': delegate_to,
            'delegated_by': delegated_by,
            'comment': comment,
        }
        
        subject = f'Task delegated to you: {instance.submission.form.name}'
        html_message = render_to_string('emails/workflow_delegation.html', context)
        plain_message = render_to_string('emails/workflow_delegation.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[delegate_to.email],
            html_message=html_message,
            fail_silently=True
        )
        
    except Exception as e:
        logger.error(f"Error sending delegation notification: {str(e)}")

def send_rejection_notification(instance, rejected_by, comment):
    """Send notification when request is rejected"""
    try:
        context = {
            'instance': instance,
            'rejected_by': rejected_by,
            'comment': comment,
        }
        
        subject = f'Form submission rejected: {instance.submission.form.name}'
        html_message = render_to_string('emails/workflow_rejection.html', context)
        plain_message = render_to_string('emails/workflow_rejection.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.submission.submitted_by.email],
            html_message=html_message,
            fail_silently=True
        )
        
    except Exception as e:
        logger.error(f"Error sending rejection notification: {str(e)}")

def send_info_request_notification(instance, requested_by, comment):
    """Send notification when additional information is requested"""
    try:
        context = {
            'instance': instance,
            'requested_by': requested_by,
            'comment': comment,
        }
        
        subject = f'Additional information required: {instance.submission.form.name}'
        html_message = render_to_string('emails/workflow_info_request.html', context)
        plain_message = render_to_string('emails/workflow_info_request.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.submission.submitted_by.email],
            html_message=html_message,
            fail_silently=True
        )
        
    except Exception as e:
        logger.error(f"Error sending info request notification: {str(e)}")