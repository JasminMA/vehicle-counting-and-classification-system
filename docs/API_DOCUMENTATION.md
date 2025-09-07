# Vehicle Analysis API Documentation

## Overview
The Vehicle Analysis API provides REST endpoints for uploading videos, checking processing status, and retrieving vehicle counting results. The API is built on AWS API Gateway with Lambda function backends.

## Base URL
```
https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/
```

**Example**: `https://abc123def4.execute-api.us-east-1.amazonaws.com/dev/`

## Authentication
Currently, the API is publicly accessible without authentication. All endpoints support CORS for web browser access.

## Rate Limiting
- **Default limits**: 10,000 requests per second, 5,000 burst
- **Throttling**: 429 status code when limits exceeded
- **Quotas**: Configurable per-client limits available

## Common Response Headers
All API responses include CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, X-Api-Key
```

## Error Response Format
All errors return consistent JSON format:
```json
{
  "error": "Human-readable error message",
  "timestamp": "2024-01-01T12:30:00Z"
}
```

---

## Endpoints

### 1. Upload Video
**`POST /upload`**

Generates a pre-signed S3 URL for secure video upload and creates a new analysis job.

#### Request Body
```json
{
  "filename": "traffic_video.mp4",
  "filesize": 125000000
}
```

**Parameters:**
- `filename` (string, required): Video filename with extension
  - Supported formats: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
  - Length: 1-255 characters
- `filesize` (integer, required): File size in bytes
  - Range: 1 byte to 8GB (8,589,934,592 bytes)

#### Response
**Success (200)**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "uploadUrl": "https://s3.amazonaws.com/bucket/uploads/job-123/video.mp4?X-Amz-Expires=3600&...",
  "expiresIn": 3600,
  "maxFileSize": 8589934592,
  "allowedFormats": ["mp4", "mov", "avi", "mkv", "webm"]
}
```

**Error Responses:**
- **400 Bad Request**: Invalid filename, filesize, or unsupported format
- **500 Internal Server Error**: Configuration error or AWS service issue

#### Example Usage
```javascript
// Upload request
const response = await fetch('/api/upload', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    filename: 'traffic_video.mp4',
    filesize: 125000000
  })
});

const { jobId, uploadUrl } = await response.json();

// Upload file to S3
const uploadResponse = await fetch(uploadUrl, {
  method: 'PUT',
  body: videoFile
});
```

---

### 2. Get Job Results
**`GET /results/{jobId}`**

Returns complete analysis results for completed jobs, or current status for pending/processing jobs.

#### Parameters
- `jobId` (path, required): Job identifier (e.g., "job-20240101-120000-abc123")
- `details` (query, optional): Include detailed timeline data
  - Values: `true` (default), `false`
  - When `false`, timeline is limited to first 10 entries

#### Response

**Success (200) - Completed Job**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "status": "completed",
  "results": {
    "video_info": {
      "filename": "traffic_video.mp4",
      "duration_seconds": 120.5,
      "frame_rate": 30,
      "format": "mp4",
      "processed_at": "2024-01-01T12:30:00Z",
      "analysis_id": "job-20240101-120000-abc123"
    },
    "vehicle_counts": {
      "cars": 45,
      "trucks": 8,
      "motorcycles": 12,
      "buses": 2,
      "vans": 5,
      "emergency_vehicles": 1,
      "total_vehicles": 73
    },
    "timeline": [
      {
        "timestamp": 5.2,
        "vehicle_type": "cars",
        "label_name": "Car",
        "confidence": 85.6
      },
      {
        "timestamp": 7.8,
        "vehicle_type": "trucks",
        "label_name": "Truck",
        "confidence": 92.1
      }
    ],
    "processing_stats": {
      "estimated_frames_analyzed": 3615,
      "total_detections": 1247,
      "analysis_duration_seconds": 120.5,
      "confidence_distribution": {
        "high_confidence": 892,
        "medium_confidence": 284,
        "low_confidence": 71
      },
      "detection_rate": 10.34
    },
    "confidence_threshold": 70.0,
    "total_detections": 1247
  }
}
```

**Success (200) - Processing Job**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "status": "processing",
  "message": "Video analysis in progress",
  "stage": "rekognition_running"
}
```

**Success (200) - Failed Job**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "status": "failed",
  "error": "Video format not supported",
  "timestamp": "2024-01-01T12:15:00Z"
}
```

**Error Responses:**
- **400 Bad Request**: Invalid job ID format
- **404 Not Found**: Job does not exist

#### Example Usage
```javascript
// Get complete results
const response = await fetch(`/api/results/${jobId}`);
const data = await response.json();

if (data.status === 'completed') {
  console.log('Total vehicles:', data.results.vehicle_counts.total_vehicles);
} else if (data.status === 'processing') {
  console.log('Still processing, stage:', data.stage);
}
```

---

### 3. Get Job Status
**`GET /results/{jobId}/status`**

Returns only job status without full results data. Optimized for polling and status checks.

#### Parameters
- `jobId` (path, required): Job identifier

#### Response

**Success (200) - Completed**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "status": "completed",
  "completedAt": "2024-01-01T12:30:00Z",
  "message": "Analysis completed successfully"
}
```

