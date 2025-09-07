// API client for Vehicle Analysis System

class VehicleAnalysisAPI {
    constructor(baseUrl) {
        this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
    }

    /**
     * Make HTTP request with error handling
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise<Object>} Response data
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}/${endpoint.replace(/^\//, '')}`;
        
        const config = {
            method: 'GET',
            headers: { ...this.defaultHeaders },
            ...options
        };

        // Add body for POST requests
        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            console.log(`API Request: ${config.method} ${url}`);
            
            const response = await fetch(url, config);
            
            // Handle different response types
            let data;
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                const error = new Error(data.error || data || `HTTP ${response.status}`);
                error.status = response.status;
                error.data = data;
                throw error;
            }

            console.log(`API Response: ${response.status}`, data);
            return data;

        } catch (error) {
            console.error(`API Error: ${config.method} ${url}`, error);
            
            // Enhance error with more context
            if (!error.status) {
                error.message = 'Network error - please check your internet connection';
                error.status = 0;
            }
            
            throw error;
        }
    }

    /**
     * Check API health
     * @returns {Promise<Object>} Health status
     */
    async checkHealth() {
        try {
            return await this.request('health');
        } catch (error) {
            return { 
                status: 'error', 
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Upload video and get pre-signed URL
     * @param {string} filename - Video filename
     * @param {number} filesize - File size in bytes
     * @returns {Promise<Object>} Upload details with jobId and uploadUrl
     */
    async initiateUpload(filename, filesize) {
        return await this.request('upload', {
            method: 'POST',
            body: { filename, filesize }
        });
    }

    /**
     * Upload file to S3 using pre-signed URL
     * @param {string} uploadUrl - Pre-signed upload URL
     * @param {File} file - File to upload
     * @param {Function} onProgress - Progress callback
     * @returns {Promise<void>}
     */
    async uploadFile(uploadUrl, file, onProgress = null) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Track upload progress
            if (onProgress && xhr.upload) {
                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        onProgress(percentComplete, event.loaded, event.total);
                    }
                });
            }

            xhr.onreadystatechange = () => {
                if (xhr.readyState === XMLHttpRequest.DONE) {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        console.log('File upload completed successfully');
                        resolve();
                    } else {
                        console.error('File upload failed:', xhr.status, xhr.statusText);
                        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
                    }
                }
            };

            xhr.onerror = () => {
                console.error('File upload network error');
                reject(new Error('Network error during file upload'));
            };

            xhr.open('PUT', uploadUrl);
            xhr.setRequestHeader('Content-Type', file.type || 'video/*');
            xhr.send(file);
        });
    }

    /**
     * Get job status
     * @param {string} jobId - Job identifier
     * @returns {Promise<Object>} Job status
     */
    async getJobStatus(jobId) {
        return await this.request(`results/${jobId}/status`);
    }

    /**
     * Get complete job results
     * @param {string} jobId - Job identifier
     * @param {boolean} includeDetails - Include detailed timeline data
     * @returns {Promise<Object>} Complete analysis results
     */
    async getJobResults(jobId, includeDetails = true) {
        const params = includeDetails ? '' : '?details=false';
        return await this.request(`results/${jobId}${params}`);
    }

    /**
     * Get download URL for results
     * @param {string} jobId - Job identifier
     * @param {string} format - File format ('json' or 'csv')
     * @returns {Promise<Object>} Download URL and metadata
     */
    async getDownloadUrl(jobId, format = 'json') {
        return await this.request(`results/${jobId}/download/${format}`);
    }

    /**
     * Download results file
     * @param {string} jobId - Job identifier
     * @param {string} format - File format ('json' or 'csv')
     * @returns {Promise<void>} Initiates download
     */
    async downloadResults(jobId, format = 'json') {
        try {
            const downloadData = await this.getDownloadUrl(jobId, format);
            
            if (downloadData.downloadUrl) {
                // Open download URL in new tab
                const link = document.createElement('a');
                link.href = downloadData.downloadUrl;
                link.download = downloadData.filename || `results_${jobId}.${format}`;
                link.target = '_blank';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                return downloadData;
            } else {
                throw new Error('No download URL provided');
            }
        } catch (error) {
            console.error('Download failed:', error);
            throw error;
        }
    }

    /**
     * Poll job status until completion
     * @param {string} jobId - Job identifier
     * @param {Function} onProgress - Progress callback
     * @param {number} interval - Polling interval in ms
     * @param {number} timeout - Max wait time in ms
     * @returns {Promise<Object>} Final results
     */
    async pollUntilComplete(jobId, onProgress = null, interval = 10000, timeout = 1800000) {
        const startTime = Date.now();
        
        return new Promise((resolve, reject) => {
            const poll = async () => {
                try {
                    // Check for timeout
                    if (Date.now() - startTime > timeout) {
                        reject(new Error('Polling timeout - job did not complete within expected time'));
                        return;
                    }

                    const status = await this.getJobStatus(jobId);
                    
                    if (onProgress) {
                        onProgress(status);
                    }

                    if (status.status === 'completed') {
                        // Get full results
                        try {
                            const results = await this.getJobResults(jobId);
                            resolve(results);
                        } catch (resultsError) {
                            console.error('Failed to get results after completion:', resultsError);
                            reject(resultsError);
                        }
                    } else if (status.status === 'failed') {
                        reject(new Error(status.error || 'Job processing failed'));
                    } else {
                        // Continue polling
                        setTimeout(poll, interval);
                    }
                } catch (error) {
                    console.error('Polling error:', error);
                    // Continue polling on network errors, but reject on other errors
                    if (error.status === 0) {
                        setTimeout(poll, interval);
                    } else {
                        reject(error);
                    }
                }
            };

            // Start polling
            poll();
        });
    }
}

