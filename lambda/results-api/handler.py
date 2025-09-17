import json
import boto3
import os
import urllib.parse
from typing import Dict, Any, Optional
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lazy initialization of AWS clients
_s3_client = None

def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client

# For backward compatibility in tests
s3_client = property(get_s3_client)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Results API Lambda Function
    
    REST API endpoint that returns job status and analysis results.
    Supports multiple endpoints:
    - GET /results/{jobId} - Get analysis results for a specific job ID
    - GET /results/{jobId}/status - Get job status only
    - GET /results/{jobId}/download/{format} - Download results in specific format
    
    Expected API Gateway event structure:
    {
        "httpMethod": "GET",
        "pathParameters": {"jobId": "job-12345"},
        "queryStringParameters": {"format": "json"},
        "requestContext": {...}
    }
    """
    
    try:
        logger.info(f"Results API called with event: {json.dumps(event, default=str)}")
        
        # Extract HTTP method and path
        http_method = event.get('httpMethod', 'GET')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        resource_path = event.get('resource', '')
        
        # Validate HTTP method
        if http_method != 'GET':
            return create_error_response(405, "Method not allowed")
        
        # Extract job ID from path parameters
        job_id = path_parameters.get('jobId')
        if not job_id:
            return create_error_response(400, "Missing jobId in path parameters")
        
        # Validate job ID format
        if not is_valid_job_id(job_id):
            return create_error_response(400, "Invalid jobId format")
        
        # Get bucket name from environment
        bucket_name = os.environ.get('STORAGE_BUCKET_NAME')
        if not bucket_name:
            logger.error("STORAGE_BUCKET_NAME environment variable not set")
            return create_error_response(500, "Configuration error")
        
        # Route to appropriate handler based on resource path
        if '/download/' in resource_path:
            # Download endpoint: /results/{jobId}/download/{format}
            download_format = path_parameters.get('format', 'json')
            return handle_download_request(bucket_name, job_id, download_format)
        
        elif resource_path.endswith('/status'):
            # Status endpoint: /results/{jobId}/status
            return handle_status_request(bucket_name, job_id)
        
        else:
            # Main results endpoint: /results/{jobId}
            include_details = query_parameters.get('details', 'true').lower() == 'true'
            return handle_results_request(bucket_name, job_id, include_details)
    
    except Exception as e:
        logger.error(f"Unexpected error in results API: {str(e)}")
        return create_error_response(500, "Internal server error")


def handle_results_request(bucket_name: str, job_id: str, include_details: bool = True) -> Dict[str, Any]:
    """
    Handle main results request - returns complete analysis results
    
    Args:
        bucket_name: S3 bucket name
        job_id: Job identifier
        include_details: Whether to include detailed detection data
        
    Returns:
        API Gateway response with results or status
    """
    try:
        # Check job status first
        job_status = get_job_status(bucket_name, job_id)
        
        if job_status['status'] == 'completed':
            # Job completed - return results
            results = get_analysis_results(bucket_name, job_id)
            if results:
                response_data = {
                    'jobId': job_id,
                    'status': 'completed',
                    'results': results
                }
                
                # Optionally include detailed timeline
                if not include_details and 'timeline' in results:
                    # Check if timeline will be truncated
                    original_timeline_length = len(results['timeline'])
                    results['timeline_truncated'] = original_timeline_length > 10
                    # Limit timeline to first 10 entries for summary
                    results['timeline'] = results['timeline'][:10]
                
                return create_success_response(response_data)
            else:
                logger.error(f"Could not retrieve results for completed job {job_id}")
                return create_error_response(500, "Results not available")
        
        elif job_status['status'] == 'failed':
            # Job failed - return error details
            return create_success_response({
                'jobId': job_id,
                'status': 'failed',
                'error': job_status.get('error', 'Processing failed'),
                'timestamp': job_status.get('timestamp')
            })
        
        elif job_status['status'] == 'processing':
            # Job still processing - return status
            return create_success_response({
                'jobId': job_id,
                'status': 'processing',
                'message': 'Video analysis in progress',
                'stage': job_status.get('stage', 'unknown')
            })
        
        else:
            # Job not found or unknown status
            return create_error_response(404, "Job not found")
    
    except Exception as e:
        logger.error(f"Error handling results request for job {job_id}: {str(e)}")
        return create_error_response(500, "Failed to retrieve results")


def handle_status_request(bucket_name: str, job_id: str) -> Dict[str, Any]:
    """
    Handle status-only request - returns just job status without full results
    
    Args:
        bucket_name: S3 bucket name
        job_id: Job identifier
        
    Returns:
        API Gateway response with job status
    """
    try:
        job_status = get_job_status(bucket_name, job_id)
        
        response_data = {
            'jobId': job_id,
            'status': job_status['status']
        }
        
        # Add additional fields based on status
        if job_status['status'] == 'completed':
            response_data['completedAt'] = job_status.get('timestamp')
            response_data['message'] = 'Analysis completed successfully'
        elif job_status['status'] == 'failed':
            response_data['error'] = job_status.get('error', 'Processing failed')
            response_data['failedAt'] = job_status.get('timestamp')
        elif job_status['status'] == 'processing':
            response_data['stage'] = job_status.get('stage', 'unknown')
            response_data['startedAt'] = job_status.get('startTime')
        
        return create_success_response(response_data)
    
    except Exception as e:
        logger.error(f"Error handling status request for job {job_id}: {str(e)}")
        return create_error_response(500, "Failed to retrieve job status")


def handle_download_request(bucket_name: str, job_id: str, download_format: str) -> Dict[str, Any]:
    """
    Handle download request - returns results file for download
    
    Args:
        bucket_name: S3 bucket name
        job_id: Job identifier
        download_format: Requested format (json, csv)
        
    Returns:
        API Gateway response with file content or pre-signed URL
    """
    try:
        # Validate format
        if download_format not in ['json', 'csv']:
            return create_error_response(400, "Invalid format. Supported formats: json, csv")
        
        # Check if job is completed
        job_status = get_job_status(bucket_name, job_id)
        if job_status['status'] != 'completed':
            return create_error_response(404, "Results not available for download")
        
        # Determine S3 key based on format
        if download_format == 'json':
            s3_key = f"results/{job_id}/analysis.json"
            content_type = 'application/json'
            filename = f"vehicle_analysis_{job_id}.json"
        else:  # csv
            s3_key = f"results/{job_id}/detections.csv"
            content_type = 'text/csv'
            filename = f"vehicle_detections_{job_id}.csv"
        
        # Check if file exists
        if not s3_object_exists(bucket_name, s3_key):
            return create_error_response(404, f"Results file not found: {download_format}")
        
        # Generate pre-signed URL for download
        download_url = generate_download_url(bucket_name, s3_key, filename, content_type)
        
        if download_url:
            return create_success_response({
                'jobId': job_id,
                'format': download_format,
                'downloadUrl': download_url,
                'filename': filename,
                'expiresIn': 3600  # 1 hour
            })
        else:
            return create_error_response(500, "Failed to generate download URL")
    
    except Exception as e:
        logger.error(f"Error handling download request for job {job_id}: {str(e)}")
        return create_error_response(500, "Failed to generate download")


def get_job_status(bucket_name: str, job_id: str) -> Dict[str, Any]:
    """
    Determine job status by checking S3 file existence
    
    Args:
        bucket_name: S3 bucket name
        job_id: Job identifier
        
    Returns:
        Dictionary with status information
    """
    try:
        # Check for completion marker
        completed_key = f"results/{job_id}/completed.json"
        if s3_object_exists(bucket_name, completed_key):
            # Get completion details
            try:
                s3_client = get_s3_client()
                response = s3_client.get_object(Bucket=bucket_name, Key=completed_key)
                completion_data = json.loads(response['Body'].read().decode('utf-8'))
                return {
                    'status': 'completed',
                    'timestamp': completion_data.get('completedAt'),
                    'files': completion_data.get('resultsFiles', {})
                }
            except Exception:
                return {'status': 'completed', 'timestamp': None}
        
        # Check for error marker
        error_key = f"errors/{job_id}/error.json"
        if s3_object_exists(bucket_name, error_key):
            # Get error details
            try:
                s3_client = get_s3_client()
                response = s3_client.get_object(Bucket=bucket_name, Key=error_key)
                error_data = json.loads(response['Body'].read().decode('utf-8'))
                return {
                    'status': 'failed',
                    'error': error_data.get('error', 'Processing failed'),
                    'timestamp': error_data.get('timestamp'),
                    'stage': error_data.get('stage')
                }
            except Exception:
                return {'status': 'failed', 'error': 'Processing failed'}
        
        # Check for processing marker
        processing_key = f"processing/{job_id}.processing"
        if s3_object_exists(bucket_name, processing_key):
            # Get processing details
            try:
                s3_client = get_s3_client()
                response = s3_client.get_object(Bucket=bucket_name, Key=processing_key)
                processing_data = json.loads(response['Body'].read().decode('utf-8'))
                return {
                    'status': 'processing',
                    'stage': processing_data.get('stage', 'analysis'),
                    'startTime': processing_data.get('startTime')
                }
            except Exception:
                return {'status': 'processing', 'stage': 'analysis'}
        
        # Check if upload exists (job created but not started)
        upload_prefix = f"uploads/{job_id}/"
        try:
            s3_client = get_s3_client()
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=upload_prefix,
                MaxKeys=1
            )
            if response.get('Contents'):
                return {'status': 'pending', 'message': 'Waiting to start processing'}
        except Exception:
            pass
        
        # Job not found
        return {'status': 'not_found'}
    
    except Exception as e:
        logger.error(f"Error checking job status for {job_id}: {str(e)}")
        return {'status': 'unknown', 'error': str(e)}


def get_analysis_results(bucket_name: str, job_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve analysis results from S3
    
    Args:
        bucket_name: S3 bucket name
        job_id: Job identifier
        
    Returns:
        Analysis results dictionary or None if not found
    """
    try:
        s3_client = get_s3_client()
        results_key = f"results/{job_id}/analysis.json"
        response = s3_client.get_object(Bucket=bucket_name, Key=results_key)
        results = json.loads(response['Body'].read().decode('utf-8'))
        
        logger.info(f"Successfully retrieved results for job {job_id}")
        return results
    
    except s3_client.exceptions.NoSuchKey:
        logger.warning(f"Results file not found for job {job_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving results for job {job_id}: {str(e)}")
        return None


