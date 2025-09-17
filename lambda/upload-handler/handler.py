import json
import boto3
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Upload Handler Lambda Function
    
    Generates pre-signed S3 URLs for secure video uploads and creates job tracking.
    
    Expected input:
    {
        "body": "{\"filename\": \"video.mp4\", \"filesize\": 125000000}"
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": "{\"jobId\": \"job-abc123\", \"uploadUrl\": \"https://s3...\", \"expiresIn\": 3600}"
    }
    """
    
    try:
        logger.info(f"Upload request received: {event}")
        
        # Parse the request body
        if 'body' not in event:
            return create_error_response(400, "Missing request body")
        
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            return create_error_response(400, "Invalid JSON in request body")
        
        # Validate required fields
        if 'filename' not in body:
            return create_error_response(400, "Missing 'filename' in request")
        
        if 'filesize' not in body:
            return create_error_response(400, "Missing 'filesize' in request")
        
        filename = body['filename']
        filesize = body['filesize']
        
        # Validate file parameters
        validation_error = validate_file_parameters(filename, filesize)
        if validation_error:
            return validation_error
        
        # Generate unique job ID
        job_id = generate_job_id()
        
        # Get bucket name from environment variable
        bucket_name = os.environ.get('STORAGE_BUCKET_NAME')
        if not bucket_name:
            logger.error("STORAGE_BUCKET_NAME environment variable not set")
            return create_error_response(500, "Configuration error")
        
        # Create S3 key for the upload
        s3_key = f"uploads/{job_id}/{filename}"
        
        # Generate pre-signed URL for upload
        upload_url = generate_presigned_upload_url(
            bucket_name=bucket_name,
            s3_key=s3_key,
            expiration=3600  # 1 hour
        )
        
        if not upload_url:
            return create_error_response(500, "Failed to generate upload URL")
        
        # Create job metadata
        job_metadata = {
            'jobId': job_id,
            'filename': filename,
            'filesize': filesize,
            'uploadTime': datetime.utcnow().isoformat(),
            'status': 'pending',
            's3Key': s3_key,
            'bucketName': bucket_name
        }
        
        # Store job metadata in S3 for tracking
        metadata_key = f"jobs/{job_id}/metadata.json"
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=metadata_key,
                Body=json.dumps(job_metadata),
                ContentType='application/json'
            )
        except Exception as e:
            logger.error(f"Failed to store job metadata: {str(e)}")
            # Don't fail the request for metadata storage issues
        
        # Prepare successful response
        response_body = {
            'jobId': job_id,
            'uploadUrl': upload_url,
            'expiresIn': 3600,
            'maxFileSize': get_max_file_size(),
            'allowedFormats': get_allowed_formats()
        }
        
        logger.info(f"Generated upload URL for job {job_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in upload handler: {str(e)}")
        return create_error_response(500, "Internal server error")


def generate_job_id() -> str:
    """Generate a unique job ID"""
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    return f"job-{timestamp}-{unique_id}"


def validate_file_parameters(filename: str, filesize: int) -> Dict[str, Any]:
    """
    Validate file parameters
    
    Returns error response dict if validation fails, None if valid
    """
    
    # Check filename
    if not filename or len(filename.strip()) == 0:
        return create_error_response(400, "Filename cannot be empty")
    
    if len(filename) > 255:
        return create_error_response(400, "Filename too long (max 255 characters)")
    
    # Check file extension
    allowed_extensions = get_allowed_formats()
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if file_extension not in allowed_extensions:
        return create_error_response(
            400, 
            f"Unsupported file format. Allowed formats: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    max_size = get_max_file_size()
    if filesize > max_size:
        max_size_mb = max_size // (1024 * 1024)
        return create_error_response(
            400, 
            f"File too large. Maximum size: {max_size_mb}MB"
        )
    
    if filesize <= 0:
        return create_error_response(400, "Invalid file size")
    
    return None


def get_allowed_formats() -> list:
    """Get list of allowed video file formats"""
    return ['mp4', 'mov', 'avi', 'mkv', 'webm']


def get_max_file_size() -> int:
    """Get maximum file size in bytes (8GB)"""
    return 8 * 1024 * 1024 * 1024  # 8GB


def generate_presigned_upload_url(bucket_name: str, s3_key: str, expiration: int) -> str:
    """
    Generate a pre-signed URL for S3 upload
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key
        expiration: URL expiration time in seconds
        
    Returns:
        Pre-signed URL string or None if generation fails
    """
    try:
        response = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': 'video/*'
            },
            ExpiresIn=expiration
        )
        return response
    except Exception as e:
        logger.error(f"Failed to generate pre-signed URL: {str(e)}")
        return None


def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create a standardized error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat()
        })
    }
