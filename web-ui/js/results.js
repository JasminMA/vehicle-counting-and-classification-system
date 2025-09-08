// Results display functionality for Vehicle Analysis System

class ResultsUI {
    constructor() {
        this.resultsSection = null;
        this.resultsContent = null;
        this.downloadJsonBtn = null;
        this.downloadCsvBtn = null;
        this.closeResultsBtn = null;
        this.currentJobId = null;
        this.currentResults = null;
        
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.resultsSection = document.getElementById('resultsSection');
        this.resultsContent = document.getElementById('resultsContent');
        this.downloadJsonBtn = document.getElementById('downloadJson');
        this.downloadCsvBtn = document.getElementById('downloadCsv');
        this.closeResultsBtn = document.getElementById('closeResults');
    }

    bindEvents() {
        // Download buttons
        if (this.downloadJsonBtn) {
            this.downloadJsonBtn.addEventListener('click', () => {
                this.downloadResults('json');
            });
        }

        if (this.downloadCsvBtn) {
            this.downloadCsvBtn.addEventListener('click', () => {
                this.downloadResults('csv');
            });
        }

        // Close button
        if (this.closeResultsBtn) {
            this.closeResultsBtn.addEventListener('click', () => {
                this.hideResults();
            });
        }
    }

    showResults(results, jobId) {
        this.currentResults = results;
        this.currentJobId = jobId;
        
        // Generate and display results content
        this.renderResults(results);
        
        // Show results section
        this.resultsSection.style.display = 'block';
        
        // Add fade-in animation
        animateIn(this.resultsSection, 'fade-in');
        
        console.log('Showing results for job:', jobId);
    }

    hideResults() {
        this.resultsSection.style.display = 'none';
        this.currentResults = null;
        this.currentJobId = null;
        
        console.log('Results hidden');
    }

    renderResults(results) {
        const html = this.generateResultsHTML(results);
        this.resultsContent.innerHTML = html;
        
        // Bind timeline events after rendering
        this.bindTimelineEvents();
    }

    generateResultsHTML(results) {
        const overview = this.generateOverviewHTML(results);
        const timeline = this.generateTimelineHTML(results);
        
        return `
            ${overview}
            ${timeline}
        `;
    }

    generateOverviewHTML(results) {
        const videoInfo = results.video_info || {};
        const vehicleCounts = results.vehicle_counts || {};
        const stats = results.processing_stats || {};
        
        // Generate summary cards
        const summaryCards = this.generateSummaryCards(vehicleCounts);
        
        // Generate video information
        const videoInfoHTML = this.generateVideoInfoHTML(videoInfo, stats);
        
        return `
            <div class="results-overview">
                <div class="results-summary">
                    ${summaryCards}
                </div>
                ${videoInfoHTML}
            </div>
        `;
    }

    generateSummaryCards(vehicleCounts) {
        const cards = [];
        
        // Total vehicles (prominent)
        if (vehicleCounts.total_vehicles !== undefined) {
            cards.push(`
                <div class="summary-card">
                    <div class="summary-number">${vehicleCounts.total_vehicles}</div>
                    <div class="summary-label">Total Vehicles</div>
                </div>
            `);
        }
        
        // Individual vehicle types
        const vehicleTypes = [
            { key: 'cars', label: 'Cars', emoji: '🚗' },
            { key: 'trucks', label: 'Trucks', emoji: '🚛' },
            { key: 'motorcycles', label: 'Motorcycles', emoji: '🏍️' },
            { key: 'buses', label: 'Buses', emoji: '🚌' },
            { key: 'vans', label: 'Vans', emoji: '🚐' },
            { key: 'emergency_vehicles', label: 'Emergency', emoji: '🚑' }
        ];
        
        vehicleTypes.forEach(type => {
            if (vehicleCounts[type.key] && vehicleCounts[type.key] > 0) {
                cards.push(`
                    <div class="summary-card">
                        <div class="summary-number">${vehicleCounts[type.key]}</div>
                        <div class="summary-label">${type.emoji} ${type.label}</div>
                    </div>
                `);
            }
        });
        
        return cards.join('');
    }

