// Utility functions for the Vehicle Analysis System

/**
 * Format file size to human readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size string
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format duration from seconds to human readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration string
 */
function formatDuration(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.round(seconds % 60);
        return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
    }
}

/**
 * Format timestamp to human readable format
 * @param {string|Date} timestamp - ISO timestamp or Date object
 * @returns {string} Formatted timestamp string
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) {
        return 'Just now';
    } else if (diffMins < 60) {
        return `${diffMins}m ago`;
    } else if (diffHours < 24) {
        return `${diffHours}h ago`;
    } else if (diffDays < 7) {
        return `${diffDays}d ago`;
    } else {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }
}

/**
 * Format video timestamp for timeline display
 * @param {number} seconds - Timestamp in seconds
 * @returns {string} Formatted timestamp (MM:SS or HH:MM:SS)
 */
function formatVideoTimestamp(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
}

/**
 * Validate file format
 * @param {string} filename - File name
 * @returns {boolean} True if format is supported
 */
function isValidVideoFormat(filename) {
    if (!filename) return false;
    
    const extension = filename.toLowerCase().split('.').pop();
    return window.APP_CONFIG.SUPPORTED_FORMATS.includes(extension);
}

/**
 * Generate a unique ID for tracking purposes
 * @returns {string} Unique identifier
 */
