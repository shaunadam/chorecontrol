/**
 * ChoreControl - Main JavaScript functionality
 */

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash');
    if (flashMessages.length > 0) {
        setTimeout(function() {
            flashMessages.forEach(function(flash) {
                flash.style.transition = 'opacity 0.5s';
                flash.style.opacity = '0';
                setTimeout(function() {
                    flash.remove();
                }, 500);
            });
        }, 5000);
    }
});

// Form validation helpers
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(function(field) {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });

    return isValid;
}

// Add error styling for invalid inputs
const style = document.createElement('style');
style.textContent = `
    .form-input.error,
    .form-select.error,
    .form-textarea.error {
        border-color: var(--danger-color);
        box-shadow: 0 0 0 3px rgba(229, 57, 53, 0.1);
    }
`;
document.head.appendChild(style);

// Handle form submissions with loading state
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Loading...';

                // Re-enable after 3 seconds as fallback
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.textContent = submitBtn.dataset.originalText || 'Submit';
                }, 3000);
            }
        });
    });
});

// Confirm dangerous actions
function confirmAction(message) {
    return confirm(message || 'Are you sure you want to do this?');
}

// Toast notification system (lightweight alternative to flash messages)
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `flash flash-${type}`;
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '10000';
    toast.style.minWidth = '250px';
    toast.style.animation = 'slideIn 0.3s ease-out';

    document.body.appendChild(toast);

    setTimeout(function() {
        toast.style.transition = 'opacity 0.5s';
        toast.style.opacity = '0';
        setTimeout(function() {
            toast.remove();
        }, 500);
    }, 3000);
}

// Add slide-in animation
const animationStyle = document.createElement('style');
animationStyle.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(animationStyle);

// Debounce helper for search/filter inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = function() {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Local storage helpers for saving user preferences
const Storage = {
    get: function(key) {
        try {
            return JSON.parse(localStorage.getItem('chorecontrol_' + key));
        } catch (e) {
            return null;
        }
    },
    set: function(key, value) {
        try {
            localStorage.setItem('chorecontrol_' + key, JSON.stringify(value));
        } catch (e) {
            console.error('Failed to save to localStorage', e);
        }
    },
    remove: function(key) {
        try {
            localStorage.removeItem('chorecontrol_' + key);
        } catch (e) {
            console.error('Failed to remove from localStorage', e);
        }
    }
};

// Remember filter selections
document.addEventListener('DOMContentLoaded', function() {
    const filterSelects = document.querySelectorAll('select[name]');
    filterSelects.forEach(function(select) {
        const savedValue = Storage.get('filter_' + select.name);
        if (savedValue && !select.value) {
            select.value = savedValue;
        }

        select.addEventListener('change', function() {
            Storage.set('filter_' + select.name, select.value);
        });
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('input[type="search"], input[name="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Escape to close modals (handled in individual pages)
    // N to create new item (when on list pages)
    if (e.key === 'n' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const target = e.target;
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
            const newBtn = document.querySelector('a[href*="/new"], button[onclick*="Modal"]');
            if (newBtn) {
                newBtn.click();
            }
        }
    }
});

// AJAX helper for API calls
async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Request failed');
        }

        return result;
    } catch (error) {
        console.error('API call failed:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

// Export for use in other scripts
window.ChoreControl = {
    showToast: showToast,
    confirmAction: confirmAction,
    validateForm: validateForm,
    debounce: debounce,
    Storage: Storage,
    apiCall: apiCall
};
