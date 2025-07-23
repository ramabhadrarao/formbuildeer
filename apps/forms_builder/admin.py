from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import nested_admin
from import_export.admin import ImportExportModelAdmin
from .models import (FormTemplate, FormField, FormValidationRule, 
                    FormSubmission, FormFile, FormFieldPermission)

class FormValidationRuleInline(nested_admin.NestedTabularInline):
    model = FormValidationRule
    extra = 0
    classes = ['collapse']

class FormFieldPermissionInline(nested_admin.NestedTabularInline):
    model = FormFieldPermission
    extra = 0
    classes = ['collapse']

class FormFieldInline(nested_admin.NestedStackedInline):
    model = FormField
    extra = 0
    inlines = [FormValidationRuleInline, FormFieldPermissionInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('field_type', 'label', 'name', 'order', 'required')
        }),
        ('Field Configuration', {
            'fields': ('placeholder', 'help_text', 'default_value', 'width', 'css_class'),
            'classes': ('collapse',)
        }),
        ('Constraints', {
            'fields': ('min_value', 'max_value', 'min_length', 'max_length', 'regex_pattern'),
            'classes': ('collapse',)
        }),
        ('Choices & Lookups', {
            'fields': ('choices', 'lookup_model', 'lookup_field', 'nested_form', 'allow_multiple'),
            'classes': ('collapse',)
        }),
        ('Conditional Logic', {
            'fields': ('show_if',),
            'classes': ('collapse',)
        }),
    )

@admin.register(FormTemplate)
class FormTemplateAdmin(nested_admin.NestedModelAdmin, ImportExportModelAdmin):
    list_display = ['name', 'category', 'color_display', 'created_by', 'created_at', 
                   'is_active', 'version', 'actions_display']
    list_filter = ['is_active', 'category', 'created_at', 'created_by']
    search_fields = ['name', 'description']
    inlines = [FormFieldInline]
    readonly_fields = ['created_at', 'updated_at', 'version']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'icon', 'color')
        }),
        ('Settings', {
            'fields': ('is_active', 'version', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; '
            'border-radius: 3px; display: inline-block;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'
    
    def actions_display(self, obj):
        preview_url = reverse('admin:form_preview', args=[obj.pk])
        clone_url = reverse('admin:form_clone', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">Preview</a>&nbsp;'
            '<a class="button" href="{}">Clone</a>',
            preview_url, clone_url
        )
    actions_display.short_description = 'Actions'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

class FormFileInline(admin.TabularInline):
    model = FormFile
    extra = 0
    readonly_fields = ['file', 'uploaded_at']

@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ['form', 'submitted_by', 'submitted_at', 'status', 
                   'current_step', 'assigned_to']
    list_filter = ['status', 'form', 'submitted_at']
    search_fields = ['submitted_by__username', 'submitted_by__email']
    readonly_fields = ['submitted_at', 'data_display']
    inlines = [FormFileInline]
    
    fieldsets = (
        ('Submission Information', {
            'fields': ('form', 'submitted_by', 'submitted_at', 'status')
        }),
        ('Workflow', {
            'fields': ('current_step', 'assigned_to')
        }),
        ('Data', {
            'fields': ('data_display',),
            'classes': ('wide',)
        }),
    )
    
    def data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.data, indent=2))
    data_display.short_description = 'Form Data'
    
    def has_change_permission(self, request, obj=None):
        if obj and hasattr(obj, 'workflow_instance'):
            # Check workflow permissions
            return request.user.has_perm('can_approve_submission')
        return super().has_change_permission(request, obj)