function generateUniqueId() {
    return 'id_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

/**
 * Debounce function to limit API calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
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

/**
 * Throttle function to limit execution frequency
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        // Fallback for older browsers
        try {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            return true;
        } catch (fallbackErr) {
            console.error('Failed to copy text:', fallbackErr);
            return false;
        }
    }
}

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type ('success', 'error', 'info')
 * @param {number} duration - Duration in milliseconds (default: 5000)
 */
function showToast(message, type = 'info', duration = 5000) {
    const toastId = type === 'error' ? 'errorToast' : 'successToast';
    const messageId = type === 'error' ? 'errorMessage' : 'successMessage';
    
    const toast = document.getElementById(toastId);
    const messageEl = document.getElementById(messageId);
    
    if (!toast || !messageEl) return;
    
    messageEl.textContent = message;
    toast.classList.add('show');
    
    // Auto-hide after duration
    setTimeout(() => {
        hideToast(toastId);
    }, duration);
}

/**
 * Hide toast notification
 * @param {string} toastId - Toast element ID
 */
function hideToast(toastId) {
    const toast = document.getElementById(toastId);
    if (toast) {
        toast.classList.remove('show');
    }
}

/**
 * Show modal dialog
 * @param {string} modalId - Modal element ID
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        // Focus trap for accessibility
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements.length > 0) {
            focusableElements[0].focus();
        }
    }
}

/**
 * Hide modal dialog
 * @param {string} modalId - Modal element ID
 */
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

/**
 * Download file from URL
 * @param {string} url - File URL
 * @param {string} filename - Suggested filename
 */
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'download';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Create a loading element
 * @param {string} text - Loading text (optional)
 * @returns {HTMLElement} Loading element
 */
function createLoadingElement(text = 'Loading...') {
    const loading = document.createElement('div');
    loading.className = 'loading-container';
    loading.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text">${text}</div>
    `;
    return loading;
}

/**
 * Animate element entrance
 * @param {HTMLElement} element - Element to animate
 * @param {string} animation - Animation class name
 */
function animateIn(element, animation = 'fade-in') {
    if (element) {
        element.classList.add(animation);
        element.addEventListener('animationend', () => {
            element.classList.remove(animation);
        }, { once: true });
    }
}

/**
 * Get vehicle type emoji
 * @param {string} vehicleType - Vehicle type
 * @returns {string} Emoji representation
 */
function getVehicleEmoji(vehicleType) {
    const emojis = {
        'cars': '🚗',
        'trucks': '🚛',
        'motorcycles': '🏍️',
        'buses': '🚌',
        'vans': '🚐',
        'emergency_vehicles': '🚑'
    };
    return emojis[vehicleType] || '🚗';
}

/**
 * Get status color class
 * @param {string} status - Status string
 * @returns {string} CSS class name
 */
function getStatusClass(status) {
    const statusClasses = {
        'pending': 'pending',
        'processing': 'processing',
        'completed': 'completed',
        'failed': 'failed'
    };
    return statusClasses[status] || 'pending';
}

/**
 * Format confidence percentage
 * @param {number} confidence - Confidence value (0-100)
 * @returns {string} Formatted percentage
 */
function formatConfidence(confidence) {
    return `${Math.round(confidence)}%`;
}

/**
 * Parse job ID from various formats
 * @param {string} input - Input string that might contain job ID
 * @returns {string|null} Extracted job ID or null
 */
function parseJobId(input) {
    if (!input || typeof input !== 'string') return null;
    
    // Direct job ID
    if (input.startsWith('job-')) {
        return input;
    }
    
    // Extract from URL or path
    const jobIdMatch = input.match(/job-[a-zA-Z0-9-]+/);
    return jobIdMatch ? jobIdMatch[0] : null;
}

/**
 * Storage utilities for persisting data locally
 */
const Storage = {
    /**
     * Get item from localStorage
     * @param {string} key - Storage key
     * @param {*} defaultValue - Default value if key doesn't exist
     * @returns {*} Stored value or default
     */
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(`vehicleAnalysis_${key}`);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.warn('Failed to get from storage:', error);
            return defaultValue;
        }
    },
    
    /**
     * Set item in localStorage
     * @param {string} key - Storage key
     * @param {*} value - Value to store
     */
    set(key, value) {
        try {
            localStorage.setItem(`vehicleAnalysis_${key}`, JSON.stringify(value));
        } catch (error) {
            console.warn('Failed to set in storage:', error);
        }
    },
    
    /**
     * Remove item from localStorage
     * @param {string} key - Storage key
     */
    remove(key) {
        try {
            localStorage.removeItem(`vehicleAnalysis_${key}`);
        } catch (error) {
            console.warn('Failed to remove from storage:', error);
        }
    },
    
    /**
     * Clear all app-related storage
     */
    clear() {
        try {
            const keys = Object.keys(localStorage).filter(key => 
                key.startsWith('vehicleAnalysis_')
            );
            keys.forEach(key => localStorage.removeItem(key));
        } catch (error) {
            console.warn('Failed to clear storage:', error);
        }
    }
};

/**
 * URL utilities
 */
const UrlUtils = {
    /**
     * Get URL parameter value
     * @param {string} param - Parameter name
     * @returns {string|null} Parameter value
     */
    getParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    },
    
    /**
     * Set URL parameter
     * @param {string} param - Parameter name
     * @param {string} value - Parameter value
     * @param {boolean} replace - Whether to replace current history entry
     */
    setParam(param, value, replace = false) {
        const url = new URL(window.location);
        url.searchParams.set(param, value);
        
        if (replace) {
            window.history.replaceState({}, '', url);
        } else {
            window.history.pushState({}, '', url);
        }
    },
    
    /**
     * Remove URL parameter
     * @param {string} param - Parameter name
     * @param {boolean} replace - Whether to replace current history entry
     */
    removeParam(param, replace = true) {
        const url = new URL(window.location);
        url.searchParams.delete(param);
        
        if (replace) {
            window.history.replaceState({}, '', url);
        } else {
            window.history.pushState({}, '', url);
        }
    }
};

/**
 * Validation utilities
 */
const Validator = {
    /**
     * Validate email format
     * @param {string} email - Email address
     * @returns {boolean} Is valid email
     */
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },
    
    /**
     * Validate job ID format
     * @param {string} jobId - Job ID
     * @returns {boolean} Is valid job ID
     */
    isValidJobId(jobId) {
        return typeof jobId === 'string' && 
               jobId.startsWith('job-') && 
               jobId.length > 10 && 
               jobId.length < 100 &&
               !jobId.includes('..') &&
               !jobId.includes('/') &&
               !jobId.includes('\\');
    },
    
    /**
     * Validate file size
     * @param {number} size - File size in bytes
     * @returns {boolean} Is valid size
     */
    isValidFileSize(size) {
        return typeof size === 'number' && 
               size > 0 && 
               size <= window.APP_CONFIG.MAX_FILE_SIZE;
    }
};

/**
 * DOM utilities
 */
const DOM = {
    /**
     * Create element with properties
     * @param {string} tag - HTML tag name
     * @param {Object} props - Element properties
     * @param {string|HTMLElement[]} content - Element content
     * @returns {HTMLElement} Created element
     */
    create(tag, props = {}, content = '') {
        const element = document.createElement(tag);
        
        Object.entries(props).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'dataset') {
                Object.entries(value).forEach(([dataKey, dataValue]) => {
                    element.dataset[dataKey] = dataValue;
                });
            } else if (key.startsWith('on') && typeof value === 'function') {
                element.addEventListener(key.slice(2).toLowerCase(), value);
            } else {
                element[key] = value;
            }
        });
        
        if (typeof content === 'string') {
            element.innerHTML = content;
        } else if (Array.isArray(content)) {
            content.forEach(child => {
                if (typeof child === 'string') {
                    element.appendChild(document.createTextNode(child));
                } else if (child instanceof HTMLElement) {
                    element.appendChild(child);
                }
            });
        }
        
        return element;
    },
    
    /**
     * Find element with error handling
     * @param {string} selector - CSS selector
     * @param {HTMLElement} context - Search context (default: document)
     * @returns {HTMLElement|null} Found element
     */
    find(selector, context = document) {
        try {
            return context.querySelector(selector);
        } catch (error) {
            console.warn('Invalid selector:', selector, error);
            return null;
        }
    },
    
    /**
     * Find all elements with error handling
     * @param {string} selector - CSS selector
     * @param {HTMLElement} context - Search context (default: document)
     * @returns {NodeList} Found elements
     */
    findAll(selector, context = document) {
        try {
            return context.querySelectorAll(selector);
        } catch (error) {
            console.warn('Invalid selector:', selector, error);
            return [];
        }
    }
};

// Export utilities for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatFileSize,
        formatDuration,
        formatTimestamp,
        formatVideoTimestamp,
        isValidVideoFormat,
        generateUniqueId,
        debounce,
        throttle,
        copyToClipboard,
        showToast,
        hideToast,
        showModal,
        hideModal,
        downloadFile,
        createLoadingElement,
        animateIn,
        getVehicleEmoji,
        getStatusClass,
        formatConfidence,
        parseJobId,
        Storage,
        UrlUtils,
        Validator,
        DOM
    };
}