def s3_object_exists(bucket_name: str, key: str) -> bool:
    """Check if S3 object exists"""
    try:
        s3_client = get_s3_client()
        s3_client.head_object(Bucket=bucket_name, Key=key)
        return True
    except s3_client.exceptions.NoSuchKey:
        return False
    except Exception as e:
        logger.warning(f"Error checking S3 object existence: {str(e)}")
        return False


def generate_download_url(bucket_name: str, s3_key: str, filename: str, content_type: str) -> Optional[str]:
    """
    Generate pre-signed URL for file download
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key
        filename: Suggested filename for download
        content_type: MIME content type
        
    Returns:
        Pre-signed URL string or None if generation fails
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ResponseContentDisposition': f'attachment; filename="{filename}"',
                'ResponseContentType': content_type
            },
            ExpiresIn=3600  # 1 hour
        )
        return response
    except Exception as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        return None


def is_valid_job_id(job_id: str) -> bool:
    """
    Validate job ID format
    
    Args:
        job_id: Job identifier to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not job_id or not isinstance(job_id, str):
        return False
    
    # Basic validation: should start with 'job-' and be reasonable length
    if not job_id.startswith('job-'):
        return False
    
    if len(job_id) < 10 or len(job_id) > 100:
        return False
    
    # Check for basic safety (no path traversal attempts)
    if '..' in job_id or '/' in job_id or '\\' in job_id:
        return False
    
    return True


def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a successful API Gateway response"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
            'Cache-Control': 'no-cache'
        },
        'body': json.dumps(data, default=str)
    }


def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create an error API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat()
        })
    }
