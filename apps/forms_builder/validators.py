# apps/forms_builder/validators.py
import re
from django.core.exceptions import ValidationError
from datetime import datetime


class DynamicFieldValidator:
    """Handles dynamic validation for form fields based on rules"""
    
    def __init__(self, form_template):
        self.form_template = form_template
        self.fields = {field.name: field for field in form_template.fields.all()}
        
    def validate_submission(self, data):
        """Validate entire form submission"""
        errors = {}
        
        for field_name, field in self.fields.items():
            # Skip if field is not visible based on conditions
            if not self._is_field_visible(field, data):
                continue
                
            value = data.get(field_name)
            field_errors = self._validate_field(field, value, data)
            
            if field_errors:
                errors[field_name] = field_errors
                
        return errors
    
    def _is_field_visible(self, field, data):
        """Check if field should be visible based on conditions"""
        if not field.show_if:
            return True
            
        for dependent_field, condition in field.show_if.items():
            dependent_value = data.get(dependent_field)
            
            if isinstance(condition, dict):
                operator = condition.get('operator', 'equals')
                expected_value = condition.get('value')
                
                if operator == 'equals' and dependent_value != expected_value:
                    return False
                elif operator == 'not_equals' and dependent_value == expected_value:
                    return False
                elif operator == 'contains' and expected_value not in str(dependent_value):
                    return False
                elif operator == 'greater_than' and float(dependent_value) <= float(expected_value):
                    return False
                elif operator == 'less_than' and float(dependent_value) >= float(expected_value):
                    return False
            else:
                if dependent_value != condition:
                    return False
                    
        return True
    
    def _validate_field(self, field, value, all_data):
        """Validate a single field"""
        errors = []
        
        # Required validation
        if field.required and not value:
            errors.append(f"{field.label} is required")
            
        if not value:
            return errors
            
        # Type-specific validation
        if field.field_type == 'email':
            if not self._validate_email(value):
                errors.append("Please enter a valid email address")
                
        elif field.field_type == 'number':
            try:
                num_value = float(value)
                if field.min_value and num_value < float(field.min_value):
                    errors.append(f"Value must be at least {field.min_value}")
                if field.max_value and num_value > float(field.max_value):
                    errors.append(f"Value must be at most {field.max_value}")
            except ValueError:
                errors.append("Please enter a valid number")
                
        elif field.field_type in ['text', 'textarea']:
            if field.min_length and len(value) < field.min_length:
                errors.append(f"Minimum length is {field.min_length} characters")
            if field.max_length and len(value) > field.max_length:
                errors.append(f"Maximum length is {field.max_length} characters")
                
        # Regex pattern validation
        if field.regex_pattern:
            if not re.match(field.regex_pattern, str(value)):
                errors.append("Invalid format")
                
        # Custom validation rules
        for rule in field.validation_rules.all():
            rule_error = self._validate_rule(rule, value, all_data)
            if rule_error:
                errors.append(rule_error)
                
        return errors
    
    def _validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_rule(self, rule, value, all_data):
        """Validate custom validation rule"""
        if rule.rule_type == 'required_if':
            # Check if field should be required based on condition
            condition_met = self._evaluate_condition(rule.condition, all_data)
            if condition_met and not value:
                return rule.error_message or "This field is required"
                
        elif rule.rule_type == 'min_if':
            condition_met = self._evaluate_condition(rule.condition, all_data)
            if condition_met and float(value) < float(rule.value):
                return rule.error_message or f"Minimum value is {rule.value}"
                
        elif rule.rule_type == 'max_if':
            condition_met = self._evaluate_condition(rule.condition, all_data)
            if condition_met and float(value) > float(rule.value):
                return rule.error_message or f"Maximum value is {rule.value}"
                
        elif rule.rule_type == 'pattern_if':
            condition_met = self._evaluate_condition(rule.condition, all_data)
            if condition_met and not re.match(rule.value, str(value)):
                return rule.error_message or "Invalid format"
                
        return None
    
    def _evaluate_condition(self, condition, data):
        """Evaluate condition for conditional validation"""
        if 'field' in condition and 'value' in condition:
            field_value = data.get(condition['field'])
            expected_value = condition['value']
            operator = condition.get('operator', 'equals')
            
            if operator == 'equals':
                return str(field_value) == str(expected_value)
            elif operator == 'not_equals':
                return str(field_value) != str(expected_value)
            elif operator == 'greater_than':
                return float(field_value) > float(expected_value)
            elif operator == 'less_than':
                return float(field_value) < float(expected_value)
            elif operator == 'contains':
                return expected_value in str(field_value)
                
        return True