    generateVideoInfoHTML(videoInfo, stats) {
        const infoItems = [];
        
        // Basic video information
        if (videoInfo.filename) {
            infoItems.push({
                label: 'Filename',
                value: videoInfo.filename
            });
        }
        
        if (videoInfo.duration_seconds) {
            infoItems.push({
                label: 'Duration',
                value: formatDuration(videoInfo.duration_seconds)
            });
        }
        
        if (videoInfo.frame_rate) {
            infoItems.push({
                label: 'Frame Rate',
                value: `${Math.round(videoInfo.frame_rate * 100) / 100} fps`
            });
        }
        
        if (videoInfo.format) {
            // Clean up format string for better display
            let formatDisplay = videoInfo.format;
            if (formatDisplay.includes('/')) {
                // Take the more common format name
                formatDisplay = formatDisplay.split('/')[0].trim();
            }
            infoItems.push({
                label: 'Format',
                value: formatDisplay
            });
        }
        
        if (videoInfo.processed_at) {
            infoItems.push({
                label: 'Processed',
                value: formatTimestamp(videoInfo.processed_at)
            });
        }
        
        // Processing statistics
        if (stats.total_detections) {
            infoItems.push({
                label: 'Total Detections',
                value: stats.total_detections.toLocaleString()
            });
        }
        
        if (stats.estimated_frames_analyzed) {
            infoItems.push({
                label: 'Frames Analyzed',
                value: stats.estimated_frames_analyzed.toLocaleString()
            });
        }
        
        if (stats.detection_rate) {
            infoItems.push({
                label: 'Detection Rate',
                value: `${stats.detection_rate}/sec`
            });
        }
        
        // Confidence distribution
        if (stats.confidence_distribution) {
            const dist = stats.confidence_distribution;
            const total = (dist.high_confidence || 0) + (dist.medium_confidence || 0) + (dist.low_confidence || 0);
            if (total > 0) {
                const highPct = Math.round((dist.high_confidence || 0) / total * 100);
                infoItems.push({
                    label: 'High Confidence',
                    value: `${highPct}% (${dist.high_confidence || 0})`
                });
            }
        }
        
        // Generate HTML
        const infoHTML = infoItems.map(item => `
            <div class="info-row">
                <span class="info-label">${item.label}:</span>
                <span class="info-value">${item.value}</span>
            </div>
        `).join('');
        
        return `
            <div class="video-info">
                ${infoHTML}
            </div>
        `;
    }

    generateTimelineHTML(results) {
        const timeline = results.timeline || [];
        
        if (timeline.length === 0) {
            return `
                <div class="timeline-section">
                    <div class="timeline-header">
                        <h3>Detection Timeline</h3>
                    </div>
                    <div class="empty-timeline">
                        <p>No vehicle detections found in timeline</p>
                    </div>
                </div>
            `;
        }
        
        // Limit timeline items for performance
        const displayedTimeline = timeline.slice(0, 100);
        const hasMore = timeline.length > 100;
        
        const timelineItems = displayedTimeline.map(item => this.generateTimelineItem(item)).join('');
        
        const moreMessage = hasMore ? `
            <div class="timeline-more">
                <p>Showing first 100 of ${timeline.length} detections. Download CSV for complete data.</p>
            </div>
        ` : '';
        
        return `
            <div class="timeline-section">
                <div class="timeline-header">
                    <h3>Detection Timeline</h3>
                    <div class="timeline-controls">
                        <button class="btn btn-outline" id="filterTimeline">Filter</button>
                        <button class="btn btn-outline" id="exportTimeline">Export</button>
                    </div>
                </div>
                <div class="timeline-container">
                    ${timelineItems}
                    ${moreMessage}
                </div>
            </div>
        `;
    }

    generateTimelineItem(item) {
        const time = formatVideoTimestamp(item.timestamp);
        const emoji = getVehicleEmoji(item.vehicle_type);
        const confidence = formatConfidence(item.confidence);
        
        return `
            <div class="timeline-item" data-timestamp="${item.timestamp}" data-type="${item.vehicle_type}">
                <div class="timeline-time">${time}</div>
                <div class="timeline-type">
                    ${emoji} ${item.label_name || item.vehicle_type}
                </div>
                <div class="timeline-confidence">${confidence}</div>
            </div>
        `;
    }

