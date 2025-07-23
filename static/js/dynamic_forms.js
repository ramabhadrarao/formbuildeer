// 
// FILE: static/js/dynamic_forms.js
// PURPOSE: Enhanced dynamic forms handling with advanced features
//

class DynamicFormsManager {
    constructor() {
        this.formData = {};
        this.conditionalRules = {};
        this.validationRules = {};
        this.nestedForms = {};
        this.lookupCache = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeConditionalLogic();
        this.initializeValidation();
        this.initializeLookupFields();
        this.initializeFileUploads();
        this.initializeNestedForms();
        this.setupAutosave();
    }

    bindEvents() {
        // Field change events
        document.querySelectorAll('.dynamic-field').forEach(field => {
            field.addEventListener('change', (e) => this.handleFieldChange(e));
            field.addEventListener('input', (e) => this.handleFieldInput(e));
            field.addEventListener('blur', (e) => this.handleFieldBlur(e));
        });

        // Form submission
        const form = document.querySelector('#dynamicForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleFormSubmit();
            });
        }

        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }

    handleFieldChange(event) {
        const field = event.target;
        const fieldName = field.name;
        let fieldValue = field.value;

        // Handle different field types
        if (field.type === 'checkbox') {
            fieldValue = field.checked;
        } else if (field.type === 'radio') {
            fieldValue = field.checked ? field.value : null;
        } else if (field.multiple) {
            fieldValue = Array.from(field.selectedOptions).map(option => option.value);
        }

        // Update form data
        this.formData[fieldName] = fieldValue;

        // Check conditional logic
        this.evaluateConditionalLogic(fieldName);

        // Validate field
        this.validateField(field);

        // Trigger dependent calculations
        this.handleDependentCalculations(fieldName);

        // Save to localStorage for recovery
        this.saveFormState();
    }

    handleFieldInput(event) {
        const field = event.target;
        
        // Real-time validation for certain field types
        if (field.type === 'email' || field.type === 'tel' || field.dataset.realtime) {
            this.debounce(() => this.validateField(field), 300)();
        }

        // Update character count for text areas
        if (field.tagName === 'TEXTAREA') {
            this.updateCharacterCount(field);
        }
    }

    handleFieldBlur(event) {
        const field = event.target;
        
        // Format field value on blur
        this.formatFieldValue(field);
        
        // Validate field
        this.validateField(field);
    }

    initializeConditionalLogic() {
        // Parse conditional rules from data attributes
        document.querySelectorAll('[data-show-if]').forEach(element => {
            try {
                const showIf = JSON.parse(element.dataset.showIf);
                this.conditionalRules[element.id] = showIf;
                
                // Initial evaluation
                this.evaluateElementVisibility(element, showIf);
            } catch (e) {
                console.warn('Invalid conditional logic for element:', element.id, e);
            }
        });
    }

    evaluateConditionalLogic(triggerField) {
        Object.entries(this.conditionalRules).forEach(([elementId, rules]) => {
            const element = document.getElementById(elementId);
            if (element) {
                this.evaluateElementVisibility(element, rules);
            }
        });
    }

    evaluateElementVisibility(element, rules) {
        let shouldShow = true;

        Object.entries(rules).forEach(([field, condition]) => {
            const fieldValue = this.getFieldValue(field);
            
            if (typeof condition === 'object') {
                // Complex conditions
                const operator = condition.operator || 'equals';
                const expectedValue = condition.value;
                
                switch (operator) {
                    case 'equals':
                        shouldShow = shouldShow && (fieldValue == expectedValue);
                        break;
                    case 'not_equals':
                        shouldShow = shouldShow && (fieldValue != expectedValue);
                        break;
                    case 'contains':
                        shouldShow = shouldShow && fieldValue?.toString().includes(expectedValue);
                        break;
                    case 'not_contains':
                        shouldShow = shouldShow && !fieldValue?.toString().includes(expectedValue);
                        break;
                    case 'greater_than':
                        shouldShow = shouldShow && (parseFloat(fieldValue) > parseFloat(expectedValue));
                        break;
                    case 'less_than':
                        shouldShow = shouldShow && (parseFloat(fieldValue) < parseFloat(expectedValue));
                        break;
                    case 'greater_equal':
                        shouldShow = shouldShow && (parseFloat(fieldValue) >= parseFloat(expectedValue));
                        break;
                    case 'less_equal':
                        shouldShow = shouldShow && (parseFloat(fieldValue) <= parseFloat(expectedValue));
                        break;
                    case 'empty':
                        shouldShow = shouldShow && (!fieldValue || fieldValue.toString().trim() === '');
                        break;
                    case 'not_empty':
                        shouldShow = shouldShow && (fieldValue && fieldValue.toString().trim() !== '');
                        break;
                    case 'in':
                        shouldShow = shouldShow && Array.isArray(expectedValue) && expectedValue.includes(fieldValue);
                        break;
                    case 'not_in':
                        shouldShow = shouldShow && (!Array.isArray(expectedValue) || !expectedValue.includes(fieldValue));
                        break;
                }
            } else {
                // Simple equality check
                shouldShow = shouldShow && (fieldValue == condition);
            }
        });

        // Show/hide with animation
        this.toggleElementVisibility(element, shouldShow);
    }

    toggleElementVisibility(element, shouldShow) {
        const isCurrentlyVisible = !element.classList.contains('hidden');
        
        if (shouldShow && !isCurrentlyVisible) {
            element.classList.remove('hidden');
            element.classList.add('fade-in');
            element.querySelectorAll('input, select, textarea').forEach(field => {
                field.disabled = false;
            });
        } else if (!shouldShow && isCurrentlyVisible) {
            element.classList.add('hidden');
            element.classList.remove('fade-in');
            element.querySelectorAll('input, select, textarea').forEach(field => {
                field.disabled = true;
                // Clear validation errors for hidden fields
                this.clearFieldErrors(field);
            });
        }
    }

    getFieldValue(fieldName) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (!field) return null;
        
        if (field.type === 'checkbox') {
            return field.checked;
        } else if (field.type === 'radio') {
            const checkedRadio = document.querySelector(`[name="${fieldName}"]:checked`);
            return checkedRadio ? checkedRadio.value : null;
        } else if (field.multiple) {
            return Array.from(field.selectedOptions).map(option => option.value);
        }
        
        return field.value;
    }

    initializeValidation() {
        // Parse validation rules
        document.querySelectorAll('[data-validation]').forEach(field => {
            try {
                const rules = JSON.parse(field.dataset.validation);
                this.validationRules[field.name] = rules;
            } catch (e) {
                console.warn('Invalid validation rules for field:', field.name, e);
            }
        });
    }

    validateField(field) {
        const rules = this.validationRules[field.name] || {};
        const value = field.value;
        const errors = [];

        // Skip validation for disabled or hidden fields
        if (field.disabled || field.closest('.hidden')) {
            this.clearFieldErrors(field);
            return true;
        }

        // Required validation
        if (field.required && this.isEmpty(value)) {
            errors.push('This field is required');
        }

        if (!this.isEmpty(value)) {
            // Type-specific validation
            if (field.type === 'email') {
                if (!this.isValidEmail(value)) {
                    errors.push('Please enter a valid email address');
                }
            } else if (field.type === 'url') {
                if (!this.isValidUrl(value)) {
                    errors.push('Please enter a valid URL');
                }
            } else if (field.type === 'tel') {
                if (!this.isValidPhone(value)) {
                    errors.push('Please enter a valid phone number');
                }
            }

            // Length validation
            if (rules.minLength && value.length < rules.minLength) {
                errors.push(`Minimum length is ${rules.minLength} characters`);
            }
            if (rules.maxLength && value.length > rules.maxLength) {
                errors.push(`Maximum length is ${rules.maxLength} characters`);
            }

            // Number validation
            if (field.type === 'number' || rules.numeric) {
                const numValue = parseFloat(value);
                if (isNaN(numValue)) {
                    errors.push('Please enter a valid number');
                } else {
                    if (rules.min !== undefined && numValue < rules.min) {
                        errors.push(`Minimum value is ${rules.min}`);
                    }
                    if (rules.max !== undefined && numValue > rules.max) {
                        errors.push(`Maximum value is ${rules.max}`);
                    }
                }
            }

            // Pattern validation
            if (rules.pattern) {
                try {
                    const regex = new RegExp(rules.pattern);
                    if (!regex.test(value)) {
                        errors.push(rules.patternMessage || 'Invalid format');
                    }
                } catch (e) {
                    console.warn('Invalid regex pattern:', rules.pattern);
                }
            }

            // Custom validation functions
            if (rules.custom) {
                try {
                    const customResult = this.runCustomValidation(rules.custom, value, field);
                    if (customResult !== true) {
                        errors.push(customResult || 'Invalid value');
                    }
                } catch (e) {
                    console.warn('Custom validation error:', e);
                }
            }
        }

        // Display errors
        this.displayFieldErrors(field, errors);

        return errors.length === 0;
    }

    isEmpty(value) {
        return value === null || value === undefined || value.toString().trim() === '';
    }

    isValidEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    }

    isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    isValidPhone(phone) {
        const regex = /^[\+]?[1-9][\d]{0,15}$/;
        return regex.test(phone.replace(/[\s\-\(\)]/g, ''));
    }

    runCustomValidation(customFunction, value, field) {
        // This could be expanded to support custom validation functions
        // For now, return true
        return true;
    }

    displayFieldErrors(field, errors) {
        // Remove existing error messages
        this.clearFieldErrors(field);

        if (errors.length > 0) {
            // Add error styling
            field.classList.add('field-invalid');

            // Create error message element
            const errorDiv = document.getElementById(`error_${field.name}`);
            if (errorDiv) {
                errorDiv.innerHTML = errors.map(error => `<span>${error}</span>`).join('<br>');
                errorDiv.style.display = 'block';
            }
        }
    }

    clearFieldErrors(field) {
        field.classList.remove('field-invalid');
        const errorDiv = document.getElementById(`error_${field.name}`);
        if (errorDiv) {
            errorDiv.innerHTML = '';
            errorDiv.style.display = 'none';
        }
    }

    initializeLookupFields() {
        document.querySelectorAll('.lookup-field').forEach(field => {
            const lookupUrl = field.dataset.lookupUrl;
            const minLength = parseInt(field.dataset.minLength) || 2;

            if (!lookupUrl) return;

            // Create autocomplete wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'autocomplete-wrapper';
            field.parentNode.insertBefore(wrapper, field);
            wrapper.appendChild(field);

            const list = document.createElement('ul');
            list.className = 'autocomplete-list';
            wrapper.appendChild(list);

            let selectedIndex = -1;
            let currentItems = [];

            // Input event handler
            field.addEventListener('input', this.debounce(async () => {
                const query = field.value.trim();
                
                if (query.length < minLength) {
                    this.hideLookupResults(list);
                    return;
                }

                // Check cache first
                const cacheKey = `${lookupUrl}_${query}`;
                let results;
                
                if (this.lookupCache[cacheKey]) {
                    results = this.lookupCache[cacheKey];
                } else {
                    try {
                        const response = await fetch(`${lookupUrl}?q=${encodeURIComponent(query)}`);
                        const data = await response.json();
                        results = data.results || [];
                        
                        // Cache results
                        this.lookupCache[cacheKey] = results;
                    } catch (error) {
                        console.error('Lookup error:', error);
                        results = [];
                    }
                }

                this.showLookupResults(list, results, field);
                currentItems = results;
                selectedIndex = -1;
            }, 300));

            // Keyboard navigation
            field.addEventListener('keydown', (e) => {
                if (!list.style.display || list.style.display === 'none') return;

                switch (e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        selectedIndex = Math.min(selectedIndex + 1, currentItems.length - 1);
                        this.highlightLookupItem(list, selectedIndex);
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        selectedIndex = Math.max(selectedIndex - 1, -1);
                        this.highlightLookupItem(list, selectedIndex);
                        break;
                    case 'Enter':
                        e.preventDefault();
                        if (selectedIndex >= 0 && currentItems[selectedIndex]) {
                            this.selectLookupItem(field, currentItems[selectedIndex], list);
                        }
                        break;
                    case 'Escape':
                        this.hideLookupResults(list);
                        break;
                }
            });

            // Hide results on blur (with delay for click handling)
            field.addEventListener('blur', () => {
                setTimeout(() => this.hideLookupResults(list), 200);
            });
        });
    }

    showLookupResults(list, results, field) {
        list.innerHTML = '';
        
        if (results.length === 0) {
            list.style.display = 'none';
            return;
        }

        results.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'autocomplete-item';
            li.innerHTML = `
                <div class="fw-bold">${this.escapeHtml(item.label)}</div>
                ${item.description ? `<small class="text-muted">${this.escapeHtml(item.description)}</small>` : ''}
            `;
            
            li.addEventListener('click', () => {
                this.selectLookupItem(field, item, list);
            });
            
            list.appendChild(li);
        });

        list.style.display = 'block';
    }

    highlightLookupItem(list, index) {
        const items = list.querySelectorAll('.autocomplete-item');
        items.forEach(item => item.classList.remove('highlighted'));
        
        if (index >= 0 && items[index]) {
            items[index].classList.add('highlighted');
            items[index].scrollIntoView({ block: 'nearest' });
        }
    }

    selectLookupItem(field, item, list) {
        field.value = item.label;
        field.dataset.selectedId = item.id;
        field.dataset.selectedValue = item.value || item.id;
        
        this.hideLookupResults(list);
        this.handleFieldChange({ target: field });
    }

    hideLookupResults(list) {
        list.style.display = 'none';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    initializeFileUploads() {
        document.querySelectorAll('.file-upload-field').forEach(field => {
            const dropZone = field.closest('.file-drop-zone');
            const preview = document.getElementById(`preview_${field.name}`);
            const maxSize = parseInt(field.dataset.maxSize) || 10485760; // 10MB default
            const acceptedTypes = field.dataset.accept?.split(',') || [];

            if (!dropZone) return;

            // Prevent default drag behaviors
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                });
            });

            // Highlight drop zone when item is dragged over it
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, () => {
                    dropZone.classList.add('drag-over');
                });
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, () => {
                    dropZone.classList.remove('drag-over');
                });
            });

            // Handle dropped files
            dropZone.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                this.handleFileSelect(field, files, preview, maxSize, acceptedTypes);
            });

            // Handle file input change
            field.addEventListener('change', (e) => {
                this.handleFileSelect(field, e.target.files, preview, maxSize, acceptedTypes);
            });
        });
    }

    handleFileSelect(field, files, preview, maxSize, acceptedTypes) {
        const file = files[0];
        if (!file) return;

        // Validate file size
        if (file.size > maxSize) {
            this.displayFieldErrors(field, [`File size must be less than ${this.formatFileSize(maxSize)}`]);
            return;
        }

        // Validate file type
        if (acceptedTypes.length > 0) {
            const fileType = file.type;
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            
            const isAccepted = acceptedTypes.some(type => {
                type = type.trim().toLowerCase();
                return type === fileType || 
                       type === fileExtension || 
                       (type.endsWith('/*') && fileType.startsWith(type.replace('/*', '')));
            });

            if (!isAccepted) {
                this.displayFieldErrors(field, [`File type not allowed. Accepted types: ${acceptedTypes.join(', ')}`]);
                return;
            }
        }

        // Clear errors
        this.clearFieldErrors(field);

        // Show preview
        if (preview) {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    preview.innerHTML = `
                        <div class="d-flex align-items-center gap-3">
                            <img src="${e.target.result}" alt="${file.name}" style="width: 100px; height: 100px; object-fit: cover; border-radius: 0.5rem;" />
                            <div class="flex-grow-1">
                                <div class="fw-bold">${file.name}</div>
                                <div class="text-muted small">${this.formatFileSize(file.size)}</div>
                                <button type="button" class="btn btn-sm btn-outline-danger mt-1" onclick="this.parentElement.parentElement.parentElement.innerHTML=''; document.getElementById('${field.id}').value='';">
                                    <i class="fas fa-trash me-1"></i>Remove
                                </button>
                            </div>
                        </div>
                    `;
                };
                reader.readAsDataURL(file);
            } else {
                preview.innerHTML = `
                    <div class="file-info">
                        <i class="fas fa-file fa-2x text-primary me-3"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold">${file.name}</div>
                            <div class="text-muted small">${this.formatFileSize(file.size)}</div>
                            <button type="button" class="btn btn-sm btn-outline-danger mt-1" onclick="this.parentElement.parentElement.innerHTML=''; document.getElementById('${field.id}').value='';">
                                <i class="fas fa-trash me-1"></i>Remove
                            </button>
                        </div>
                    </div>
                `;
            }
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    initializeNestedForms() {
        document.querySelectorAll('.nested-form').forEach(nestedForm => {
            const formId = nestedForm.dataset.formId;
            const container = nestedForm.querySelector('.nested-form-container');
            const addButton = nestedForm.querySelector('.add-nested-row');
            
            if (!formId || !container) return;

            // Initialize with one row
            this.addNestedRow(container, formId);

            // Add row button handler
            if (addButton) {
                addButton.addEventListener('click', () => {
                    this.addNestedRow(container, formId);
                });
            }
        });
    }

    addNestedRow(container, formId) {
        const rowIndex = container.children.length;
        const rowElement = document.createElement('div');
        rowElement.className = 'nested-row';
        rowElement.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="mb-0">Row ${rowIndex + 1}</h6>
                <button type="button" class="btn btn-sm btn-outline-danger remove-nested-row">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
            <div class="nested-fields">
                <!-- Nested fields will be loaded here -->
                <p class="text-muted">Loading nested form fields...</p>
            </div>
        `;

        container.appendChild(rowElement);

        // Add remove handler
        const removeButton = rowElement.querySelector('.remove-nested-row');
        removeButton.addEventListener('click', () => {
            rowElement.remove();
            this.updateNestedRowNumbers(container);
        });

        // TODO: Load actual nested form fields via AJAX
        // This would require an endpoint to return form fields
        setTimeout(() => {
            const fieldsContainer = rowElement.querySelector('.nested-fields');
            fieldsContainer.innerHTML = `
                <div class="row">
                    <div class="col-md-6 mb-2">
                        <input type="text" class="form-control form-control-sm" placeholder="Field 1" name="nested_${formId}_${rowIndex}_field1">
                    </div>
                    <div class="col-md-6 mb-2">
                        <input type="text" class="form-control form-control-sm" placeholder="Field 2" name="nested_${formId}_${rowIndex}_field2">
                    </div>
                </div>
            `;
        }, 500);
    }

    updateNestedRowNumbers(container) {
        const rows = container.querySelectorAll('.nested-row');
        rows.forEach((row, index) => {
            const title = row.querySelector('h6');
            if (title) {
                title.textContent = `Row ${index + 1}`;
            }
        });
    }

    setupAutosave() {
        // Auto-save form data every 30 seconds
        setInterval(() => {
            this.saveFormState();
        }, 30000);

        // Save on page unload
        window.addEventListener('beforeunload', () => {
            this.saveFormState();
        });

        // Load saved state on page load
        this.loadFormState();
    }

    saveFormState() {
        const formData = {};
        document.querySelectorAll('.dynamic-field').forEach(field => {
            if (field.type === 'checkbox') {
                formData[field.name] = field.checked;
            } else if (field.type === 'radio') {
                if (field.checked) {
                    formData[field.name] = field.value;
                }
            } else {
                formData[field.name] = field.value;
            }
        });

        const formId = document.querySelector('#dynamicForm')?.dataset.formId || 'default';
        localStorage.setItem(`form_autosave_${formId}`, JSON.stringify({
            data: formData,
            timestamp: Date.now()
        }));
    }

    loadFormState() {
        const formId = document.querySelector('#dynamicForm')?.dataset.formId || 'default';
        const saved = localStorage.getItem(`form_autosave_${formId}`);
        
        if (!saved) return;

        try {
            const { data, timestamp } = JSON.parse(saved);
            
            // Only restore if saved within last 24 hours
            if (Date.now() - timestamp > 24 * 60 * 60 * 1000) {
                localStorage.removeItem(`form_autosave_${formId}`);
                return;
            }

            // Show restore prompt
            if (Object.keys(data).length > 0) {
                this.showRestorePrompt(data, formId);
            }
        } catch (e) {
            console.warn('Error loading form state:', e);
        }
    }

    showRestorePrompt(data, formId) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-history me-2"></i>Restore Previous Session
                        </h5>
                    </div>
                    <div class="modal-body">
                        <p>We found a previous session of this form. Would you like to restore your previous input?</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-action="dismiss">Start Fresh</button>
                        <button type="button" class="btn btn-primary" data-action="restore">Restore Previous Input</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        modal.addEventListener('click', (e) => {
            if (e.target.dataset.action === 'restore') {
                this.restoreFormData(data);
                bootstrapModal.hide();
            } else if (e.target.dataset.action === 'dismiss') {
                localStorage.removeItem(`form_autosave_${formId}`);
                bootstrapModal.hide();
            }
        });

        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    restoreFormData(data) {
        Object.entries(data).forEach(([fieldName, value]) => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            if (field.type === 'checkbox') {
                field.checked = value;
            } else if (field.type === 'radio') {
                if (field.value === value) {
                    field.checked = true;
                }
            } else if (field.multiple) {
                Array.from(field.options).forEach(option => {
                    option.selected = Array.isArray(value) && value.includes(option.value);
                });
            } else {
                field.value = value;
            }

            // Trigger change event to update conditional logic
            this.handleFieldChange({ target: field });
        });

        this.showNotification('Previous form data has been restored', 'success');
    }

    handleDependentCalculations(triggerField) {
        // Handle calculated fields based on other field values
        document.querySelectorAll('[data-calculate]').forEach(calcField => {
            try {
                const formula = calcField.dataset.calculate;
                const result = this.evaluateFormula(formula);
                if (result !== null) {
                    calcField.value = result;
                    this.handleFieldChange({ target: calcField });
                }
            } catch (e) {
                console.warn('Calculation error:', e);
            }
        });
    }

    evaluateFormula(formula) {
        // Simple formula evaluation - can be extended
        // Example: {field1} + {field2} * 0.1
        let expression = formula;
        
        // Replace field references with actual values
        const fieldMatches = formula.match(/\{([^}]+)\}/g);
        if (fieldMatches) {
            fieldMatches.forEach(match => {
                const fieldName = match.slice(1, -1);
                const value = parseFloat(this.getFieldValue(fieldName)) || 0;
                expression = expression.replace(match, value);
            });
        }

        // Evaluate mathematical expression (basic implementation)
        try {
            // Only allow safe mathematical operations
            if (/^[0-9+\-*/.() ]+$/.test(expression)) {
                return eval(expression);
            }
        } catch (e) {
            console.warn('Formula evaluation error:', e);
        }
        
        return null;
    }

    formatFieldValue(field) {
        // Format field values based on type
        if (field.type === 'tel') {
            field.value = this.formatPhoneNumber(field.value);
        } else if (field.classList.contains('currency')) {
            field.value = this.formatCurrency(field.value);
        } else if (field.classList.contains('percentage')) {
            field.value = this.formatPercentage(field.value);
        }
    }

    formatPhoneNumber(phone) {
        // Basic phone number formatting
        const cleaned = phone.replace(/\D/g, '');
        if (cleaned.length === 10) {
            return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
        }
        return phone;
    }

    formatCurrency(value) {
        const num = parseFloat(value.replace(/[^0-9.-]/g, ''));
        if (isNaN(num)) return value;
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(num);
    }

    formatPercentage(value) {
        const num = parseFloat(value.replace(/[^0-9.-]/g, ''));
        if (isNaN(num)) return value;
        return num + '%';
    }

    updateCharacterCount(field) {
        const maxLength = field.getAttribute('maxlength');
        if (!maxLength) return;

        let counter = field.parentElement.querySelector('.character-count');
        if (!counter) {
            counter = document.createElement('div');
            counter.className = 'character-count text-muted small mt-1';
            field.parentElement.appendChild(counter);
        }

        const remaining = maxLength - field.value.length;
        counter.textContent = `${field.value.length}/${maxLength} characters`;
        
        if (remaining < 10) {
            counter.classList.add('text-warning');
        } else {
            counter.classList.remove('text-warning');
        }
    }

    handleKeyboardShortcuts(event) {
        // Ctrl+S to save (prevent default and trigger autosave)
        if (event.ctrlKey && event.key === 's') {
            event.preventDefault();
            this.saveFormState();
            this.showNotification('Form progress saved', 'info');
        }
        
        // Ctrl+Enter to submit
        if (event.ctrlKey && event.key === 'Enter') {
            event.preventDefault();
            this.handleFormSubmit();
        }
    }

    async handleFormSubmit() {
        const form = document.querySelector('#dynamicForm');
        const submitBtn = document.querySelector('#submitBtn');
        const loadingOverlay = document.querySelector('#loadingOverlay');
        
        if (!form) return;

        // Validate all visible fields
        let isValid = true;
        const visibleFields = Array.from(form.querySelectorAll('.dynamic-field'))
            .filter(field => !field.disabled && !field.closest('.hidden'));

        visibleFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        if (!isValid) {
            this.showNotification('Please fix the errors before submitting', 'error');
            // Scroll to first error
            const firstError = form.querySelector('.field-invalid');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstError.focus();
            }
            return;
        }

        // Show loading state
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Submitting...';
        }
        
        if (loadingOverlay) {
            loadingOverlay.classList.add('show');
        }

        try {
            // Prepare form data
            const formData = new FormData(form);
            
            // Add lookup field selected IDs
            document.querySelectorAll('.lookup-field[data-selected-id]').forEach(field => {
                formData.append(`${field.name}_id`, field.dataset.selectedId);
            });

            // Submit form
            const response = await fetch(form.action || window.location.pathname, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                // Clear autosave data
                const formId = form.dataset.formId || 'default';
                localStorage.removeItem(`form_autosave_${formId}`);
                
                // Show success message
                this.showSuccessModal(result);
                
                // Reset form if needed
                if (result.reset_form) {
                    form.reset();
                    this.formData = {};
                }
                
                // Redirect if specified
                if (result.redirect_url) {
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 2000);
                }
                
            } else {
                // Handle validation errors
                if (result.errors) {
                    Object.entries(result.errors).forEach(([fieldName, errors]) => {
                        const field = document.querySelector(`[name="${fieldName}"]`);
                        if (field) {
                            this.displayFieldErrors(field, Array.isArray(errors) ? errors : [errors]);
                        }
                    });
                    this.showNotification('Please correct the errors and try again', 'error');
                } else {
                    this.showNotification(result.message || 'An error occurred while submitting the form', 'error');
                }
            }

        } catch (error) {
            console.error('Submit error:', error);
            this.showNotification('A network error occurred. Please try again.', 'error');
        } finally {
            // Hide loading state
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Submit Form';
            }
            
            if (loadingOverlay) {
                loadingOverlay.classList.remove('show');
            }
        }
    }

    showSuccessModal(result) {
        const modal = document.querySelector('#successModal');
        if (modal) {
            const bootstrapModal = new bootstrap.Modal(modal);
            
            // Update modal content if needed
            const modalBody = modal.querySelector('.modal-body');
            if (result.message && modalBody) {
                const messageP = modalBody.querySelector('p');
                if (messageP) {
                    messageP.textContent = result.message;
                }
            }
            
            bootstrapModal.show();
        } else {
            this.showNotification('Form submitted successfully!', 'success');
        }
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    showNotification(message, type = 'info') {
        // Remove existing notifications
        document.querySelectorAll('.notification').forEach(n => n.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icon = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        }[type] || 'info-circle';
        
        notification.innerHTML = `
            <i class="fas fa-${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close btn-close-white ms-auto" onclick="this.parentElement.remove()"></button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }, 5000);
    }

    // Utility function for debouncing
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Enhanced Autocomplete class for lookup fields
class EnhancedAutocomplete {
    constructor(input, options) {
        this.input = input;
        this.options = options;
        this.wrapper = null;
        this.list = null;
        this.items = [];
        this.selectedIndex = -1;
        this.cache = new Map();
        this.init();
    }

