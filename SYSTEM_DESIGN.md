# Vehicle Counting and Classification System - Design Document

## Overview
A simplified AWS-based system for counting and classifying vehicles in uploaded videos. Designed for single-user operation with minimal complexity and cost optimization.

## System Architecture

### Simplified Architecture for Single User

```
[User] → [S3 Static Website] → [API Gateway] → [Lambda] → [S3 Bucket] → [Rekognition Video]
           ↓                    ↓                              ↓
[Results View] ← [Lambda API] ← [Lambda Processor] ← [Rekognition Results]
```

### Core Components

#### 1. **Video Storage (S3)**
- **Input Bucket**: `vehicle-videos-input-[account-id]`
  - Single upload location for video files
  - Lifecycle policy to delete videos after 30 days (cost optimization)
- **Results Bucket**: `vehicle-analysis-results-[account-id]`
  - Stores JSON results and summary reports
  - Organized by date/timestamp folders

#### 2. **Video Analysis (AWS Rekognition Video)**
- Uses `DetectLabels` API for object detection
- Automatically detects and tracks vehicles frame by frame
- Provides confidence scores and bounding boxes
- No custom training required

#### 3. **Simple Web UI (S3 Static Website)**
- **Static Website Hosting**: Single-page application (HTML/CSS/JavaScript)
- **Direct HTTP Access**: No CDN needed for single user
- **Features**:
  - Drag & drop video upload interface
  - Upload progress tracking
  - Real-time job status monitoring
  - Results viewing and download
  - Simple, clean interface optimized for single user
- **Access URL**: `http://bucket-name.s3-website-region.amazonaws.com`

#### 4. **API Layer (API Gateway + Lambda)**
- **Upload API** (`/upload`): Generates pre-signed S3 URLs for secure upload
- **Results API** (`/results/{jobId}`): Returns analysis results when processing is complete

#### 5. **Processing Logic (AWS Lambda)**
- **Function 1: Upload Handler** (`handle-upload-request`)
  - Generates pre-signed S3 upload URLs
  - Returns job ID for tracking
  - Runtime: Python 3.13, Timeout: 30 seconds

- **Function 2: Video Processor** (`process-video-upload`)
  - Triggered by S3 upload event
  - Starts Rekognition Video analysis job
  - Runtime: Python 3.13, Timeout: 5 minutes
  
- **Function 3: Results Processor** (`process-rekognition-results`)
  - Triggered by Rekognition job completion (SNS)
  - Filters and classifies vehicle detections
  - Generates summary reports and saves to S3
  - Runtime: Python 3.13, Timeout: 10 minutes

- **Function 4: Results API Handler** (`get-results`)
  - Returns analysis results from S3
  - Only responds when processing is complete
  - Runtime: Python 3.13, Timeout: 30 seconds

#### 6. **Job Tracking (S3 Metadata + File-based)**
- **No DynamoDB needed**: Use S3 object metadata and file naming conventions
- **Job Tracking Method**: 
  - Upload creates: `uploads/{job-id}/{filename}.mp4`
  - Processing creates: `processing/{job-id}.processing` (empty marker file)
  - Completion creates: `results/{job-id}/analysis.json`
  - Error creates: `errors/{job-id}/error.json`
- **Status Detection**: Check file existence in S3 folders

#### 7. **Notification System (SNS)**
- Topic: `vehicle-analysis-notifications`
- Sends completion notifications
- Can email user when analysis is complete

#### 8. **Monitoring (CloudWatch)**
- Logs from Lambda functions
- Basic metrics and alarms
- Cost monitoring dashboard

## Vehicle Classification Strategy

### Supported Vehicle Types
Using AWS Rekognition's built-in labels:
- **Cars** (Car, Sedan, Coupe, Convertible)
- **Trucks** (Truck, Pickup Truck, Semi Truck, Delivery Truck)
- **Motorcycles** (Motorcycle, Scooter)
- **Buses** (Bus, School Bus)
- **Vans** (Van, Minivan)
- **Emergency Vehicles** (Ambulance, Fire Truck, Police Car)

### Classification Logic
1. Filter Rekognition results for vehicle-related labels
2. Apply confidence threshold (>80%)
3. Group similar vehicle types
4. Count unique instances using tracking IDs
5. Remove duplicate detections across frames

## Data Flow

### 1. Video Upload via Web UI
```
User selects video → Web UI → API Gateway → Lambda (generate pre-signed URL)
                                ↓
Web UI uploads directly to S3 → S3 Event → Video Processor Lambda
```

### 2. Job Tracking via S3 Structure
```
Upload Handler → Creates upload file in S3 → Returns Job ID to UI
                        ↓
Web UI polls Results API → Checks S3 for results file → Returns status
```

### 3. Processing
```
Video Processor → Start Rekognition Job → Create processing marker in S3
                         ↓
SNS Notification → Results Processor Lambda
```

### 4. Results
```
Results Lambda → Process Detections → Save results to S3 → Remove processing marker
                        ↓
Web UI → Results API → Finds results file → Web UI shows results
```

