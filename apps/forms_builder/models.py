from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from colorfield.fields import ColorField
import uuid

User = get_user_model()

class FormTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_forms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)
    category = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=50, default='file-text')
    color = ColorField(default='#3498db')
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("can_publish_form", "Can publish form"),
            ("can_archive_form", "Can archive form"),
        ]
    
    def __str__(self):
        return self.name

class FormField(models.Model):
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('number', 'Number'),
        ('email', 'Email'),
        ('date', 'Date'),
        ('datetime', 'Date Time'),
        ('select', 'Dropdown'),
        ('multiselect', 'Multi Select'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkbox'),
        ('file', 'File Upload'),
        ('image', 'Image Upload'),
        ('lookup', 'Lookup Field'),
        ('nested', 'Nested Form'),
        ('signature', 'Signature'),
        ('location', 'Location'),
        ('rating', 'Rating'),
        ('richtext', 'Rich Text Editor'),
    ]
    
    form = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='fields')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    label = models.CharField(max_length=200)
    name = models.CharField(max_length=100)
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=500, blank=True)
    required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    default_value = models.TextField(blank=True)
    
    # Field constraints
    min_value = models.CharField(max_length=50, blank=True)
    max_value = models.CharField(max_length=50, blank=True)
    min_length = models.IntegerField(null=True, blank=True)
    max_length = models.IntegerField(null=True, blank=True)
    regex_pattern = models.CharField(max_length=500, blank=True)
    
    # For select/multiselect fields
    choices = models.JSONField(default=list, blank=True)
    
    # For lookup fields
    lookup_model = models.CharField(max_length=100, blank=True)
    lookup_field = models.CharField(max_length=100, blank=True)
    
    # For nested forms
    nested_form = models.ForeignKey(FormTemplate, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='nested_in')
    allow_multiple = models.BooleanField(default=False)
    
    # Conditional logic
    show_if = models.JSONField(default=dict, blank=True)
    
    # Styling
    width = models.CharField(max_length=20, default='full')
    css_class = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['form', 'name']
    
    def __str__(self):
        return f"{self.form.name} - {self.label}"

class FormValidationRule(models.Model):
    RULE_TYPES = [
        ('required_if', 'Required If'),
        ('min_if', 'Minimum If'),
        ('max_if', 'Maximum If'),
        ('pattern_if', 'Pattern If'),
        ('custom', 'Custom Validation'),
    ]
    
    field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name='validation_rules')
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    condition = models.JSONField(default=dict)
    value = models.CharField(max_length=500)
    error_message = models.CharField(max_length=500)
    
    def __str__(self):
        return f"{self.field.label} - {self.rule_type}"

class FormSubmission(models.Model):
    form = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='submissions')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=50, default='draft')
    
    # Workflow tracking
    current_step = models.CharField(max_length=100, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='assigned_submissions')
    
    class Meta:
        ordering = ['-submitted_at']
        permissions = [
            ("can_approve_submission", "Can approve submission"),
            ("can_reject_submission", "Can reject submission"),
        ]
    
    def __str__(self):
        return f"{self.form.name} - {self.submitted_by.username} - {self.submitted_at}"

class FormFile(models.Model):
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='files')
    field_name = models.CharField(max_length=100)
    file = models.FileField(upload_to='form_uploads/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.submission.id} - {self.field_name}"

class FormFieldPermission(models.Model):
    PERMISSION_TYPES = [
        ('view', 'View'),
        ('edit', 'Edit'),
        ('required', 'Required'),
    ]
    
    field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey('auth.Group', on_delete=models.CASCADE, null=True, blank=True)
    permission_type = models.CharField(max_length=20, choices=PERMISSION_TYPES)
    
    class Meta:
        unique_together = ['field', 'user', 'group', 'permission_type']