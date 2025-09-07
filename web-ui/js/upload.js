// Upload functionality for Vehicle Analysis System

class UploadManager {
    constructor() {
        this.currentUpload = null;
        this.uploadZone = null;
        this.videoInput = null;
        this.uploadContent = null;
        this.uploadProgress = null;
        
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.uploadZone = document.getElementById('uploadZone');
        this.videoInput = document.getElementById('videoInput');
        this.uploadContent = document.getElementById('uploadContent');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.browseBtn = document.getElementById('browseBtn');
        this.cancelUpload = document.getElementById('cancelUpload');
        
        // Progress elements
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
    }

    bindEvents() {
        // Drag and drop events
        this.uploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
        this.uploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.uploadZone.addEventListener('drop', this.handleDrop.bind(this));
        
        // Click to browse
        this.browseBtn.addEventListener('click', () => {
            this.videoInput.click();
        });
        
        this.uploadZone.addEventListener('click', (e) => {
            if (e.target === this.uploadZone || e.target.closest('.upload-content')) {
                this.videoInput.click();
            }
        });
        
        // File input change
        this.videoInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Cancel upload
        this.cancelUpload.addEventListener('click', this.cancelCurrentUpload.bind(this));
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.uploadZone.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleDragOver(e) {
        this.preventDefaults(e);
        this.uploadZone.classList.add('drag-over');
    }

    handleDragLeave(e) {
        this.preventDefaults(e);
        
        // Only remove drag-over if we're leaving the upload zone itself
        if (!this.uploadZone.contains(e.relatedTarget)) {
            this.uploadZone.classList.remove('drag-over');
        }
    }

    handleDrop(e) {
        this.preventDefaults(e);
        this.uploadZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    async handleFile(file) {
        try {
            // Validate file
            const validation = this.validateFile(file);
            if (!validation.valid) {
                showToast(validation.error, 'error');
                return;
            }

            // Check if there's already an upload in progress
            if (this.currentUpload) {
                const proceed = confirm('An upload is already in progress. Do you want to cancel it and upload this file instead?');
                if (proceed) {
                    this.cancelCurrentUpload();
                } else {
                    return;
                }
            }

            // Start upload process
            await this.startUpload(file);

        } catch (error) {
            console.error('Upload error:', error);
            showToast(`Upload failed: ${error.message}`, 'error');
            this.resetUploadUI();
        }
    }

    validateFile(file) {
        // Check file type
        if (!isValidVideoFormat(file.name)) {
            return {
                valid: false,
                error: `Unsupported file format. Please use: ${window.APP_CONFIG.SUPPORTED_FORMATS.join(', ')}`
            };
        }

        // Check file size
        if (file.size > window.APP_CONFIG.MAX_FILE_SIZE) {
            return {
                valid: false,
                error: `File too large. Maximum size is ${formatFileSize(window.APP_CONFIG.MAX_FILE_SIZE)}`
            };
        }

        if (file.size === 0) {
            return {
                valid: false,
                error: 'File appears to be empty'
            };
        }

        return { valid: true };
    }

    async startUpload(file) {
        try {
            // Show progress UI
            this.showProgressUI(file);

            // Get upload URL from API
            showToast('Preparing upload...', 'info', 3000);
            
            const uploadData = await api.initiateUpload(file.name, file.size);
            const { jobId, uploadUrl } = uploadData;

            console.log('Upload initiated:', { jobId, file: file.name });

            // Store current upload info
            this.currentUpload = {
                jobId,
                file,
                uploadUrl,
                xhr: null
            };

            // Add job to job manager
            jobManager.addJob(jobId, {
                filename: file.name,
                filesize: file.size,
                status: 'uploading'
            });

            // Upload file to S3
            await api.uploadFile(uploadUrl, file, this.onUploadProgress.bind(this));

            // Upload completed
            this.onUploadComplete();
            showToast('Upload completed! Analysis starting...', 'success');

        } catch (error) {
            console.error('Upload failed:', error);
            this.onUploadError(error);
            throw error;
        }
    }

    onUploadProgress(percentComplete, loaded, total) {
        // Update progress bar
        this.progressFill.style.width = `${percentComplete}%`;
        this.progressText.textContent = `${Math.round(percentComplete)}%`;

        // Update job status if available
        if (this.currentUpload && this.currentUpload.jobId) {
            jobManager.updateJob(this.currentUpload.jobId, {
                status: 'uploading',
                progress: Math.round(percentComplete),
                uploaded: loaded,
                total: total
            });
        }

        console.log(`Upload progress: ${Math.round(percentComplete)}%`);
    }

    onUploadComplete() {
        if (this.currentUpload) {
            // Update job status
            jobManager.updateJob(this.currentUpload.jobId, {
                status: 'pending',
                progress: 100,
                uploadedAt: new Date().toISOString()
            });

            console.log('Upload completed for job:', this.currentUpload.jobId);
        }

        // Reset upload state
        this.currentUpload = null;
        this.resetUploadUI();

        // Clear file input
        this.videoInput.value = '';
    }

    onUploadError(error) {
        if (this.currentUpload) {
            // Update job status
            jobManager.updateJob(this.currentUpload.jobId, {
                status: 'failed',
                error: error.message,
                failedAt: new Date().toISOString()
            });
        }

        // Reset upload state
        this.currentUpload = null;
        this.resetUploadUI();
        
        // Clear file input
        this.videoInput.value = '';

        showToast(`Upload failed: ${error.message}`, 'error');
    }

    cancelCurrentUpload() {
        if (this.currentUpload) {
            // Cancel XHR if available
            if (this.currentUpload.xhr) {
                this.currentUpload.xhr.abort();
            }

            // Update job status
            jobManager.updateJob(this.currentUpload.jobId, {
                status: 'cancelled',
                cancelledAt: new Date().toISOString()
            });

            console.log('Upload cancelled for job:', this.currentUpload.jobId);
            showToast('Upload cancelled', 'info');
        }

        // Reset state
        this.currentUpload = null;
        this.resetUploadUI();
        
        // Clear file input
        this.videoInput.value = '';
    }

    showProgressUI(file) {
        // Hide upload content, show progress
        this.uploadContent.style.display = 'none';
        this.uploadProgress.style.display = 'block';

        // Set file info
        this.fileName.textContent = file.name;
        this.fileSize.textContent = formatFileSize(file.size);

        // Reset progress
        this.progressFill.style.width = '0%';
        this.progressText.textContent = '0%';

        // Disable upload zone interaction
        this.uploadZone.style.pointerEvents = 'none';
        this.uploadZone.style.opacity = '0.8';
    }

    resetUploadUI() {
        // Show upload content, hide progress
        this.uploadContent.style.display = 'block';
        this.uploadProgress.style.display = 'none';

        // Re-enable upload zone interaction
        this.uploadZone.style.pointerEvents = '';
        this.uploadZone.style.opacity = '';

        // Remove drag over state
        this.uploadZone.classList.remove('drag-over');
    }

    isUploading() {
        return this.currentUpload !== null;
    }

    getCurrentUpload() {
        return this.currentUpload;
    }
}

// File validation utilities
function validateVideoFile(file) {
    const errors = [];

    // Check if file exists
    if (!file) {
        errors.push('No file selected');
        return errors;
    }

    // Check file type
    if (!isValidVideoFormat(file.name)) {
        errors.push(`Unsupported format. Supported formats: ${window.APP_CONFIG.SUPPORTED_FORMATS.join(', ')}`);
    }

    // Check file size
    if (file.size > window.APP_CONFIG.MAX_FILE_SIZE) {
        errors.push(`File too large. Maximum size: ${formatFileSize(window.APP_CONFIG.MAX_FILE_SIZE)}`);
    }

    if (file.size === 0) {
        errors.push('File appears to be empty');
    }

    // Check file name length
    if (file.name.length > 255) {
        errors.push('Filename too long (maximum 255 characters)');
    }

    // Check for special characters that might cause issues
    if (/[<>:"/\\|?*]/.test(file.name)) {
        errors.push('Filename contains invalid characters');
    }

    return errors;
}

// Initialize upload manager when DOM is ready
let uploadManager;

document.addEventListener('DOMContentLoaded', () => {
    uploadManager = new UploadManager();
    console.log('Upload manager initialized');
});

// Export for global use
window.uploadManager = uploadManager;