## Output Format

### Summary Report (JSON)
```json
{
  "video_info": {
    "filename": "traffic_video.mp4",
    "duration_seconds": 120,
    "processed_at": "2024-01-15T10:30:00Z",
    "analysis_id": "job-12345"
  },
  "vehicle_counts": {
    "cars": 45,
    "trucks": 8,
    "motorcycles": 12,
    "buses": 2,
    "vans": 5,
    "total_vehicles": 72
  },
  "timeline": [
    {
      "timestamp": 5.2,
      "vehicle_type": "car",
      "confidence": 85.6,
      "tracking_id": "track_001"
    }
  ],
  "processing_stats": {
    "total_frames_analyzed": 3600,
    "analysis_duration_seconds": 45
  }
}
```

### CSV Export
```csv
timestamp,vehicle_type,confidence,tracking_id,x,y,width,height
5.2,car,85.6,track_001,120,340,80,45
7.8,truck,92.1,track_002,450,280,120,90
```

## Cost Optimization Features

### Single User Optimizations
- **Simple Static Website**: No complex frontend framework needed
- **Direct S3 Access**: No CDN overhead for single user
- **File-based Job Tracking**: No database needed, use S3 file structure
- **Pre-signed URLs**: Direct S3 upload reduces Lambda costs
- **Auto-cleanup**: Videos and old job files deleted after 30 days
- **Basic monitoring**: Essential CloudWatch only
- **Minimal API**: Only upload and results endpoints

### Estimated Monthly Costs (Light Usage)
- **S3 Storage**: $2-5 (with lifecycle policies)
- **API Gateway**: $1-2 (only 2 endpoints, low request volume)
- **Lambda Execution**: $3-10 (depending on video length/frequency)
- **Rekognition Video**: $0.10 per minute of video processed
- **SNS Notifications**: <$1
- **Total**: ~$8-18/month for moderate usage (10-20 videos)

## Security & Access

### IAM Roles
- **Lambda Execution Role**: Minimal permissions for S3, Rekognition, SNS
- **User Access**: S3 console access or programmatic access via CLI
- **No public endpoints**: Everything within AWS account

### Security Features
- Bucket policies restrict access to account owner
- Lambda functions use least-privilege IAM roles
- Video files auto-deleted after processing
- Results encrypted at rest (S3 default encryption)

## Deployment Strategy

### Infrastructure as Code
- **AWS CloudFormation** template for entire stack
- Single deployment command
- Easy teardown when not needed
- Version controlled infrastructure

### Manual Alternative
- Step-by-step AWS Console setup guide
- For users preferring GUI over code
- Same functionality, manual configuration

## Usage Workflow

### For the Single User:
1. **Access Web UI**: Open the S3 website URL in browser
2. **Upload Video**: Drag & drop video file to upload area
3. **Monitor Progress**: Watch real-time status updates on the page
4. **View Results**: Browse analysis results directly in the web interface
5. **Download Reports**: Download JSON/CSV files for further analysis

### Alternative: Command Line Option:
```bash
# Upload video (still supported)
aws s3 cp my_video.mp4 s3://vehicle-analysis-bucket-123456789/uploads/manual-job-$(date +%s)/

# Check for results
aws s3 ls s3://vehicle-analysis-bucket-123456789/results/

# Download results
aws s3 sync s3://vehicle-analysis-bucket-123456789/results/job-id/ ./results/
```

## Monitoring & Troubleshooting

### CloudWatch Dashboards
- Processing status and errors
- Cost tracking
- Performance metrics

### Logging Strategy
- Detailed Lambda logs for debugging
- S3 access logs for audit trail
- Rekognition job status tracking

## Web UI Implementation Details

### Frontend Architecture
- **Technology Stack**: Vanilla HTML5, CSS3, JavaScript (ES6+)
- **No Framework Dependencies**: Keeps it simple and lightweight
- **Responsive Design**: Works on desktop and mobile devices
- **Modern Browser Features**: File API, Fetch API, WebSockets (future)

### UI Components

#### 1. **Upload Interface**
```html
<div class="upload-zone">
  <input type="file" accept="video/*" id="video-input">
  <div class="drag-drop-area">
    <p>Drag & drop video file or click to browse</p>
    <div class="upload-progress" style="display:none">
      <div class="progress-bar"></div>
      <span class="progress-text">0%</span>
    </div>
  </div>
</div>
```

#### 2. **Job Status Dashboard**
```html
<div class="jobs-dashboard">
  <h2>Processing Jobs</h2>
  <div class="job-list">
    <!-- Dynamically populated job cards -->
  </div>
</div>
```

#### 3. **Results Viewer**
```html
<div class="results-container">
  <div class="summary-stats">
    <!-- Vehicle count summary -->
  </div>
  <div class="timeline-view">
    <!-- Interactive timeline -->
  </div>
  <div class="download-options">
    <!-- JSON/CSV download buttons -->
  </div>
</div>
```

### Key JavaScript Functions