// Job Manager class for handling multiple jobs
class JobManager {
    constructor(api) {
        this.api = api;
        this.jobs = new Map();
        this.pollingIntervals = new Map();
        this.eventHandlers = new Map();
    }

    /**
     * Add event listener
     * @param {string} event - Event name
     * @param {Function} handler - Event handler
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    /**
     * Emit event
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    emit(event, data) {
        const handlers = this.eventHandlers.get(event) || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error('Event handler error:', error);
            }
        });
    }

    /**
     * Add job to manager
     * @param {string} jobId - Job identifier
     * @param {Object} jobData - Job data
     */
    addJob(jobId, jobData = {}) {
        const job = {
            id: jobId,
            status: 'pending',
            createdAt: new Date().toISOString(),
            ...jobData
        };
        
        this.jobs.set(jobId, job);
        this.emit('jobAdded', job);
        
        // Start polling for this job
        this.startPolling(jobId);
        
        return job;
    }

    /**
     * Update job data
     * @param {string} jobId - Job identifier
     * @param {Object} updates - Job updates
     */
    updateJob(jobId, updates) {
        const job = this.jobs.get(jobId);
        if (job) {
            Object.assign(job, updates, { updatedAt: new Date().toISOString() });
            this.jobs.set(jobId, job);
            this.emit('jobUpdated', job);
        }
    }

    /**
     * Get job by ID
     * @param {string} jobId - Job identifier
     * @returns {Object|null} Job data
     */
    getJob(jobId) {
        return this.jobs.get(jobId) || null;
    }

    /**
     * Get all jobs
     * @returns {Array} Array of job objects
     */
    getAllJobs() {
        return Array.from(this.jobs.values()).sort((a, b) => 
            new Date(b.createdAt) - new Date(a.createdAt)
        );
    }

    /**
     * Remove job
     * @param {string} jobId - Job identifier
     */
    removeJob(jobId) {
        const job = this.jobs.get(jobId);
        if (job) {
            this.stopPolling(jobId);
            this.jobs.delete(jobId);
            this.emit('jobRemoved', job);
        }
    }

    /**
     * Start polling for job status
     * @param {string} jobId - Job identifier
     */
    startPolling(jobId) {
        // Clear existing polling if any
        this.stopPolling(jobId);

        const pollInterval = setInterval(async () => {
            try {
                const status = await this.api.getJobStatus(jobId);
                this.updateJob(jobId, status);

                // Stop polling if job is complete or failed
                if (status.status === 'completed' || status.status === 'failed') {
                    this.stopPolling(jobId);
                    
                    if (status.status === 'completed') {
                        this.emit('jobCompleted', { jobId, status });
                    } else {
                        this.emit('jobFailed', { jobId, status });
                    }
                }
            } catch (error) {
                console.error(`Polling error for job ${jobId}:`, error);
                // Don't stop polling on network errors
                if (error.status !== 0) {
                    this.updateJob(jobId, { 
                        status: 'error', 
                        error: error.message 
                    });
                    this.stopPolling(jobId);
                    this.emit('jobError', { jobId, error });
                }
            }
        }, window.APP_CONFIG.POLL_INTERVAL);

        this.pollingIntervals.set(jobId, pollInterval);
    }

    /**
     * Stop polling for job status
     * @param {string} jobId - Job identifier
     */
    stopPolling(jobId) {
        const interval = this.pollingIntervals.get(jobId);
        if (interval) {
            clearInterval(interval);
            this.pollingIntervals.delete(jobId);
        }
    }

    /**
     * Stop all polling
     */
    stopAllPolling() {
        this.pollingIntervals.forEach(interval => clearInterval(interval));
        this.pollingIntervals.clear();
    }

    /**
     * Load jobs from storage
     */
    loadFromStorage() {
        const storedJobs = Storage.get('jobs', []);
        storedJobs.forEach(job => {
            this.jobs.set(job.id, job);
            // Only start polling for jobs that aren't complete/failed
            if (!['completed', 'failed'].includes(job.status)) {
                this.startPolling(job.id);
            }
        });
    }

    /**
     * Save jobs to storage
     */
    saveToStorage() {
        const jobs = this.getAllJobs();
        Storage.set('jobs', jobs);
    }

    /**
     * Clear completed jobs
     */
    clearCompleted() {
        const completedJobs = [];
        this.jobs.forEach((job, jobId) => {
            if (job.status === 'completed') {
                completedJobs.push(jobId);
            }
        });

        completedJobs.forEach(jobId => {
            this.removeJob(jobId);
        });

        this.saveToStorage();
        this.emit('jobsCleared', completedJobs);
    }
}

// Initialize API client and job manager
let api, jobManager;

// Initialize API when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize API client
    api = new VehicleAnalysisAPI(window.APP_CONFIG.API_BASE_URL);
    
    // Initialize job manager
    jobManager = new JobManager(api);
    
    // Load existing jobs from storage
    jobManager.loadFromStorage();
    
    // Save jobs to storage when they change
    jobManager.on('jobAdded', () => jobManager.saveToStorage());
    jobManager.on('jobUpdated', () => jobManager.saveToStorage());
    jobManager.on('jobRemoved', () => jobManager.saveToStorage());
    
    console.log('API client initialized:', api.baseUrl);
});

// Export for global use
window.api = api;
window.jobManager = jobManager;
