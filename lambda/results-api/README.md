# Results API Lambda Function

## Overview
The Results API Lambda function provides REST API endpoints for retrieving vehicle analysis job status and results. It serves as the backend API that the web UI calls to check job progress and download completed analysis reports.

## API Endpoints

### 1. Get Job Results
**Endpoint**: `GET /results/{jobId}`

Returns complete analysis results for a completed job, or current status for pending/processing jobs.

**Parameters**:
- `jobId` (path): Job identifier (e.g., "job-20240101-120000-abc123")
- `details` (query, optional): Include detailed timeline data (default: true)

**Example Request**:
```
GET /results/job-20240101-120000-abc123?details=false
```

**Responses**:

**Success (200) - Completed Job**:
```json
{
  "jobId": "job-20240101-120000-abc123",
  "status": "completed",
  "results": {
    "video_info": {
      "filename": "traffic_video.mp4",
      "duration_seconds": 120.5,
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
      }
    ],
    "processing_stats": {
      "total_detections": 1247,
      "analysis_duration_seconds": 120.5,
      "confidence_distribution": {
        "high_confidence": 892,
        "medium_confidence": 284,
        "low_confidence": 71
      }
    }
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

**Error (404) - Job Not Found**:
```json
{
  "error": "Job not found",
  "timestamp": "2024-01-01T12:30:00Z"
}
```

### 2. Get Job Status Only
**Endpoint**: `GET /results/{jobId}/status`

Returns only the job status without full results data (faster, lighter response).

**Example Request**:
```
GET /results/job-20240101-120000-abc123/status
```

**Responses**:

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

### 3. Download Results Files
**Endpoint**: `GET /results/{jobId}/download/{format}`

Generates pre-signed URLs for downloading result files in different formats.

**Parameters**:
- `jobId` (path): Job identifier
- `format` (path): File format ("json" or "csv")

**Example Requests**:
```
GET /results/job-20240101-120000-abc123/download/json
GET /results/job-20240101-120000-abc123/download/csv
```

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

**Error (400) - Invalid Format**:
```json
{
  "error": "Invalid format. Supported formats: json, csv",
  "timestamp": "2024-01-01T12:30:00Z"
}
```

**Error (404) - Results Not Available**:
```json
{
  "error": "Results not available for download",
  "timestamp": "2024-01-01T12:30:00Z"
}
```

## Job Status Flow

The API tracks jobs through different states based on S3 file markers:

```
Upload → Pending → Processing → Completed/Failed
```

### Status Detection Logic

1. **Completed**: `results/{jobId}/completed.json` exists
2. **Failed**: `errors/{jobId}/error.json` exists  
3. **Processing**: `processing/{jobId}.processing` exists
4. **Pending**: `uploads/{jobId}/` contains files but no processing marker
5. **Not Found**: No files found for the job ID

## Configuration

### Environment Variables
- `STORAGE_BUCKET_NAME`: S3 bucket name for accessing job files
- `ENVIRONMENT`: Deployment environment (dev/prod)

### Lambda Configuration
- **Runtime**: Python 3.9
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Trigger**: API Gateway (multiple endpoints)

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:HeadObject"
      ],
      "Resource": [
        "arn:aws:s3:::bucket-name",
        "arn:aws:s3:::bucket-name/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream", 
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security Features

### Input Validation
- **Job ID Format**: Must start with "job-" and be 10-100 characters
- **Path Traversal Protection**: Blocks "../", "/", "\" characters
- **HTTP Method Validation**: Only GET requests allowed
- **Format Validation**: Only "json" and "csv" formats for downloads

### CORS Configuration
```json
{
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "GET,OPTIONS"
}
```

### Download Security
- **Pre-signed URLs**: Secure, time-limited access (1 hour)
- **Content-Disposition**: Proper filename handling
- **Content-Type**: Correct MIME types for downloads

## Error Handling

### Error Response Format
All errors return consistent JSON format:
```json
{
  "error": "Human-readable error message",
  "timestamp": "2024-01-01T12:30:00Z"
}
```

### Error Codes
- **400**: Bad Request (invalid job ID, format, etc.)
- **404**: Not Found (job doesn't exist, results not available)
- **405**: Method Not Allowed (non-GET requests)
- **500**: Internal Server Error (configuration issues, AWS errors)

### Logging
Comprehensive logging for debugging:
```python
# Example log entries
INFO: Results API called with jobId: job-test-123
INFO: Successfully retrieved results for job job-test-123
WARNING: Results file not found for job job-test-123
ERROR: Error retrieving results for job job-test-123: S3 access denied
```

## Performance Characteristics

### Response Times
- **Status check**: 50-200ms
- **Results retrieval**: 100-500ms (depends on result size)
- **Download URL generation**: 100-300ms

### Caching Strategy
- **No caching headers**: Results can change as jobs complete
- **Cache-Control**: "no-cache" to ensure fresh data
- **ETag support**: Could be added for result files

### Scalability
- **Concurrent requests**: Handles multiple requests simultaneously
- **Memory efficient**: Streams large files, minimal memory usage
- **API Gateway integration**: Auto-scaling and throttling

## Testing

### Unit Tests Coverage
- ✅ All API endpoints (results, status, download)
- ✅ Job status detection logic
- ✅ Input validation and security
- ✅ Error handling scenarios
- ✅ S3 integration and file operations
- ✅ Pre-signed URL generation

### Integration Tests
- ✅ Complete workflow testing (pending → processing → completed)
- ✅ Error scenarios (failed jobs, missing files)
- ✅ CORS and security headers
- ✅ Download functionality

### Test Execution
```bash
# Run all tests
pytest lambda/tests/test_results_api.py -v

