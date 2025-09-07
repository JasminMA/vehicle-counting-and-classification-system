// Main application controller for Vehicle Analysis System

class VehicleAnalysisApp {
    constructor() {
        this.initialized = false;
        this.apiStatus = 'checking';
        
        this.initializeApp();
    }

    async initializeApp() {
        try {
            console.log('Initializing Vehicle Analysis App...');
            
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
            } else {
                await this.init();
            }
            
        } catch (error) {
            console.error('Failed to initialize app:', error);
            this.showCriticalError('Failed to initialize application');
        }
    }

    async init() {
        try {
            // Initialize UI components
            this.initializeUI();
            
            // Check API connectivity
            await this.checkAPIStatus();
            
            // Set up global event handlers
            this.setupGlobalEventHandlers();
            
            // Load application state
            this.loadApplicationState();
            
            // Check for URL parameters (e.g., job ID to view)
            this.handleURLParameters();
            
            this.initialized = true;
            console.log('Vehicle Analysis App initialized successfully');
            
        } catch (error) {
            console.error('App initialization error:', error);
            this.showCriticalError('Failed to start application');
        }
    }

    initializeUI() {
        // Initialize modal handlers
        this.setupModalHandlers();
        
        // Initialize tooltip handlers
        this.setupTooltipHandlers();
        
        // Initialize keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // Initialize responsive handlers
        this.setupResponsiveHandlers();
        
        console.log('UI components initialized');
    }

    setupModalHandlers() {
        // Help modal
        const helpBtn = document.getElementById('helpBtn');
        if (helpBtn) {
            helpBtn.addEventListener('click', () => showModal('helpModal'));
        }

        // About modal
        const aboutBtn = document.getElementById('aboutBtn');
        if (aboutBtn) {
            aboutBtn.addEventListener('click', () => showModal('aboutModal'));
        }

        // Privacy modal
        const privacyBtn = document.getElementById('privacyBtn');
        if (privacyBtn) {
            privacyBtn.addEventListener('click', () => showModal('privacyModal'));
        }

        // Close modal buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modalId = btn.dataset.modal;
                if (modalId) {
                    hideModal(modalId);
                }
            });
        });

        // Close modal on backdrop click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    hideModal(modal.id);
                }
            });
        });

        // Close modal on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    hideModal(openModal.id);
                }
            }
        });
    }

    setupTooltipHandlers() {
        // Add tooltips to elements with title attributes
        document.querySelectorAll('[title]').forEach(element => {
            element.addEventListener('mouseenter', this.showTooltip.bind(this));
            element.addEventListener('mouseleave', this.hideTooltip.bind(this));
        });
    }

    showTooltip(event) {
        // Simple tooltip implementation
        const element = event.target;
        const title = element.getAttribute('title');
        
        if (title) {
            // Remove title to prevent browser tooltip
            element.removeAttribute('title');
            element.dataset.originalTitle = title;
            
            // Could implement custom tooltip here
            console.log('Tooltip:', title);
        }
    }

    hideTooltip(event) {
        const element = event.target;
        const originalTitle = element.dataset.originalTitle;
        
        if (originalTitle) {
            element.setAttribute('title', originalTitle);
            delete element.dataset.originalTitle;
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Only handle shortcuts when not in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            // Handle keyboard shortcuts
            switch (e.key) {
                case 'u':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        document.getElementById('videoInput')?.click();
                    }
                    break;
                    
                case 'r':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        document.getElementById('refreshJobs')?.click();
                    }
                    break;
                    
                case '?':
                    if (!e.ctrlKey && !e.metaKey) {
                        e.preventDefault();
                        showModal('helpModal');
                    }
                    break;
            }
        });
    }

    setupResponsiveHandlers() {
        // Handle responsive layout changes
        const handleResize = throttle(() => {
            this.updateResponsiveLayout();
        }, 250);

        window.addEventListener('resize', handleResize);
        
        // Initial layout update
        this.updateResponsiveLayout();
    }

    updateResponsiveLayout() {
        const width = window.innerWidth;
        
        // Update layout classes based on screen size
        document.body.classList.toggle('mobile', width < 768);
        document.body.classList.toggle('tablet', width >= 768 && width < 1024);
        document.body.classList.toggle('desktop', width >= 1024);
    }

    async checkAPIStatus() {
        const statusElement = document.getElementById('apiStatus');
        const statusIndicator = statusElement?.querySelector('.status-indicator');
        const statusText = statusElement?.querySelector('.status-text');
        
        try {
            // Update UI to show checking
            if (statusText) statusText.textContent = 'Checking...';
            
            // Check API health
            const health = await api.checkHealth();
            
            if (health.status === 'healthy') {
                this.apiStatus = 'healthy';
                if (statusElement) statusElement.className = 'api-status healthy';
                if (statusText) statusText.textContent = 'API Online';
                console.log('API is healthy');
            } else {
                throw new Error(health.error || 'API unhealthy');
            }
            
        } catch (error) {
            this.apiStatus = 'error';
            if (statusElement) statusElement.className = 'api-status error';
            if (statusText) statusText.textContent = 'API Offline';
            
            console.error('API health check failed:', error);
            showToast(`API connection failed: ${error.message}`, 'error', 10000);
        }
    }

    setupGlobalEventHandlers() {
        // Handle online/offline events
        window.addEventListener('online', () => {
            showToast('Connection restored', 'success', 3000);
            this.checkAPIStatus();
        });

        window.addEventListener('offline', () => {
            showToast('Connection lost - working offline', 'error', 5000);
        });

        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.initialized) {
                // Page became visible, refresh status
                this.checkAPIStatus();
                
                // Refresh active jobs
                if (window.jobsUI) {
                    setTimeout(() => window.jobsUI.refreshJobs(), 1000);
                }
            }
        });

        // Handle beforeunload for unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (window.uploadManager && window.uploadManager.isUploading()) {
                e.preventDefault();
                e.returnValue = 'Upload in progress. Are you sure you want to leave?';
                return e.returnValue;
            }
        });

        // Handle errors globally
        window.addEventListener('error', (e) => {
            console.error('Global error:', e.error);
            this.handleGlobalError(e.error);
        });

        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            this.handleGlobalError(e.reason);
        });
    }

    handleGlobalError(error) {
        // Log error for debugging
        console.error('Global error handled:', error);
        
        // Show user-friendly error message
        const message = error.message || 'An unexpected error occurred';
        showToast(`Error: ${message}`, 'error', 5000);
    }

    loadApplicationState() {
        // Load user preferences
        const preferences = Storage.get('preferences', {});
        this.applyPreferences(preferences);
        
        // Load recent jobs from storage (handled by job manager)
        console.log('Application state loaded');
    }

    applyPreferences(preferences) {
        // Apply theme
        if (preferences.theme) {
            document.body.classList.toggle('dark-theme', preferences.theme === 'dark');
        }
        
        // Apply other preferences as needed
        console.log('Preferences applied:', preferences);
    }

    handleURLParameters() {
        // Check for job ID in URL
        const jobId = UrlUtils.getParam('jobId');
        if (jobId && Validator.isValidJobId(jobId)) {
            // Load and display job results
            this.loadJobFromURL(jobId);
        }
        
        // Check for other parameters
        const action = UrlUtils.getParam('action');
        if (action === 'help') {
            showModal('helpModal');
        }
    }

    async loadJobFromURL(jobId) {
        try {
            console.log('Loading job from URL:', jobId);
            
            const results = await api.getJobResults(jobId);
            if (results.status === 'completed' && results.results) {
                // Show results
                window.resultsUI?.showResults(results.results, jobId);
                
                // Scroll to results
                setTimeout(() => {
                    document.getElementById('resultsSection')?.scrollIntoView({ 
                        behavior: 'smooth' 
                    });
                }, 500);
                
                showToast('Results loaded from URL', 'success');
            } else {
                showToast('Job not completed or results not available', 'info');
            }
        } catch (error) {
            console.error('Failed to load job from URL:', error);
            showToast(`Failed to load job: ${error.message}`, 'error');
        }
    }

    showCriticalError(message) {
        // Show critical error that prevents app from working
        const errorHTML = `
            <div class="critical-error">
                <div class="error-icon">⚠️</div>
                <h2>Application Error</h2>
                <p>${message}</p>
                <button onclick="location.reload()" class="btn btn-primary">Reload Page</button>
            </div>
        `;
        
        document.body.innerHTML = errorHTML;
        document.body.className = 'critical-error-state';
    }

    // Public methods for external use
    getAPIStatus() {
        return this.apiStatus;
    }

    isInitialized() {
        return this.initialized;
    }

    async refreshApp() {
        console.log('Refreshing application...');
        await this.checkAPIStatus();
        
        if (window.jobsUI) {
            window.jobsUI.refreshJobs();
        }
        
        showToast('Application refreshed', 'success', 2000);
    }
}

