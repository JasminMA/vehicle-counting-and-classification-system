# Results Processor Lambda Function

## Overview
The Results Processor Lambda function is the core component that processes AWS Rekognition video analysis results and converts them into meaningful vehicle counting reports. It's triggered by SNS notifications when Rekognition completes video analysis.

## Functionality

### Core Features
- **Rekognition Results Processing**: Retrieves and processes label detection results from AWS Rekognition
- **Vehicle Classification**: Classifies detected objects into vehicle categories (cars, trucks, motorcycles, buses, vans, emergency vehicles)
- **Vehicle Counting**: Estimates unique vehicle counts using spatial-temporal clustering
- **Report Generation**: Creates comprehensive analysis reports in JSON and CSV formats
- **Error Handling**: Robust error handling with detailed logging and error markers

### Vehicle Classification Categories
```python
VEHICLE_LABELS = {
    'cars': ['Car', 'Sedan', 'Coupe', 'Convertible', 'Hatchback', 'SUV', 'Crossover'],
    'trucks': ['Truck', 'Pickup Truck', 'Semi Truck', 'Delivery Truck', 'Dump Truck', 'Tow Truck'],
    'motorcycles': ['Motorcycle', 'Scooter', 'Moped', 'Motorbike'],
    'buses': ['Bus', 'School Bus', 'Coach', 'Double Decker'],
    'vans': ['Van', 'Minivan', 'Cargo Van'],
    'emergency_vehicles': ['Ambulance', 'Fire Truck', 'Police Car', 'Emergency Vehicle']
}
```

## Input/Output

### Input (SNS Event)
The function is triggered by SNS notifications from AWS Rekognition:
```json
{
  "Records": [
    {
      "Sns": {
        "Message": "{\"JobId\": \"rekognition-job-id\", \"Status\": \"SUCCEEDED\", \"JobTag\": \"job-12345\"}"
      }
    }
  ]
}
```

### Output Files (S3)
The function generates several output files in S3:

#### 1. Analysis Summary (`results/{job-id}/analysis.json`)
```json
{
  "video_info": {
    "filename": "traffic_video.mp4",
    "duration_seconds": 120.5,
    "frame_rate": 30,
    "format": "mp4",
    "processed_at": "2024-01-15T10:30:00Z",
    "analysis_id": "job-12345"
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
```

#### 2. Detailed Detections (`results/{job-id}/detections.csv`)
```csv
timestamp,vehicle_type,label_name,confidence,bbox_left,bbox_top,bbox_width,bbox_height
5.2,cars,Car,85.6,0.1234,0.3456,0.2345,0.1890
7.8,trucks,Truck,92.1,0.4567,0.2890,0.3456,0.2345
10.1,motorcycles,Motorcycle,78.9,0.7890,0.5678,0.1234,0.0987
```

#### 3. Completion Marker (`results/{job-id}/completed.json`)
```json
{
  "jobId": "job-12345",
  "status": "completed",
  "completedAt": "2024-01-15T10:30:00Z",
  "resultsFiles": {
    "summary": "results/job-12345/analysis.json",
    "detections": "results/job-12345/detections.csv"
  }
}
```

## Vehicle Counting Algorithm

### Unique Vehicle Estimation
The function uses a simplified spatial-temporal clustering algorithm to estimate unique vehicles:

1. **Temporal Windowing**: Groups detections within 2-second windows
2. **Spatial Clustering**: Considers detections within 10% frame distance as same vehicle
3. **Vehicle Tracking**: Updates vehicle positions over time
4. **Duplicate Removal**: Prevents counting same vehicle multiple times

### Algorithm Parameters
```python
TIME_WINDOW = 2.0      # 2 seconds
SPATIAL_THRESHOLD = 0.1 # 10% of frame
MIN_CONFIDENCE = 70.0   # Minimum confidence for detections
```

### Limitations
- **Simple Tracking**: Uses basic spatial-temporal clustering (not advanced tracking)
- **Occlusion Handling**: Limited handling of vehicles hidden behind others
- **Camera Movement**: Assumes stationary camera
- **Vehicle Size**: All vehicle types treated equally for distance calculations

## Configuration

### Environment Variables
- `STORAGE_BUCKET_NAME`: S3 bucket for storing results
- `ENVIRONMENT`: Deployment environment (dev/prod)

### Lambda Configuration
- **Runtime**: Python 3.9
- **Memory**: 512 MB
- **Timeout**: 10 minutes
- **Trigger**: SNS topic (Rekognition completion notifications)

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:GetLabelDetection",
        "rekognition:DescribeCollection"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
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

## Error Handling

### Error Types Handled
1. **SNS Message Parsing Errors**: Invalid JSON or missing fields
2. **Rekognition API Errors**: Failed job retrieval or API limits
3. **S3 Access Errors**: Bucket permissions or network issues
4. **Processing Errors**: Data format issues or algorithm failures

