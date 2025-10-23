/**
 * Form Accessibility Helper
 *
 * Provides accessible form validation with ARIA announcements
 * and proper error messaging for screen readers.
 */

export class FormAccessibility {
    /**
     * Set up accessible validation for a text input
     * @param {string} inputId - ID of the input element
     * @param {string} errorMessage - Error message to display
     */
    static setupTextInput(inputId, errorMessage) {
        const input = document.getElementById(inputId);
        if (!input) return;

        // Create error message element if it doesn't exist
        let errorEl = document.getElementById(`${inputId}-error`);
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.id = `${inputId}-error`;
            errorEl.className = 'text-xs text-red-600 mt-1';
            errorEl.setAttribute('role', 'alert');
            errorEl.setAttribute('aria-live', 'polite');
            input.parentNode.insertBefore(errorEl, input.nextSibling);
        }

        // Set ARIA attributes
        input.setAttribute('aria-describedby', `${inputId}-error`);
        input.setAttribute('aria-invalid', 'false');

        // Show error on invalid input
        input.addEventListener('invalid', function(e) {
            e.preventDefault();
            errorEl.textContent = errorMessage;
            this.setAttribute('aria-invalid', 'true');
        });

        // Clear error on valid input
        input.addEventListener('input', function() {
            if (this.validity.valid && this.value.trim()) {
                errorEl.textContent = '';
                this.setAttribute('aria-invalid', 'false');
            }
        });

        // Clear error on blur if valid
        input.addEventListener('blur', function() {
            if (this.validity.valid) {
                errorEl.textContent = '';
                this.setAttribute('aria-invalid', 'false');
            }
        });
    }

    /**
     * Set up accessible validation for file input
     * @param {string} inputId - ID of the input element
     */
    static setupFileInput(inputId) {
        const input = document.getElementById(inputId);
        if (!input) return;

        // File inputs already have status elements from avatar-manager
        // Just ensure ARIA attributes are set
        input.setAttribute('aria-invalid', 'false');

        // The avatar-manager.js already handles validation messages
        // We just need to ensure they're announced to screen readers
    }
}
