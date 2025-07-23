// Dynamic Forms Handler
class DynamicFormsManager {
    constructor() {
        this.formData = {};
        this.conditionalRules = {};
        this.validationRules = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeConditionalLogic();
        this.initializeValidation();
        this.initializeLookupFields();
        this.initializeFileUploads();
    }

    bindEvents() {
        // Field change events
        document.querySelectorAll('.dynamic-field').forEach(field => {
            field.addEventListener('change', (e) => this.handleFieldChange(e));
            field.addEventListener('input', (e) => this.handleFieldInput(e));
        });

        // Form submission
        document.querySelector('#dynamic-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmit();
        });
    }

    handleFieldChange(event) {
        const field = event.target;
        const fieldName = field.name;
        const fieldValue = field.value;

        // Update form data
        this.formData[fieldName] = fieldValue;

        // Check conditional logic
        this.evaluateConditionalLogic(fieldName);

        // Validate field
        this.validateField(field);
    }

    handleFieldInput(event) {
        const field = event.target;
        
        // Real-time validation for certain field types
        if (field.type === 'email' || field.type === 'tel' || field.dataset.realtime) {
            this.validateField(field);
        }
    }

    initializeConditionalLogic() {
        // Parse conditional rules from data attributes
        document.querySelectorAll('[data-show-if]').forEach(element => {
            const showIf = JSON.parse(element.dataset.showIf);
            this.conditionalRules[element.id] = showIf;
            
            // Initial evaluation
            this.evaluateElementVisibility(element, showIf);
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
            const fieldValue = this.formData[field] || document.querySelector(`[name="${field}"]`)?.value;
            
            if (typeof condition === 'object') {
                // Complex conditions
                if (condition.operator === 'equals') {
                    shouldShow = shouldShow && (fieldValue == condition.value);
                } else if (condition.operator === 'not_equals') {
                    shouldShow = shouldShow && (fieldValue != condition.value);
                } else if (condition.operator === 'contains') {
                    shouldShow = shouldShow && fieldValue?.includes(condition.value);
                } else if (condition.operator === 'greater_than') {
                    shouldShow = shouldShow && (parseFloat(fieldValue) > parseFloat(condition.value));
                } else if (condition.operator === 'less_than') {
                    shouldShow = shouldShow && (parseFloat(fieldValue) < parseFloat(condition.value));
                }
            } else {
                // Simple equality check
                shouldShow = shouldShow && (fieldValue == condition);
            }
        });

        // Show/hide with animation
        if (shouldShow) {
            element.style.display = 'block';
            element.classList.add('fade-in');
            element.querySelectorAll('input, select, textarea').forEach(field => {
                field.disabled = false;
            });
        } else {
            element.style.display = 'none';
            element.classList.remove('fade-in');
            element.querySelectorAll('input, select, textarea').forEach(field => {
                field.disabled = true;
            });
        }
    }

    initializeValidation() {
        // Parse validation rules
        document.querySelectorAll('[data-validation]').forEach(field => {
            const rules = JSON.parse(field.dataset.validation);
            this.validationRules[field.name] = rules;
        });
    }

    validateField(field) {
        const rules = this.validationRules[field.name];
        if (!rules) return true;

        const value = field.value;
        const errors = [];

        // Required validation
        if (rules.required && !value) {
            errors.push(rules.requiredMessage || 'This field is required');
        }

        // Min length
        if (rules.minLength && value.length < rules.minLength) {
            errors.push(`Minimum length is ${rules.minLength} characters`);
        }

        // Max length
        if (rules.maxLength && value.length > rules.maxLength) {
            errors.push(`Maximum length is ${rules.maxLength} characters`);
        }

        // Pattern matching
        if (rules.pattern && !new RegExp(rules.pattern).test(value)) {
            errors.push(rules.patternMessage || 'Invalid format');
        }

        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                errors.push('Please enter a valid email address');
            }
        }

        // Number range validation
        if (field.type === 'number' && value) {
            const numValue = parseFloat(value);
            if (rules.min !== undefined && numValue < rules.min) {
                errors.push(`Minimum value is ${rules.min}`);
            }
            if (rules.max !== undefined && numValue > rules.max) {
                errors.push(`Maximum value is ${rules.max}`);
            }
        }

        // Display errors
        this.displayFieldErrors(field, errors);

        return errors.length === 0;
    }

    displayFieldErrors(field, errors) {
        // Remove existing error messages
        const existingError = field.parentElement.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }

        // Remove error styling
        field.classList.remove('field-invalid');

        if (errors.length > 0) {
            // Add error styling
            field.classList.add('field-invalid');

            // Create error message element
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error';
            errorDiv.innerHTML = errors.map(error => `<span>${error}</span>`).join('<br>');
            
            field.parentElement.appendChild(errorDiv);
        }
    }

    initializeLookupFields() {
        document.querySelectorAll('.lookup-field').forEach(field => {
            const lookupUrl = field.dataset.lookupUrl;
            const minLength = parseInt(field.dataset.minLength) || 2;

            // Initialize autocomplete
            new Autocomplete(field, {
                source: async (query) => {
                    if (query.length < minLength) return [];
                    
                    try {
                        const response = await fetch(`${lookupUrl}?q=${encodeURIComponent(query)}`);
                        const data = await response.json();
                        return data.results;
                    } catch (error) {
                        console.error('Lookup error:', error);
                        return [];
                    }
                },
                onSelect: (item) => {
                    field.value = item.label;
                    field.dataset.selectedId = item.id;
                    this.handleFieldChange({ target: field });
                }
            });
        });
    }

    initializeFileUploads() {
        document.querySelectorAll('.file-upload-field').forEach(field => {
            const dropZone = field.closest('.file-drop-zone');
            const preview = field.parentElement.querySelector('.file-preview');
            const maxSize = parseInt(field.dataset.maxSize) || 10485760; // 10MB default
            const acceptedTypes = field.dataset.accept?.split(',') || [];

            // Drag and drop events
            if (dropZone) {
                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                    dropZone.addEventListener(eventName, (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                    });
                });

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

                dropZone.addEventListener('drop', (e) => {
                    const files = e.dataTransfer.files;
                    this.handleFileSelect(field, files, preview, maxSize, acceptedTypes);
                });
            }

            // File input change
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
            const fileExtension = '.' + file.name.split('.').pop();
            
            const isAccepted = acceptedTypes.some(type => {
                return type === fileType || type === fileExtension || 
                       (type.endsWith('/*') && fileType.startsWith(type.replace('/*', '')));
            });

            if (!isAccepted) {
                this.displayFieldErrors(field, [`File type not allowed. Accepted types: ${acceptedTypes.join(', ')}`]);
                return;
            }
        }

        // Clear errors
        this.displayFieldErrors(field, []);

        // Show preview
        if (preview) {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    preview.innerHTML = `<img src="${e.target.result}" alt="${file.name}" />`;
                };
                reader.readAsDataURL(file);
            } else {
                preview.innerHTML = `
                    <div class="file-info">
                        <i class="file-icon"></i>
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
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

    async handleFormSubmit() {
        // Validate all fields
        let isValid = true;
        document.querySelectorAll('.dynamic-field').forEach(field => {
            if (!field.disabled && !this.validateField(field)) {
                isValid = false;
            }
        });

        if (!isValid) {
            this.showNotification('Please fix the errors before submitting', 'error');
            return;
        }

        // Prepare form data
        const formData = new FormData();
        
        // Add regular fields
        Object.entries(this.formData).forEach(([key, value]) => {
            formData.append(key, value);
        });

        // Add file fields
        document.querySelectorAll('input[type="file"]').forEach(field => {
            if (field.files[0]) {
                formData.append(field.name, field.files[0]);
            }
        });

        // Submit form
        try {
            const response = await fetch('/api/forms/submit/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Form submitted successfully!', 'success');
                
                // Redirect or show success message
                if (result.redirect_url) {
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 1500);
                }
            } else {
                this.showNotification(result.message || 'Error submitting form', 'error');
            }
        } catch (error) {
            console.error('Submit error:', error);
            this.showNotification('An error occurred while submitting the form', 'error');
        }
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
}

// Autocomplete Helper Class
class Autocomplete {
    constructor(input, options) {
        this.input = input;
        this.options = options;
        this.wrapper = null;
        this.list = null;
        this.items = [];
        this.selectedIndex = -1;
        this.init();
    }

    init() {
        this.createWrapper();
        this.bindEvents();
    }

    createWrapper() {
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'autocomplete-wrapper';
        this.input.parentNode.insertBefore(this.wrapper, this.input);
        this.wrapper.appendChild(this.input);

        this.list = document.createElement('ul');
        this.list.className = 'autocomplete-list';
        this.wrapper.appendChild(this.list);
    }

    bindEvents() {
        this.input.addEventListener('input', debounce(() => this.handleInput(), 300));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('blur', () => setTimeout(() => this.hide(), 200));
        
        this.list.addEventListener('mousedown', (e) => {
            e.preventDefault();
        });
    }

    async handleInput() {
        const query = this.input.value;
        
        if (!query || query.length < 2) {
            this.hide();
            return;
        }

        const results = await this.options.source(query);
        this.showResults(results);
    }

    showResults(results) {
        this.items = results;
        this.selectedIndex = -1;
        
        this.list.innerHTML = '';
        
        if (results.length === 0) {
            this.hide();
            return;
        }

        results.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'autocomplete-item';
            li.textContent = item.label;
            li.dataset.index = index;
            
            li.addEventListener('click', () => this.selectItem(index));
            li.addEventListener('mouseenter', () => this.highlightItem(index));
            
            this.list.appendChild(li);
        });

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
                if (this.selectedIndex >= 0) {
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
        
        if (index < 0) index = items.length - 1;
        if (index >= items.length) index = 0;
        
        items.forEach(item => item.classList.remove('highlighted'));
        
        if (items[index]) {
            items[index].classList.add('highlighted');
            this.selectedIndex = index;
            
            // Scroll into view
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
}

// Utility function for debouncing
function debounce(func, wait) {
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

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    new DynamicFormsManager();
});