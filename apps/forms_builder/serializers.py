# apps/forms_builder/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FormTemplate, FormField, FormSubmission, FormFile, FormValidationRule
from .validators import DynamicFieldValidator

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'name', 'department']
    
    def get_name(self, obj):
        return obj.get_full_name() or obj.username


class FormValidationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormValidationRule
        fields = ['id', 'rule_type', 'condition', 'value', 'error_message']


class FormFieldSerializer(serializers.ModelSerializer):
    validation_rules = FormValidationRuleSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_view = serializers.SerializerMethodField()
    
    class Meta:
        model = FormField
        fields = [
            'id', 'field_type', 'label', 'name', 'placeholder', 'help_text',
            'required', 'order', 'default_value', 'min_value', 'max_value',
            'min_length', 'max_length', 'regex_pattern', 'choices',
            'lookup_model', 'lookup_field', 'nested_form', 'allow_multiple',
            'show_if', 'width', 'css_class', 'validation_rules',
            'can_edit', 'can_view'
        ]
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request:
            return True
        return obj.has_permission(request.user, 'edit')
    
    def get_can_view(self, obj):
        request = self.context.get('request')
        if not request:
            return True
        return obj.has_permission(request.user, 'view')


class FormTemplateSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    fields = FormFieldSerializer(many=True, read_only=True)
    submissions_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = FormTemplate
        fields = [
            'id', 'name', 'description', 'created_by', 'created_at',
            'updated_at', 'is_active', 'version', 'category', 'icon',
            'color', 'fields', 'submissions_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'version']


class FormSubmissionSerializer(serializers.ModelSerializer):
    form = FormTemplateSerializer(read_only=True)
    submitted_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    files = serializers.SerializerMethodField()
    workflow_status = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form', 'submitted_by', 'submitted_at', 'data',
            'status', 'current_step', 'assigned_to', 'files',
            'workflow_status'
        ]
        read_only_fields = ['submitted_at']
    
    def get_files(self, obj):
        return [
            {
                'field_name': file.field_name,
                'url': file.file.url,
                'name': file.file.name.split('/')[-1],
                'uploaded_at': file.uploaded_at
            }
            for file in obj.files.all()
        ]
    
    def get_workflow_status(self, obj):
        if hasattr(obj, 'workflow_instance'):
            instance = obj.workflow_instance
            return {
                'workflow': instance.workflow.name,
                'current_step': instance.current_step.name if instance.current_step else None,
                'is_active': instance.is_active,
                'started_at': instance.started_at,
                'completed_at': instance.completed_at
            }
        return None


class FormSubmitSerializer(serializers.Serializer):
    """Serializer for form submission"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically add fields based on form template
        form = self.context.get('form')
        if form:
            for field in form.fields.all():
                field_kwargs = {
                    'required': field.required,
                    'allow_blank': not field.required,
                    'allow_null': not field.required,
                    'help_text': field.help_text,
                    'label': field.label,
                }
                
                # Create appropriate field type
                if field.field_type == 'text':
                    serializer_field = serializers.CharField(**field_kwargs)
                elif field.field_type == 'textarea':
                    serializer_field = serializers.CharField(**field_kwargs)
                elif field.field_type == 'number':
                    serializer_field = serializers.DecimalField(
                        max_digits=10, decimal_places=2, **field_kwargs
                    )
                elif field.field_type == 'email':
                    serializer_field = serializers.EmailField(**field_kwargs)
                elif field.field_type == 'date':
                    serializer_field = serializers.DateField(**field_kwargs)
                elif field.field_type == 'datetime':
                    serializer_field = serializers.DateTimeField(**field_kwargs)
                elif field.field_type == 'checkbox':
                    serializer_field = serializers.BooleanField(**field_kwargs)
                elif field.field_type in ['select', 'radio']:
                    serializer_field = serializers.ChoiceField(
                        choices=[(c['value'], c['label']) for c in field.choices],
                        **field_kwargs
                    )
                elif field.field_type == 'multiselect':
                    serializer_field = serializers.MultipleChoiceField(
                        choices=[(c['value'], c['label']) for c in field.choices],
                        **field_kwargs
                    )
                elif field.field_type == 'file':
                    serializer_field = serializers.FileField(**field_kwargs)
                elif field.field_type == 'image':
                    serializer_field = serializers.ImageField(**field_kwargs)
                else:
                    serializer_field = serializers.CharField(**field_kwargs)
                
                # Add validators
                validators = []
                if field.min_value:
                    validators.append(
                        serializers.MinValueValidator(float(field.min_value))
                    )
                if field.max_value:
                    validators.append(
                        serializers.MaxValueValidator(float(field.max_value))
                    )
                if field.min_length:
                    validators.append(
                        serializers.MinLengthValidator(field.min_length)
                    )
                if field.max_length:
                    validators.append(
                        serializers.MaxLengthValidator(field.max_length)
                    )
                if field.regex_pattern:
                    validators.append(
                        serializers.RegexValidator(field.regex_pattern)
                    )
                
                if validators:
                    serializer_field.validators.extend(validators)
                
                self.fields[field.name] = serializer_field
    
    def validate(self, attrs):
        # Custom validation based on form rules
        form = self.context.get('form')
        validator = DynamicFieldValidator(form)
        
        # Validate all fields
        errors = validator.validate_submission(attrs)
        if errors:
            raise serializers.ValidationError(errors)
        
        return attrs
    
    def create(self, validated_data):
        form = self.context.get('form')
        request = self.context.get('request')
        
        submission = FormSubmission.objects.create(
            form=form,
            submitted_by=request.user,
            data=validated_data,
            status='pending'
        )
        
        return submission


class WorkflowActionSerializer(serializers.Serializer):
    """Serializer for workflow actions"""
    action = serializers.ChoiceField(choices=['approve', 'reject', 'request_info'])
    comment = serializers.CharField(required=False, allow_blank=True)
    delegate_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    
    def validate(self, attrs):
        action = attrs.get('action')
        comment = attrs.get('comment')
        
        # Some actions might require comments
        if action == 'reject' and not comment:
            raise serializers.ValidationError({
                'comment': 'Comment is required when rejecting'
            })
        
        return attrs