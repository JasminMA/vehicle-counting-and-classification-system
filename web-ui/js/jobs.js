// Jobs management functionality for Vehicle Analysis System

class JobsUI {
    constructor() {
        this.jobsList = null;
        this.emptyState = null;
        this.refreshBtn = null;
        this.clearCompleted = null;
        
        this.initializeElements();
        this.bindEvents();
        this.setupJobManagerEvents();
    }

    initializeElements() {
        this.jobsList = document.getElementById('jobsList');
        this.emptyState = document.getElementById('emptyState');
        this.refreshBtn = document.getElementById('refreshJobs');
        this.clearCompleted = document.getElementById('clearCompleted');
    }

    bindEvents() {
        // Refresh jobs button
        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', this.refreshJobs.bind(this));
        }

        // Clear completed jobs button
        if (this.clearCompleted) {
            this.clearCompleted.addEventListener('click', this.clearCompletedJobs.bind(this));
        }
    }

    setupJobManagerEvents() {
        // Wait for job manager to be available
        const waitForJobManager = () => {
            if (window.jobManager) {
                // Listen for job events
                jobManager.on('jobAdded', this.onJobAdded.bind(this));
                jobManager.on('jobUpdated', this.onJobUpdated.bind(this));
                jobManager.on('jobRemoved', this.onJobRemoved.bind(this));
                jobManager.on('jobCompleted', this.onJobCompleted.bind(this));
                jobManager.on('jobFailed', this.onJobFailed.bind(this));
                jobManager.on('jobsCleared', this.onJobsCleared.bind(this));

                // Initial render
                this.renderAllJobs();
            } else {
                setTimeout(waitForJobManager, 100);
            }
        };
        waitForJobManager();
    }

    onJobAdded(job) {
        console.log('Job added:', job.id);
        this.renderAllJobs();
    }

    onJobUpdated(job) {
        console.log('Job updated:', job.id, job.status);
        this.updateJobCard(job);
    }

    onJobRemoved(job) {
        console.log('Job removed:', job.id);
        this.removeJobCard(job.id);
        this.updateEmptyState();
    }

    onJobCompleted(data) {
        console.log('Job completed:', data.jobId);
        showToast(`Analysis completed for ${this.getJobFilename(data.jobId)}`, 'success');
    }

    onJobFailed(data) {
        console.log('Job failed:', data.jobId);
        showToast(`Analysis failed for ${this.getJobFilename(data.jobId)}: ${data.status.error}`, 'error');
    }

    onJobsCleared(jobIds) {
        console.log('Jobs cleared:', jobIds);
        showToast(`Cleared ${jobIds.length} completed job(s)`, 'info');
        this.renderAllJobs();
    }

    getJobFilename(jobId) {
        const job = jobManager.getJob(jobId);
        return job ? job.filename : 'Unknown file';
    }

    renderAllJobs() {
        if (!jobManager) return;

        const jobs = jobManager.getAllJobs();
        
        // Clear existing jobs
        this.jobsList.innerHTML = '';

        // Render each job
        jobs.forEach(job => {
            const jobCard = this.createJobCard(job);
            this.jobsList.appendChild(jobCard);
        });

        this.updateEmptyState();
    }

    updateJobCard(job) {
        const existingCard = document.querySelector(`[data-job-id="${job.id}"]`);
        if (existingCard) {
            const newCard = this.createJobCard(job);
            existingCard.replaceWith(newCard);
        } else {
            // Job card doesn't exist, add it
            const jobCard = this.createJobCard(job);
            this.jobsList.insertBefore(jobCard, this.jobsList.firstChild);
        }
        this.updateEmptyState();
    }

    removeJobCard(jobId) {
        const jobCard = document.querySelector(`[data-job-id="${jobId}"]`);
        if (jobCard) {
            jobCard.remove();
        }
    }

    createJobCard(job) {
        const card = document.createElement('div');
        card.className = 'job-card';
        card.setAttribute('data-job-id', job.id);

        // Generate card content
        card.innerHTML = this.generateJobCardHTML(job);

        // Add event listeners
        this.bindJobCardEvents(card, job);

        return card;
    }

    generateJobCardHTML(job) {
        const statusClass = getStatusClass(job.status);
        const statusText = this.getStatusText(job);
        const timeAgo = formatTimestamp(job.createdAt);
        
        // Generate job details based on status
        const details = this.generateJobDetails(job);
        const actions = this.generateJobActions(job);

        return `
            <div class="job-header">
                <div class="job-info">
                    <h3>${job.filename || 'Unknown file'}</h3>
                    <div class="job-id">${job.id}</div>
                </div>
                <div class="job-status ${statusClass}">
                    ${this.getStatusIcon(job.status)} ${statusText}
                </div>
            </div>
            
            ${details}
            
            <div class="job-actions">
                ${actions}
            </div>
        `;
    }

    generateJobDetails(job) {
        const details = [];

        // File size
        if (job.filesize) {
            details.push({
                label: 'Size',
                value: formatFileSize(job.filesize)
            });
        }

        // Created time
        details.push({
            label: 'Created',
            value: formatTimestamp(job.createdAt)
        });

        // Status-specific details
        if (job.status === 'uploading' && job.progress !== undefined) {
            details.push({
                label: 'Progress',
                value: `${job.progress}%`
            });
        }

        if (job.status === 'completed' && job.results) {
            const totalVehicles = job.results?.vehicle_counts?.total_vehicles;
            if (totalVehicles !== undefined) {
                details.push({
                    label: 'Vehicles',
                    value: totalVehicles.toString()
                });
            }
        }

        if (job.status === 'processing' && job.stage) {
            details.push({
                label: 'Stage',
                value: this.formatStage(job.stage)
            });
        }

        if (job.error) {
            details.push({
                label: 'Error',
                value: job.error
            });
        }

        // Generate HTML
        if (details.length === 0) return '';

        const detailsHTML = details.map(detail => `
            <div class="job-detail">
                <div class="job-detail-label">${detail.label}</div>
                <div class="job-detail-value">${detail.value}</div>
            </div>
        `).join('');

        return `<div class="job-details">${detailsHTML}</div>`;
    }

    generateJobActions(job) {
        const actions = [];

        switch (job.status) {
            case 'completed':
                actions.push(`<button class="btn btn-primary" data-action="view-results">View Results</button>`);
                actions.push(`<button class="btn btn-outline" data-action="download-json">Download JSON</button>`);
                actions.push(`<button class="btn btn-outline" data-action="download-csv">Download CSV</button>`);
                actions.push(`<button class="btn btn-outline" data-action="remove">Remove</button>`);
                break;
                
            case 'failed':
            case 'cancelled':
                actions.push(`<button class="btn btn-outline" data-action="retry">Retry</button>`);
                actions.push(`<button class="btn btn-outline" data-action="remove">Remove</button>`);
                break;
                
            case 'uploading':
                actions.push(`<button class="btn btn-outline danger" data-action="cancel">Cancel Upload</button>`);
                break;
                
            case 'processing':
            case 'pending':
                actions.push(`<button class="btn btn-outline" data-action="refresh">Refresh Status</button>`);
                actions.push(`<button class="btn btn-outline danger" data-action="remove">Remove</button>`);
                break;
                
            default:
                actions.push(`<button class="btn btn-outline" data-action="refresh">Refresh</button>`);
                actions.push(`<button class="btn btn-outline" data-action="remove">Remove</button>`);
        }

        return actions.join('');
    }

    bindJobCardEvents(card, job) {
        // Bind action buttons
        const buttons = card.querySelectorAll('[data-action]');
        buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleJobAction(job.id, button.dataset.action);
            });
        });

        // Copy job ID on click
        const jobIdElement = card.querySelector('.job-id');
        if (jobIdElement) {
            jobIdElement.addEventListener('click', async (e) => {
                e.stopPropagation();
                const success = await copyToClipboard(job.id);
                if (success) {
                    showToast('Job ID copied to clipboard', 'info', 2000);
                }
            });
            jobIdElement.style.cursor = 'pointer';
            jobIdElement.title = 'Click to copy job ID';
        }
    }

    async handleJobAction(jobId, action) {
        const job = jobManager.getJob(jobId);
        if (!job) return;

        try {
            switch (action) {
                case 'view-results':
                    await this.viewResults(jobId);
                    break;
                    
                case 'download-json':
                    await this.downloadResults(jobId, 'json');
                    break;
                    
                case 'download-csv':
                    await this.downloadResults(jobId, 'csv');
                    break;
                    
                case 'refresh':
                    await this.refreshJobStatus(jobId);
                    break;
                    
                case 'retry':
                    this.retryJob(job);
                    break;
                    
                case 'cancel':
                    this.cancelJob(jobId);
                    break;
                    
                case 'remove':
                    this.removeJob(jobId);
                    break;
                    
                default:
                    console.warn('Unknown job action:', action);
            }
        } catch (error) {
            console.error('Job action error:', error);
            showToast(`Action failed: ${error.message}`, 'error');
        }
    }

    async viewResults(jobId) {
        try {
            const results = await api.getJobResults(jobId);
            if (results.status === 'completed' && results.results) {
                // Show results in the results section
                window.resultsUI.showResults(results.results, jobId);
                
                // Scroll to results section
                document.getElementById('resultsSection').scrollIntoView({ 
                    behavior: 'smooth' 
                });
            } else {
                showToast('Results not yet available', 'info');
            }
        } catch (error) {
            showToast(`Failed to load results: ${error.message}`, 'error');
        }
    }

    async downloadResults(jobId, format) {
        try {
            await api.downloadResults(jobId, format);
            showToast(`${format.toUpperCase()} download started`, 'success');
        } catch (error) {
            showToast(`Download failed: ${error.message}`, 'error');
        }
    }

    async refreshJobStatus(jobId) {
        try {
            const status = await api.getJobStatus(jobId);
            jobManager.updateJob(jobId, status);
            showToast('Status refreshed', 'info', 2000);
        } catch (error) {
            showToast(`Failed to refresh status: ${error.message}`, 'error');
        }
    }

    retryJob(job) {
        // For retry, we would need to re-upload the file
        // Since we don't store the original file, show a message
        showToast('Please upload the file again to retry analysis', 'info');
    }

    cancelJob(jobId) {
        // Cancel upload if in progress
        if (window.uploadManager && window.uploadManager.getCurrentUpload()?.jobId === jobId) {
            window.uploadManager.cancelCurrentUpload();
        }
        
        jobManager.updateJob(jobId, { 
            status: 'cancelled',
            cancelledAt: new Date().toISOString()
        });
    }

    removeJob(jobId) {
        const job = jobManager.getJob(jobId);
        if (!job) return;

        const confirmMessage = job.status === 'completed' 
            ? `Remove analysis results for "${job.filename}"?`
            : `Remove job "${job.filename}"?`;
            
        if (confirm(confirmMessage)) {
            jobManager.removeJob(jobId);
        }
    }

    refreshJobs() {
        // Add visual feedback
        if (this.refreshBtn) {
            this.refreshBtn.disabled = true;
            const originalText = this.refreshBtn.innerHTML;
            this.refreshBtn.innerHTML = '<span class="refresh-icon spinning">🔄</span> Refreshing...';
            
            setTimeout(() => {
                this.refreshBtn.disabled = false;
                this.refreshBtn.innerHTML = originalText;
            }, 1000);
        }

        // Refresh all non-completed jobs
        const jobs = jobManager.getAllJobs();
        const activeJobs = jobs.filter(job => 
            !['completed', 'failed', 'cancelled'].includes(job.status)
        );

        activeJobs.forEach(async (job) => {
            try {
                const status = await api.getJobStatus(job.id);
                jobManager.updateJob(job.id, status);
            } catch (error) {
                console.error('Failed to refresh job:', job.id, error);
            }
        });

        if (activeJobs.length === 0) {
            showToast('No active jobs to refresh', 'info', 2000);
        }
    }

    clearCompletedJobs() {
        const jobs = jobManager.getAllJobs();
        const completedJobs = jobs.filter(job => job.status === 'completed');
        
        if (completedJobs.length === 0) {
            showToast('No completed jobs to clear', 'info');
            return;
        }

        const confirmMessage = `Clear ${completedJobs.length} completed job(s)? This will remove the job history but not delete the results from the server.`;
        
        if (confirm(confirmMessage)) {
            jobManager.clearCompleted();
        }
    }

    updateEmptyState() {
        const jobs = jobManager ? jobManager.getAllJobs() : [];
        
        if (jobs.length === 0) {
            this.emptyState.style.display = 'block';
            this.jobsList.style.display = 'none';
        } else {
            this.emptyState.style.display = 'none';
            this.jobsList.style.display = 'block';
        }
    }

    getStatusText(job) {
        const statusTexts = {
            'pending': 'Pending',
            'uploading': 'Uploading',
            'processing': 'Processing',
            'completed': 'Completed',
            'failed': 'Failed',
            'cancelled': 'Cancelled',
            'error': 'Error'
        };
        
        return statusTexts[job.status] || 'Unknown';
    }

    getStatusIcon(status) {
        const icons = {
            'pending': '⏳',
            'uploading': '📤',
            'processing': '⚙️',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫',
            'error': '⚠️'
        };
        
        return icons[status] || '❓';
    }

    formatStage(stage) {
        const stageNames = {
            'rekognition_started': 'Analysis Started',
            'rekognition_running': 'AI Analysis',
            'processing_results': 'Processing Results',
            'generating_reports': 'Generating Reports'
        };
        
        return stageNames[stage] || stage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
}

// Add CSS for spinning animation
const style = document.createElement('style');
style.textContent = `
    .spinning {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// Initialize jobs UI when DOM is ready
let jobsUI;

document.addEventListener('DOMContentLoaded', () => {
    jobsUI = new JobsUI();
    console.log('Jobs UI initialized');
});

// Export for global use
window.jobsUI = jobsUI;
