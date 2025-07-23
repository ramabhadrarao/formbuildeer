# apps/forms_builder/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import FormSubmission


@shared_task
def cleanup_old_submissions():
    """Clean up old draft submissions"""
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = FormSubmission.objects.filter(
        status='draft',
        submitted_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} old draft submissions"


@shared_task
def send_submission_notification(submission_id):
    """Send email notification for new submission"""
    try:
        submission = FormSubmission.objects.get(id=submission_id)
        
        # Send to form creator
        context = {
            'submission': submission,
            'form': submission.form,
            'submitted_by': submission.submitted_by,
        }
        
        html_message = render_to_string('emails/new_submission.html', context)
        
        send_mail(
            subject=f'New submission for {submission.form.name}',
            message=f'New submission received from {submission.submitted_by.get_full_name()}',
            from_email='noreply@dynamicforms.com',
            recipient_list=[submission.form.created_by.email],
            html_message=html_message,
        )
        
        return f"Notification sent for submission {submission_id}"
    except FormSubmission.DoesNotExist:
        return f"Submission {submission_id} not found"


@shared_task
def generate_analytics_report():
    """Generate weekly analytics report"""
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Q
    
    User = get_user_model()
    
    # Get data for the past week
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    # Get submission statistics
    submissions = FormSubmission.objects.filter(
        submitted_at__range=[start_date, end_date]
    )
    
    stats = {
        'total_submissions': submissions.count(),
        'completed_submissions': submissions.filter(status='completed').count(),
        'pending_submissions': submissions.filter(status='pending').count(),
        'top_forms': submissions.values('form__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5],
    }
    
    # Send report to admins
    admins = User.objects.filter(is_superuser=True)
    
    for admin in admins:
        context = {
            'admin': admin,
            'stats': stats,
            'start_date': start_date,
            'end_date': end_date,
        }
        
        html_message = render_to_string('emails/analytics_report.html', context)
        
        send_mail(
            subject='Weekly Analytics Report - Dynamic Forms',
            message='Please find attached the weekly analytics report.',
            from_email='noreply@dynamicforms.com',
            recipient_list=[admin.email],
            html_message=html_message,
        )
    
    return f"Analytics report sent to {admins.count()} administrators"


@shared_task
def process_file_upload(file_id):
    """Process uploaded files (e.g., virus scan, thumbnail generation)"""
    from .models import FormFile
    
    try:
        form_file = FormFile.objects.get(id=file_id)
        
        # Add file processing logic here
        # For example: virus scanning, image optimization, etc.
        
        return f"Processed file {file_id}"
    except FormFile.DoesNotExist:
        return f"File {file_id} not found"