import json
import boto3
import os
import urllib.parse
from typing import Dict, Any
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lazy initialization of AWS clients
_rekognition = None
_s3_client = None
_sns_client = None

def get_rekognition_client():
    global _rekognition
    if _rekognition is None:
        _rekognition = boto3.client('rekognition')
    return _rekognition

def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client

def get_sns_client():
    global _sns_client
    if _sns_client is None:
        _sns_client = boto3.client('sns')
    return _sns_client

# For backward compatibility in tests
rekognition = property(get_rekognition_client)
s3_client = property(get_s3_client)
sns_client = property(get_sns_client)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Video Processor Lambda Function
    
    Triggered by S3 events when videos are uploaded.
    Starts AWS Rekognition video analysis and creates processing markers.
    
    Expected S3 event structure:
    {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "bucket-name"},
                    "object": {"key": "uploads/job-id/video.mp4"}
                }
            }
        ]
    }
    """
    
    try:
        logger.info(f"Video processor triggered with event: {json.dumps(event)}")
        
        # Process each S3 record
        for record in event.get('Records', []):
            if not is_valid_s3_record(record):
                logger.warning(f"Skipping invalid S3 record: {record}")
                continue
            
            # Extract S3 details
            bucket_name = record['s3']['bucket']['name']
            s3_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processing video: s3://{bucket_name}/{s3_key}")
            
            # Extract job ID from S3 key
            job_id = extract_job_id_from_key(s3_key)
            if not job_id:
                logger.error(f"Could not extract job ID from S3 key: {s3_key}")
                continue
            
            # Validate video file
            if not is_supported_video_file(s3_key):
                logger.error(f"Unsupported video file format: {s3_key}")
                create_error_marker(bucket_name, job_id, "Unsupported video format")
                continue
            
            # Check if video exists and get metadata
            video_metadata = get_video_metadata(bucket_name, s3_key)
            if not video_metadata:
                logger.error(f"Could not access video file: {s3_key}")
                create_error_marker(bucket_name, job_id, "Could not access video file")
                continue
            
            # Create processing marker
            create_processing_marker(bucket_name, job_id, video_metadata)
            
            # Start Rekognition video analysis
            rekognition_job_id = start_rekognition_analysis(
                bucket_name=bucket_name,
                s3_key=s3_key,
                job_id=job_id
            )
            
            if rekognition_job_id:
                logger.info(f"Successfully started Rekognition job {rekognition_job_id} for {job_id}")
                update_processing_marker(bucket_name, job_id, rekognition_job_id)
            else:
                logger.error(f"Failed to start Rekognition analysis for {job_id}")
                create_error_marker(bucket_name, job_id, "Failed to start video analysis")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(event.get("Records", []))} video(s)',
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in video processor: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'timestamp': datetime.utcnow().isoformat()
            })
        }


def is_valid_s3_record(record: Dict[str, Any]) -> bool:
    """Validate S3 event record structure"""
    try:
        return (
            's3' in record and
            'bucket' in record['s3'] and
            'name' in record['s3']['bucket'] and
            'object' in record['s3'] and
            'key' in record['s3']['object']
        )
    except (KeyError, TypeError):
        return False


def extract_job_id_from_key(s3_key: str) -> str:
    """
    Extract job ID from S3 key pattern: uploads/{job-id}/{filename}
    
    Args:
        s3_key: S3 object key
        
    Returns:
        Job ID string or None if pattern doesn't match
    """
    try:
        parts = s3_key.split('/')
        if len(parts) >= 3 and parts[0] == 'uploads':
            return parts[1]  # job-id
        return None
    except Exception:
        return None


def is_supported_video_file(s3_key: str) -> bool:
    """Check if the file is a supported video format"""
    supported_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    return any(s3_key.lower().endswith(ext) for ext in supported_extensions)


def get_video_metadata(bucket_name: str, s3_key: str) -> Dict[str, Any]:
    """
    Get video file metadata from S3
    
    Returns:
        Dictionary with video metadata or None if error
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        return {
            'size': response.get('ContentLength', 0),
            'lastModified': response.get('LastModified', '').isoformat() if response.get('LastModified') else '',
            'contentType': response.get('ContentType', ''),
            'etag': response.get('ETag', '').strip('"')
        }
    except Exception as e:
        logger.error(f"Failed to get video metadata: {str(e)}")
        return None


