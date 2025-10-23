/**
 * Interest Manager - Shared interest selection functionality
 *
 * Handles interest selection, removal, and display for user profiles.
 * Used by both profile_create.html and profile_settings.html.
 */

export class InterestManager {
    constructor() {
        this.selectedInterests = new Set();
    }

    /**
     * Initialize with existing interests
     * @param {string[]} interests - Array of interest names
     */
    initialize(interests = []) {
        this.selectedInterests = new Set(interests);
        this.updateDisplay();
    }

    /**
     * Toggle interest selection
     * @param {HTMLElement|null} button - Grid button element (if clicked from grid)
     * @param {string} interest - Interest name
     */
    toggle(button, interest) {
        if (this.selectedInterests.has(interest)) {
            this.selectedInterests.delete(interest);
            if (button) button.classList.remove('selected');
        } else {
            this.selectedInterests.add(interest);
            if (button) button.classList.add('selected');
        }
        this.updateDisplay();
    }

    /**
     * Remove interest
     * @param {string} interest - Interest to remove
     */
    remove(interest) {
        this.selectedInterests.delete(interest);
        // Also remove 'selected' class from grid button if it exists
        document.querySelectorAll('.interest-tag').forEach(btn => {
            if (btn.textContent.trim() === interest) {
                btn.classList.remove('selected');
            }
        });
        this.updateDisplay();
    }

    /**
     * Add custom interest from input
     * @param {string} inputId - ID of input element
     */
    addCustom(inputId) {
        const input = document.getElementById(inputId);
        const interest = input.value.trim();
        if (interest && interest.length > 0) {
            this.selectedInterests.add(interest);
            this.updateDisplay();
            input.value = '';
        }
    }

    /**
     * Update the selected interests display
     */
    updateDisplay() {
        const container = document.getElementById('selected-interests');
        container.innerHTML = '';

        if (this.selectedInterests.size === 0) {
            const span = document.createElement('span');
            span.className = 'text-xs text-gray-500 empty-state';
            span.textContent = 'No interests selected yet. Add your interests to personalize your news!';
            container.appendChild(span);
        } else {
            Array.from(this.selectedInterests).forEach(interest => {
                const span = document.createElement('span');
                span.className = 'interest-tag cursor-pointer hover:opacity-80';
                span.textContent = interest;  // Safe - sets text, not HTML
                span.dataset.interest = interest;  // Safe - use data attribute
                container.appendChild(span);
            });
        }
    }

    /**
     * Get selected interests as array
     * @returns {string[]}
     */
    getSelected() {
        return Array.from(this.selectedInterests);
    }
}