// Configuration validation
function validateConfiguration() {
    if (!window.APP_CONFIG) {
        throw new Error('APP_CONFIG not found');
    }

    if (!window.APP_CONFIG.API_BASE_URL) {
        throw new Error('API_BASE_URL not configured');
    }

    // Validate API URL format
    try {
        new URL(window.APP_CONFIG.API_BASE_URL);
    } catch (error) {
        throw new Error('Invalid API_BASE_URL format');
    }

    console.log('Configuration validated');
}

// Initialize application when DOM is ready
let app;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Validate configuration
        validateConfiguration();
        
        // Initialize application
        app = new VehicleAnalysisApp();
        
        // Make app globally available for debugging
        window.app = app;
        
    } catch (error) {
        console.error('Failed to start application:', error);
        
        // Show error message to user
        const errorMessage = error.message || 'Application failed to start';
        document.body.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; text-align: center; padding: 20px;">
                <h1 style="color: #ef4444; margin-bottom: 20px;">⚠️ Configuration Error</h1>
                <p style="margin-bottom: 20px; max-width: 500px; line-height: 1.6;">${errorMessage}</p>
                <p style="color: #64748b; font-size: 14px;">Please check the console for more details.</p>
                <button onclick="location.reload()" style="margin-top: 20px; padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer;">Reload Page</button>
            </div>
        `;
    }
});

// Export for global use
window.VehicleAnalysisApp = VehicleAnalysisApp;