**Success (200) - Processing**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "status": "processing",
  "stage": "rekognition_running",
  "startedAt": "2024-01-01T12:25:00Z"
}
```

**Success (200) - Failed**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "status": "failed",
  "error": "Video format not supported",
  "failedAt": "2024-01-01T12:15:00Z"
}
```

**Success (200) - Pending**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "status": "pending",
  "message": "Waiting to start processing"
}
```

#### Example Usage
```javascript
// Poll for completion
function pollJobStatus(jobId) {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/results/${jobId}/status`);
    const status = await response.json();
    
    if (status.status === 'completed') {
      clearInterval(interval);
      // Get full results
      const results = await fetch(`/api/results/${jobId}`);
      // Handle results...
    } else if (status.status === 'failed') {
      clearInterval(interval);
      console.error('Job failed:', status.error);
    }
    // Continue polling if still processing
  }, 10000); // Poll every 10 seconds
}
```

---

### 4. Download Results
**`GET /results/{jobId}/download/{format}`**

Generates secure pre-signed URLs for downloading result files.

#### Parameters
- `jobId` (path, required): Job identifier
- `format` (path, required): File format
  - Values: `json`, `csv`

#### Response

**Success (200)**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "format": "json",
  "downloadUrl": "https://s3.amazonaws.com/bucket/results/job-123/analysis.json?X-Amz-Expires=3600&...",
  "filename": "vehicle_analysis_job-20240101-120000-abc123.json",
  "expiresIn": 3600
}
```

**File Formats:**

**JSON Format** (`/download/json`):
- Complete analysis results in JSON format
- Includes all vehicle counts, timeline, and statistics
- Human-readable and machine-parseable

**CSV Format** (`/download/csv`):
- Detailed detection data in CSV format
- Columns: timestamp, vehicle_type, label_name, confidence, bbox_left, bbox_top, bbox_width, bbox_height
- Suitable for spreadsheet analysis

**Error Responses:**
- **400 Bad Request**: Invalid format (only json/csv supported)
- **404 Not Found**: Job not completed or results not available

#### Example Usage
```javascript
// Download JSON results
const response = await fetch(`/api/results/${jobId}/download/json`);
const data = await response.json();

if (data.downloadUrl) {
  // Open download in new tab
  window.open(data.downloadUrl, '_blank');
  
  // Or download programmatically
  const fileResponse = await fetch(data.downloadUrl);
  const blob = await fileResponse.blob();
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = data.filename;
  link.click();
}
```

---

### 5. Health Check
**`GET /health`**

Simple health check endpoint for monitoring API availability.

#### Response

**Success (200)**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:30:00Z",
  "environment": "dev",
  "version": "1.0.0"
}
```

#### Example Usage
```javascript
// Health check
const response = await fetch('/api/health');
const health = await response.json();

if (health.status === 'healthy') {
  console.log('API is operational');
}
```

---

## Job Status Flow

Jobs progress through the following states:

```
Upload → Pending → Processing → Completed/Failed
```

### Status Descriptions

- **Pending**: Video uploaded, waiting for processing to start
- **Processing**: AI analysis in progress (1-5 minutes typical)
- **Completed**: Analysis finished successfully, results available
- **Failed**: Processing failed due to error (format, size, etc.)

### Typical Processing Times

- **1-5 minute video**: 30-90 seconds
- **5-15 minute video**: 1-3 minutes  
- **15-30 minute video**: 3-5 minutes

## Error Codes

### HTTP Status Codes
- **200**: Success
- **400**: Bad Request (invalid input)
- **404**: Not Found (job/resource doesn't exist)
- **405**: Method Not Allowed (wrong HTTP method)
- **429**: Too Many Requests (rate limited)
- **500**: Internal Server Error (AWS service issue)

### Common Error Messages

**Upload Errors:**
- "Missing 'filename' in request"
- "File too large. Maximum size: 8GB"
- "Unsupported file format. Allowed formats: mp4, mov, avi, mkv, webm"

**Results Errors:**
- "Job not found"
- "Invalid jobId format"
- "Results not available for download"

**Validation Errors:**
- "Invalid format. Supported formats: json, csv"
- "Missing jobId in path parameters"

## API Limits

### File Upload Limits
- **Maximum file size**: 8GB
- **Maximum video length**: 30 minutes (recommended)
- **Supported formats**: MP4, MOV, AVI, MKV, WEBM

### Request Limits
- **Upload URL expiration**: 1 hour
- **Download URL expiration**: 1 hour
- **Job retention**: 30 days (automatically deleted)

### Processing Limits
- **Concurrent jobs**: Multiple jobs can be processed simultaneously
- **Queue depth**: No hard limit, but longer videos take more time
- **Retry attempts**: Automatic retry on transient failures

## Integration Examples

### Complete Frontend Integration
```javascript
class VehicleAnalysisAPI {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async uploadVideo(file) {
    // 1. Get upload URL
    const uploadResponse = await fetch(`${this.baseUrl}/upload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: file.name,
        filesize: file.size
      })
    });

    if (!uploadResponse.ok) {
      throw new Error('Failed to get upload URL');
    }

    const { jobId, uploadUrl } = await uploadResponse.json();

    // 2. Upload file to S3
    const fileUploadResponse = await fetch(uploadUrl, {
      method: 'PUT',
      body: file
    });

    if (!fileUploadResponse.ok) {
      throw new Error('Failed to upload file');
    }

    return jobId;
  }

  async waitForCompletion(jobId, onProgress) {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const response = await fetch(`${this.baseUrl}/results/${jobId}/status`);
          const status = await response.json();

          if (onProgress) onProgress(status);

          if (status.status === 'completed') {
            const results = await this.getResults(jobId);
            resolve(results);
          } else if (status.status === 'failed') {
            reject(new Error(status.error));
          } else {
            setTimeout(poll, 10000); // Poll every 10 seconds
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }

  async getResults(jobId) {
    const response = await fetch(`${this.baseUrl}/results/${jobId}`);
    if (!response.ok) {
      throw new Error('Failed to get results');
    }
    return response.json();
  }

  async downloadResults(jobId, format = 'json') {
    const response = await fetch(`${this.baseUrl}/results/${jobId}/download/${format}`);
    if (!response.ok) {
      throw new Error('Failed to get download URL');
    }
    
    const data = await response.json();
    window.open(data.downloadUrl, '_blank');
    return data;
  }
}

