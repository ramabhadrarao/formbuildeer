# dynamic_forms_project/celery.py
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dynamic_forms_project.settings')

# Create the Celery app
app = Celery('dynamic_forms_project')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat Schedule (for periodic tasks)
app.conf.beat_schedule = {
    'cleanup-old-submissions': {
        'task': 'apps.forms_builder.tasks.cleanup_old_submissions',
        'schedule': 86400.0,  # Run daily
    },
    'send-reminder-emails': {
        'task': 'apps.workflow.tasks.send_reminder_emails',
        'schedule': 3600.0,  # Run hourly
    },
    'generate-analytics-report': {
        'task': 'apps.forms_builder.tasks.generate_analytics_report',
        'schedule': 604800.0,  # Run weekly
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')