# Run specific test class
pytest lambda/tests/test_results_api.py::TestAPIEndpoints -v

# Run with coverage
pytest lambda/tests/test_results_api.py --cov=handler --cov-report=html
```

## Usage Examples

### JavaScript/Frontend Integration
```javascript
// Check job status
async function checkJobStatus(jobId) {
  const response = await fetch(`/api/results/${jobId}/status`);
  const data = await response.json();
  return data;
}

// Get complete results
async function getJobResults(jobId) {
  const response = await fetch(`/api/results/${jobId}`);
  if (response.ok) {
    return await response.json();
  }
  throw new Error('Failed to get results');
}

// Download results
async function downloadResults(jobId, format) {
  const response = await fetch(`/api/results/${jobId}/download/${format}`);
  const data = await response.json();
  
  if (data.downloadUrl) {
    window.open(data.downloadUrl, '_blank');
  }
}

// Polling for completion
async function pollJobCompletion(jobId, callback) {
  const poll = async () => {
    try {
      const status = await checkJobStatus(jobId);
      
      if (status.status === 'completed') {
        const results = await getJobResults(jobId);
        callback(null, results);
      } else if (status.status === 'failed') {
        callback(new Error(status.error));
      } else {
        // Still processing, poll again in 10 seconds
        setTimeout(poll, 10000);
      }
    } catch (error) {
      callback(error);
    }
  };
  
  poll();
}
```

### Python/Backend Integration
```python
import requests
import time

class VehicleAnalysisAPI:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_job_status(self, job_id):
        response = requests.get(f"{self.base_url}/results/{job_id}/status")
        return response.json()
    
    def get_job_results(self, job_id):
        response = requests.get(f"{self.base_url}/results/{job_id}")
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get results: {response.text}")
    
    def wait_for_completion(self, job_id, timeout=300):
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            if status['status'] == 'completed':
                return self.get_job_results(job_id)
            elif status['status'] == 'failed':
                raise Exception(f"Job failed: {status.get('error')}")
            
            time.sleep(10)  # Poll every 10 seconds
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
```

## Monitoring & Alerting

### CloudWatch Metrics
- **Invocation count**: Track API usage
- **Duration**: Monitor response times
- **Error rate**: Track failed requests
- **4xx/5xx errors**: Monitor client vs server errors

### Custom Alarms
```yaml
# CloudWatch Alarms (example)
HighErrorRate:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: ResultsAPI-HighErrorRate
    MetricName: Errors
    Threshold: 10
    ComparisonOperator: GreaterThanThreshold
    EvaluationPeriods: 2

SlowResponses:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: ResultsAPI-SlowResponses
    MetricName: Duration
    Threshold: 5000  # 5 seconds
    ComparisonOperator: GreaterThanThreshold
```

### Health Check Endpoint
Consider adding a health check endpoint:
```python
# GET /health
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }
```

## Cost Optimization

### Request Optimization
- **Lightweight status checks**: Use `/status` endpoint for polling
- **Conditional requests**: Could implement ETag support
- **Result pagination**: Limit timeline entries in responses

### S3 Optimization
- **Head requests**: Use `HeadObject` for existence checks (cheaper than `GetObject`)
- **Pre-signed URLs**: Offload downloads from Lambda to S3 direct access

## Deployment

### Infrastructure Deployment
The function is automatically deployed as part of the Lambda stack:
```bash
cd infrastructure
npm run build
cdk deploy --all -c environment=dev
```

### API Gateway Integration
The function will be integrated with API Gateway endpoints:
- `/results/{jobId}` → Results Lambda
- `/results/{jobId}/status` → Results Lambda  
- `/results/{jobId}/download/{format}` → Results Lambda

---

This Results API Lambda provides a robust, secure, and scalable backend for serving vehicle analysis results to frontend applications with comprehensive error handling and monitoring capabilities.