### Error Output
When errors occur, the function creates error markers in S3:
```json
{
  "jobId": "job-12345",
  "status": "failed",
  "error": "Failed to process Rekognition results: API rate limit exceeded",
  "timestamp": "2024-01-15T10:30:00Z",
  "stage": "results_processing"
}
```

## Performance Characteristics

### Processing Time
- **Small videos (1-5 minutes)**: 10-30 seconds
- **Medium videos (5-15 minutes)**: 30-90 seconds
- **Large videos (15-30 minutes)**: 90-300 seconds

### Memory Usage
- **Base memory**: ~100MB
- **Per minute of video**: ~10-20MB additional
- **Peak usage**: Usually < 400MB for 30-minute videos

### Scalability Considerations
- **Concurrent Processing**: Can handle multiple jobs simultaneously
- **Memory Scaling**: Auto-scales with video length and detection count
- **API Rate Limits**: Includes retry logic for Rekognition API limits

## Testing

### Unit Tests Coverage
- ✅ SNS event processing and validation
- ✅ Vehicle classification logic
- ✅ Counting algorithm accuracy
- ✅ S3 file operations
- ✅ Error handling scenarios
- ✅ Rekognition API integration

### Test Execution
```bash
# Run all tests
pytest lambda/tests/test_results_processor.py -v

# Run specific test class
pytest lambda/tests/test_results_processor.py::TestVehicleClassification -v

# Run with coverage
pytest lambda/tests/test_results_processor.py --cov=handler --cov-report=html
```

## Monitoring & Logging

### CloudWatch Metrics
- **Invocation Count**: Number of function executions
- **Duration**: Processing time per job
- **Error Rate**: Failed processing attempts
- **Memory Usage**: Peak memory consumption

### Custom Logging
The function logs detailed information for debugging:
```python
# Example log entries
INFO: Processing Rekognition job rekognition-123, status: SUCCEEDED, tag: job-abc123
INFO: Found 147 vehicle detections
INFO: Vehicle counts: {'cars': 45, 'trucks': 8, 'total': 53}
INFO: Saved results to S3: results/job-abc123
```

### Alerts & Notifications
Recommended CloudWatch alarms:
- **High Error Rate**: > 5% failed executions
- **Long Duration**: > 5 minutes processing time
- **Memory Issues**: > 90% memory utilization

## Optimization Opportunities

### Current Implementation
- Basic spatial-temporal clustering
- Simple confidence filtering
- CSV/JSON output formats

### Future Enhancements
1. **Advanced Tracking**: Implement Kalman filters or SORT algorithm
2. **Machine Learning**: Train custom vehicle detection models
3. **Real-time Processing**: Support for live video streams
4. **Enhanced Analytics**: Speed estimation, traffic flow analysis
5. **Multi-camera Support**: Track vehicles across multiple camera feeds

## Deployment

### Infrastructure Deployment
```bash
cd infrastructure
npm run build
cdk deploy --all -c environment=dev
```

### Manual Testing
```bash
# Test with sample SNS event
aws lambda invoke \
  --function-name VehicleAnalysis-ResultsProcessor-dev \
  --payload file://test-event.json \
  response.json
```

### Integration Testing
The function integrates with:
- **Video Processor Lambda**: Receives job completion notifications
- **Results API Lambda**: Results are consumed by API endpoints
- **Web UI**: Final results displayed to users

## Troubleshooting

### Common Issues

#### 1. "Failed to get Rekognition results"
**Cause**: Rekognition job not found or access denied
**Solution**: Check IAM permissions and job ID validity

#### 2. "No vehicle detections found"
**Cause**: Low confidence detections or no vehicles in video
**Solution**: Lower MIN_CONFIDENCE threshold or verify video content

#### 3. "S3 access denied"
**Cause**: Insufficient S3 permissions
**Solution**: Verify bucket policies and IAM role permissions

#### 4. "Function timeout"
**Cause**: Large video with many detections
**Solution**: Increase Lambda timeout or optimize processing

### Debug Mode
Enable detailed logging by setting environment variable:
```bash
LOG_LEVEL=DEBUG
```

## Cost Analysis

### Processing Costs
- **Lambda execution**: $0.0000166667 per GB-second
- **Rekognition API calls**: Included in video analysis cost
- **S3 storage**: $0.023 per GB per month
- **SNS notifications**: $0.50 per 1 million requests

### Example Monthly Costs (100 videos)
- Lambda processing: ~$2-5
- S3 storage: ~$1-2
- SNS notifications: <$1
- **Total**: ~$3-8/month

---

This Results Processor Lambda function provides the core vehicle counting intelligence for the system, converting raw Rekognition data into actionable insights with robust error handling and comprehensive reporting capabilities.
