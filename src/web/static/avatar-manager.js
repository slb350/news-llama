/**
 * Avatar Manager - Shared avatar upload functionality
 *
 * Handles file validation, preview, and upload for profile avatars.
 * Used by both profile_create.html and profile_settings.html.
 */

export const AvatarManager = {
    /**
     * Handle avatar file selection with validation and preview
     * @param {HTMLInputElement} input - File input element
     * @param {string} previewId - ID of avatar preview element
     * @param {string} statusId - ID of status message element (optional for profile_create)
     * @param {boolean} uploadImmediately - Whether to upload right away (settings) or wait (creation)
     * @returns {Promise<File|null>} - Selected file if valid
     */
    async handleAvatarSelect(input, previewId, statusId, uploadImmediately = false) {
        const file = input.files[0];
        const statusEl = statusId ? document.getElementById(statusId) : null;
        const avatarPreview = document.getElementById(previewId);

        if (!file) return null;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            if (statusEl) {
                statusEl.textContent = 'Please select an image file';
                statusEl.className = 'text-xs mt-1 text-red-600';
            }
            return null;
        }

        // Validate file size (500KB max)
        if (file.size > 500 * 1024) {
            if (statusEl) {
                statusEl.textContent = 'File size must be less than 500KB';
                statusEl.className = 'text-xs mt-1 text-red-600';
            }
            return null;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            avatarPreview.innerHTML = `<img src="${e.target.result}" alt="Avatar preview" class="w-full h-full object-cover rounded-full">`;
        };
        reader.readAsDataURL(file);

        if (uploadImmediately) {
            return await this.uploadAvatar(file, statusEl);
        } else {
            if (statusEl) {
                statusEl.textContent = 'Avatar ready to upload';
                statusEl.className = 'text-xs mt-1 text-green-600';
            }
            return file;
        }
    },

    /**
     * Upload avatar to server
     * @param {File} file - Avatar file
     * @param {HTMLElement} statusEl - Status message element (optional)
     * @returns {Promise<File|null>} - File on success, null on failure
     */
    async uploadAvatar(file, statusEl = null) {
        if (statusEl) {
            statusEl.textContent = 'Uploading...';
            statusEl.className = 'text-xs mt-1 text-blue-600';
        }

        const formData = new FormData();
        formData.append('avatar', file);

        try {
            const response = await fetch('/profile/avatar', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                if (statusEl) {
                    statusEl.textContent = 'Avatar uploaded successfully!';
                    statusEl.className = 'text-xs mt-1 text-green-600';
                }
                return file;
            } else {
                // Parse error message from backend
                let errorMessage = 'Upload failed. Please try again.';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorMessage;
                } catch {
                    // Response wasn't JSON
                }
                if (statusEl) {
                    statusEl.textContent = errorMessage;
                    statusEl.className = 'text-xs mt-1 text-red-600';
                }
                NewsLlama.showToast(errorMessage, 'error');
                return null;
            }
        } catch (error) {
            console.error('Avatar upload error:', error.message);
            const errorMessage = 'Network error. Please check your connection.';
            if (statusEl) {
                statusEl.textContent = errorMessage;
                statusEl.className = 'text-xs mt-1 text-red-600';
            }
            NewsLlama.showToast(errorMessage, 'error');
            return null;
        }
    }
};