// Usage
const api = new VehicleAnalysisAPI('https://api.example.com/dev');

async function analyzeVideo(videoFile) {
  try {
    // Upload video
    const jobId = await api.uploadVideo(videoFile);
    console.log('Upload successful, job ID:', jobId);

    // Wait for completion with progress updates
    const results = await api.waitForCompletion(jobId, (status) => {
      console.log('Status:', status.status, status.stage);
    });

    // Display results
    console.log('Analysis complete!');
    console.log('Total vehicles:', results.results.vehicle_counts.total_vehicles);

    // Download detailed results
    await api.downloadResults(jobId, 'csv');

  } catch (error) {
    console.error('Analysis failed:', error.message);
  }
}
```

### Python Backend Integration
```python
import requests
import time

class VehicleAnalysisAPI:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    def upload_video(self, file_path):
        """Upload video and return job ID"""
        import os
        
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)
        
        # Get upload URL
        response = requests.post(f"{self.base_url}/upload", json={
            'filename': filename,
            'filesize': filesize
        })
        response.raise_for_status()
        
        data = response.json()
        upload_url = data['uploadUrl']
        job_id = data['jobId']
        
        # Upload file
        with open(file_path, 'rb') as f:
            upload_response = requests.put(upload_url, data=f)
            upload_response.raise_for_status()
        
        return job_id
    
    def get_job_status(self, job_id):
        """Get current job status"""
        response = requests.get(f"{self.base_url}/results/{job_id}/status")
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, job_id, timeout=600):
        """Wait for job completion with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            if status['status'] == 'completed':
                return self.get_results(job_id)
            elif status['status'] == 'failed':
                raise Exception(f"Job failed: {status.get('error')}")
            
            print(f"Status: {status['status']}, Stage: {status.get('stage', 'unknown')}")
            time.sleep(10)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
    
    def get_results(self, job_id):
        """Get complete analysis results"""
        response = requests.get(f"{self.base_url}/results/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def download_results(self, job_id, format='json', save_path=None):
        """Download results file"""
        response = requests.get(f"{self.base_url}/results/{job_id}/download/{format}")
        response.raise_for_status()
        
        download_data = response.json()
        download_url = download_data['downloadUrl']
        filename = download_data['filename']
        
        # Download file
        file_response = requests.get(download_url)
        file_response.raise_for_status()
        
        if save_path:
            with open(save_path, 'wb') as f:
                f.write(file_response.content)
            return save_path
        else:
            return file_response.content

# Usage
api = VehicleAnalysisAPI('https://api.example.com/dev')

# Analyze video
job_id = api.upload_video('/path/to/video.mp4')
results = api.wait_for_completion(job_id)

print(f"Found {results['results']['vehicle_counts']['total_vehicles']} vehicles")

# Download CSV data
api.download_results(job_id, 'csv', 'analysis_results.csv')
```

---

## Monitoring & Debugging

### CloudWatch Logs
API Gateway logs are available in CloudWatch:
- **Log Group**: `/aws/apigateway/VehicleAnalysis-{environment}`
- **Log Level**: INFO (includes request/response details)
- **Retention**: 7 days

### Metrics
Monitor these CloudWatch metrics:
- **4XXError**: Client errors (bad requests)
- **5XXError**: Server errors (AWS issues)
- **Latency**: Response time
- **Count**: Request volume

### Debug Headers
Include these headers for debugging:
- **X-Amzn-RequestId**: Unique request identifier
- **X-Amzn-Trace-Id**: Request tracing ID

---

This API provides a complete interface for video upload, processing, and results retrieval with robust error handling and comprehensive monitoring capabilities.