#### Upload Handler
```javascript
async function uploadVideo(file) {
  // 1. Request pre-signed URL from API
  const response = await fetch('/api/upload', {
    method: 'POST',
    body: JSON.stringify({ filename: file.name, filesize: file.size })
  });
  
  // 2. Upload directly to S3 using pre-signed URL
  const { uploadUrl, jobId } = await response.json();
  
  // 3. Track upload progress
  const uploadResponse = await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    onUploadProgress: updateProgressBar
  });
  
  // 4. Start status polling
  pollJobStatus(jobId);
}
```

#### Status Polling (Simplified)
```javascript
function pollJobResults(jobId) {
  const interval = setInterval(async () => {
    try {
      const response = await fetch(`/api/results/${jobId}`);
      
      if (response.ok) {
        // Results are ready
        const results = await response.json();
        clearInterval(interval);
        displayResults(jobId, results);
      } else if (response.status === 404) {
        // Still processing, continue polling
        updateJobStatus(jobId, 'processing');
      } else {
        // Error occurred
        clearInterval(interval);
        updateJobStatus(jobId, 'failed');
      }
    } catch (error) {
      console.log('Polling...', error);
      // Continue polling on network errors
    }
  }, 10000); // Poll every 10 seconds
}
```

### Deployment Strategy

#### S3 Static Website Hosting
```bash
# Create and configure S3 bucket for static website
aws s3 mb s3://vehicle-analysis-ui-[account-id]
aws s3 website s3://vehicle-analysis-ui-[account-id] --index-document index.html

# Set bucket policy for public read access
aws s3api put-bucket-policy --bucket vehicle-analysis-ui-[account-id] --policy file://bucket-policy.json
```

**Bucket Policy (bucket-policy.json):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::vehicle-analysis-ui-[account-id]/*"
    }
  ]
}
```

**Access URL**: `http://vehicle-analysis-ui-[account-id].s3-website-[region].amazonaws.com`

### Security Considerations

#### CORS Configuration
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["http://bucket-name.s3-website-region.amazonaws.com"],
      "AllowedMethods": ["GET", "POST", "PUT"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

#### API Gateway CORS
```yaml
Cors:
  AllowMethods: "'GET,POST,OPTIONS'"
  AllowHeaders: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
  AllowOrigin: "'http://bucket-name.s3-website-region.amazonaws.com'"
```

### User Experience Features

#### Real-time Updates (Simplified)
- **Status Detection**: Web UI polls results endpoint every 10 seconds
- **Visual Indicators**: 
  - **Gray**: Uploaded, waiting to start
  - **Blue**: Processing (no results file found)
  - **Green**: Completed (results file exists)
  - **Red**: Failed (error file exists)
- **Auto-refresh**: Polls until results are available
- **Error Handling**: User-friendly error messages from error files

#### Results Visualization
- **Summary Cards**: Quick overview of vehicle counts
- **Interactive Timeline**: Click to see detections at specific times
- **Export Options**: One-click download of JSON/CSV reports
- **Mobile Responsive**: Works well on phones/tablets

### Development Workflow
```bash
# Local development
cd web-ui/
python -m http.server 8000  # Simple local server for testing

# Deployment to S3
aws s3 sync ./web-ui/ s3://vehicle-analysis-ui-[account-id]/

# Update bucket policy if needed
aws s3api put-bucket-policy --bucket vehicle-analysis-ui-[account-id] --policy file://bucket-policy.json
```

### Future Enhancements (Optional)

### Phase 2 Features (if needed later):
- **HTTPS Support**: Add CloudFront distribution for SSL/TLS
- **Custom Domain**: Route 53 + CloudFront for branded URL
- Video preview with detection overlays
- Historical analysis trends and charts
- Email reports with visual summaries
- Batch processing of multiple videos
- Support for live video streams

### Adding HTTPS Later (Optional)
If you later need HTTPS or custom domain:
```bash
# Create CloudFront distribution
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json

# Point custom domain via Route 53
aws route53 create-hosted-zone --name your-domain.com
```

## Prerequisites

### AWS Account Setup:
- Active AWS account with appropriate permissions
- AWS CLI configured (for deployment)
- Basic understanding of S3 bucket policies

### Technical Requirements:
- Supported video formats: MP4, MOV, AVI
- Maximum video length: 30 minutes (cost consideration)
- Maximum file size: 8GB (Lambda limitation)
- Modern web browser (Chrome, Firefox, Safari, Edge)
- **Note**: HTTP only (no HTTPS) - suitable for single user

### Development Requirements:
- Basic HTML/CSS/JavaScript knowledge (for UI customization)
- AWS CloudFormation familiarity (for deployment)
- Text editor or IDE for code modifications

## Next Steps

1. Review and approve this design
2. Create CloudFormation template
3. Implement Lambda functions
4. Deploy and test system
5. Create user documentation

---

*This design prioritizes simplicity, cost-effectiveness, and ease of use for a single-user scenario while leveraging AWS managed services to minimize operational overhead.*