def create_processing_marker(bucket_name: str, job_id: str, video_metadata: Dict[str, Any]) -> bool:
    """
    Create a processing marker file in S3
    
    Args:
        bucket_name: S3 bucket name
        job_id: Job identifier
        video_metadata: Video file metadata
        
    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client = get_s3_client()
        marker_key = f"processing/{job_id}.processing"
        marker_data = {
            'jobId': job_id,
            'status': 'processing',
            'startTime': datetime.utcnow().isoformat(),
            'videoMetadata': video_metadata,
            'stage': 'rekognition_started'
        }
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=marker_key,
            Body=json.dumps(marker_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Created processing marker for job {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create processing marker: {str(e)}")
        return False


def update_processing_marker(bucket_name: str, job_id: str, rekognition_job_id: str) -> bool:
    """Update processing marker with Rekognition job ID"""
    try:
        s3_client = get_s3_client()
        marker_key = f"processing/{job_id}.processing"
        
        # Get existing marker
        response = s3_client.get_object(Bucket=bucket_name, Key=marker_key)
        marker_data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Update with Rekognition job ID
        marker_data['rekognitionJobId'] = rekognition_job_id
        marker_data['stage'] = 'rekognition_running'
        marker_data['lastUpdated'] = datetime.utcnow().isoformat()
        
        # Save updated marker
        s3_client.put_object(
            Bucket=bucket_name,
            Key=marker_key,
            Body=json.dumps(marker_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Updated processing marker for job {job_id} with Rekognition job {rekognition_job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update processing marker: {str(e)}")
        return False


def create_error_marker(bucket_name: str, job_id: str, error_message: str) -> bool:
    """Create an error marker file in S3"""
    try:
        s3_client = get_s3_client()
        error_key = f"errors/{job_id}/error.json"
        error_data = {
            'jobId': job_id,
            'status': 'failed',
            'error': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'stage': 'video_processing'
        }
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=error_key,
            Body=json.dumps(error_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Created error marker for job {job_id}: {error_message}")
        return True
    except Exception as e:
        logger.error(f"Failed to create error marker: {str(e)}")
        return False


def start_rekognition_analysis(bucket_name: str, s3_key: str, job_id: str) -> str:
    """
    Start AWS Rekognition video label detection
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key for the video
        job_id: Job identifier for tracking
        
    Returns:
        Rekognition job ID if successful, None otherwise
    """
    try:
        rekognition = get_rekognition_client()
        
        # Get SNS topic ARN and service role ARN from environment
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        rekognition_role_arn = os.environ.get('REKOGNITION_ROLE_ARN')
        
        if not sns_topic_arn or not rekognition_role_arn:
            logger.error("Missing required environment variables: SNS_TOPIC_ARN or REKOGNITION_ROLE_ARN")
            return None
        
        # Start label detection
        response = rekognition.start_label_detection(
            Video={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': s3_key
                }
            },
            NotificationChannel={
                'SNSTopicArn': sns_topic_arn,
                'RoleArn': rekognition_role_arn
            },
            JobTag=job_id,  # Use job ID as tag for easy tracking
            MinConfidence=70.0,  # Minimum confidence for detections
            Features=['GENERAL_LABELS']  # Focus on general object detection
        )
        
        rekognition_job_id = response.get('JobId')
        logger.info(f"Started Rekognition job {rekognition_job_id} for video {s3_key}")
        
        return rekognition_job_id
        
    except Exception as e:
        logger.error(f"Failed to start Rekognition analysis: {str(e)}")
        return None
