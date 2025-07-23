from django.db import models
from django.contrib.auth import get_user_model
from apps.forms_builder.models import FormTemplate, FormSubmission

User = get_user_model()

class WorkflowTemplate(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    form = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='workflows')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class WorkflowStep(models.Model):
    STEP_TYPES = [
        ('approval', 'Approval'),
        ('review', 'Review'),
        ('notification', 'Notification'),
        ('condition', 'Conditional'),
        ('parallel', 'Parallel Approval'),
    ]
    
    workflow = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name='steps')
    name = models.CharField(max_length=200)
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    order = models.IntegerField(default=0)
    
    # Assignee options
    assigned_to_user = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='workflow_steps')
    assigned_to_group = models.ForeignKey('auth.Group', on_delete=models.SET_NULL, 
                                        null=True, blank=True)
    assigned_to_role = models.CharField(max_length=100, blank=True)
    
    # Step configuration
    auto_approve_after = models.IntegerField(null=True, blank=True, help_text="Hours")
    require_all_approvals = models.BooleanField(default=False)
    can_edit_form = models.BooleanField(default=False)
    notification_template = models.TextField(blank=True)
    
    # Conditional logic
    condition = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.workflow.name} - {self.name}"

class WorkflowAction(models.Model):
    ACTION_TYPES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('request_info', 'Request Information'),
        ('delegate', 'Delegate'),
    ]
    
    step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    name = models.CharField(max_length=100)
    next_step = models.ForeignKey(WorkflowStep, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='previous_actions')
    require_comment = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.step.name} - {self.name}"

class WorkflowInstance(models.Model):
    workflow = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE)
    submission = models.OneToOneField(FormSubmission, on_delete=models.CASCADE, 
                                    related_name='workflow_instance')
    current_step = models.ForeignKey(WorkflowStep, on_delete=models.SET_NULL, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.workflow.name} - {self.submission.id}"

class WorkflowHistory(models.Model):
    instance = models.ForeignKey(WorkflowInstance, on_delete=models.CASCADE, 
                               related_name='history')
    step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE)
    action = models.ForeignKey(WorkflowAction, on_delete=models.CASCADE)
    actor = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)
    data_before = models.JSONField(default=dict, blank=True)
    data_after = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']