    bindTimelineEvents() {
        // Filter button
        const filterBtn = document.getElementById('filterTimeline');
        if (filterBtn) {
            filterBtn.addEventListener('click', this.showTimelineFilter.bind(this));
        }
        
        // Export button
        const exportBtn = document.getElementById('exportTimeline');
        if (exportBtn) {
            exportBtn.addEventListener('click', this.exportTimeline.bind(this));
        }
        
        // Timeline item clicks (for future enhancements)
        const timelineItems = document.querySelectorAll('.timeline-item');
        timelineItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const timestamp = item.dataset.timestamp;
                const type = item.dataset.type;
                this.onTimelineItemClick(timestamp, type);
            });
        });
    }

    showTimelineFilter() {
        // Simple filter implementation
        const filterTypes = ['all', 'cars', 'trucks', 'motorcycles', 'buses', 'vans', 'emergency_vehicles'];
        
        const filterHTML = filterTypes.map(type => 
            `<option value="${type}">${type === 'all' ? 'All Types' : type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>`
        ).join('');
        
        const filterSelect = DOM.create('select', { 
            className: 'timeline-filter',
            innerHTML: filterHTML
        });
        
        filterSelect.addEventListener('change', (e) => {
            this.filterTimeline(e.target.value);
        });
        
        // Add filter to timeline controls
        const controls = document.querySelector('.timeline-controls');
        if (controls) {
            // Remove existing filter
            const existingFilter = controls.querySelector('.timeline-filter');
            if (existingFilter) {
                existingFilter.remove();
            }
            
            controls.insertBefore(filterSelect, controls.firstChild);
        }
    }

    filterTimeline(filterType) {
        const timelineItems = document.querySelectorAll('.timeline-item');
        
        timelineItems.forEach(item => {
            const itemType = item.dataset.type;
            
            if (filterType === 'all' || itemType === filterType) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
        
        // Update visible count
        const visibleItems = document.querySelectorAll('.timeline-item:not([style*="display: none"])');
        showToast(`Showing ${visibleItems.length} detections`, 'info', 2000);
    }

    exportTimeline() {
        if (!this.currentResults || !this.currentResults.timeline) {
            showToast('No timeline data to export', 'error');
            return;
        }
        
        // Convert timeline to CSV
        const timeline = this.currentResults.timeline;
        const csvContent = this.timelineToCSV(timeline);
        
        // Create and download file
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        
        const filename = `timeline_${this.currentJobId}_${new Date().toISOString().split('T')[0]}.csv`;
        downloadFile(url, filename);
        
        // Cleanup
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        
        showToast('Timeline exported to CSV', 'success');
    }

    timelineToCSV(timeline) {
        const headers = ['timestamp', 'video_time', 'vehicle_type', 'label_name', 'confidence'];
        const rows = timeline.map(item => [
            item.timestamp,
            formatVideoTimestamp(item.timestamp),
            item.vehicle_type,
            item.label_name || item.vehicle_type,
            item.confidence
        ]);
        
        const csvRows = [headers, ...rows];
        return csvRows.map(row => row.map(field => `"${field}"`).join(',')).join('\n');
    }

    onTimelineItemClick(timestamp, type) {
        // Future enhancement: could show more details or seek to video timestamp
        console.log('Timeline item clicked:', { timestamp, type });
        
        // For now, just show a tooltip with more info
        showToast(`${type} detected at ${formatVideoTimestamp(timestamp)}`, 'info', 2000);
    }

    async downloadResults(format) {
        if (!this.currentJobId) {
            showToast('No results available for download', 'error');
            return;
        }

        try {
            await api.downloadResults(this.currentJobId, format);
            showToast(`${format.toUpperCase()} download started`, 'success');
        } catch (error) {
            console.error('Download error:', error);
            showToast(`Download failed: ${error.message}`, 'error');
        }
    }
}

// Initialize results UI when DOM is ready
let resultsUI;

document.addEventListener('DOMContentLoaded', () => {
    resultsUI = new ResultsUI();
    
    // Make resultsUI immediately available globally
    window.resultsUI = resultsUI;
    
    console.log('Results UI initialized and available globally');
});

// Export for global use
// Note: window.resultsUI is set in the DOMContentLoaded event handler