    init() {
        this.createWrapper();
        this.bindEvents();
    }

    createWrapper() {
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'autocomplete-wrapper position-relative';
        this.input.parentNode.insertBefore(this.wrapper, this.input);
        this.wrapper.appendChild(this.input);

        this.list = document.createElement('ul');
        this.list.className = 'autocomplete-list position-absolute w-100 list-unstyled m-0 p-0 bg-white border rounded shadow-sm';
        this.list.style.zIndex = '1050';
        this.list.style.maxHeight = '200px';
        this.list.style.overflowY = 'auto';
        this.list.style.display = 'none';
        this.wrapper.appendChild(this.list);
    }

    bindEvents() {
        let searchTimeout;
        
        this.input.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => this.handleInput(), 300);
        });
        
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('blur', () => setTimeout(() => this.hide(), 200));
        this.input.addEventListener('focus', () => {
            if (this.items.length > 0) {
                this.show();
            }
        });
        
        this.list.addEventListener('mousedown', (e) => e.preventDefault());
    }

    async handleInput() {
        const query = this.input.value.trim();
        
        if (!query || query.length < (this.options.minLength || 2)) {
            this.hide();
            return;
        }

        // Check cache
        if (this.cache.has(query)) {
            this.showResults(this.cache.get(query));
            return;
        }

        try {
            const results = await this.options.source(query);
            this.cache.set(query, results);
            this.showResults(results);
        } catch (error) {
            console.error('Autocomplete error:', error);
            this.showResults([]);
        }
    }

    showResults(results) {
        this.items = results;
        this.selectedIndex = -1;
        
        this.list.innerHTML = '';
        
        if (results.length === 0) {
            const li = document.createElement('li');
            li.className = 'autocomplete-item p-2 text-muted';
            li.textContent = 'No results found';
            this.list.appendChild(li);
        } else {
            results.forEach((item, index) => {
                const li = document.createElement('li');
                li.className = 'autocomplete-item p-2 cursor-pointer border-bottom';
                li.style.cursor = 'pointer';
                li.innerHTML = `
                    <div class="fw-bold">${this.escapeHtml(item.label)}</div>
                    ${item.description ? `<small class="text-muted">${this.escapeHtml(item.description)}</small>` : ''}
                `;
                
                li.addEventListener('click', () => this.selectItem(index));
                li.addEventListener('mouseenter', () => this.highlightItem(index));
                
                this.list.appendChild(li);
            });
        }

        this.show();
    }

    handleKeydown(e) {
        if (!this.isVisible()) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.highlightItem(this.selectedIndex + 1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.highlightItem(this.selectedIndex - 1);
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.items[this.selectedIndex]) {
                    this.selectItem(this.selectedIndex);
                }
                break;
            case 'Escape':
                this.hide();
                break;
        }
    }

    highlightItem(index) {
        const items = this.list.querySelectorAll('.autocomplete-item');
        
        if (this.items.length === 0) return;
        
        if (index < 0) index = items.length - 1;
        if (index >= items.length) index = 0;
        
        items.forEach(item => item.classList.remove('highlighted', 'bg-light'));
        
        if (items[index] && this.items[index]) {
            items[index].classList.add('highlighted', 'bg-light');
            this.selectedIndex = index;
            items[index].scrollIntoView({ block: 'nearest' });
        }
    }

    selectItem(index) {
        const item = this.items[index];
        if (item && this.options.onSelect) {
            this.options.onSelect(item);
            this.hide();
        }
    }

    show() {
        this.list.style.display = 'block';
    }

    hide() {
        this.list.style.display = 'none';
    }

    isVisible() {
        return this.list.style.display === 'block';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on a form page
    if (document.querySelector('#dynamicForm')) {
        window.dynamicFormsManager = new DynamicFormsManager();
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DynamicFormsManager, EnhancedAutocomplete };
}