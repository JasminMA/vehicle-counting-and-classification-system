import json
import boto3
import os
import urllib.parse
from typing import Dict, Any, List, Set
import logging
from datetime import datetime
from collections import defaultdict, Counter
import csv
import io

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
rekognition = boto3.client('rekognition')
s3_client = boto3.client('s3')

# Vehicle classification mapping
VEHICLE_LABELS = {
    'cars': ['Car', 'Sedan', 'Coupe', 'Convertible', 'Hatchback', 'SUV', 'Crossover'],
    'trucks': ['Truck', 'Pickup Truck', 'Semi Truck', 'Delivery Truck', 'Dump Truck', 'Tow Truck'],
    'motorcycles': ['Motorcycle', 'Scooter', 'Moped', 'Motorbike'],
    'buses': ['Bus', 'School Bus', 'Coach', 'Double Decker'],
    'vans': ['Van', 'Minivan', 'Cargo Van'],
    'emergency_vehicles': ['Ambulance', 'Fire Truck', 'Police Car', 'Emergency Vehicle']
}

# Minimum confidence threshold for detections
MIN_CONFIDENCE = 70.0

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Results Processor Lambda Function
    
    Triggered by SNS when Rekognition video analysis completes.
    Processes the results and generates vehicle counting reports.
    
    Expected SNS event structure:
    {
        "Records": [
            {
                "Sns": {
                    "Message": "{\"JobId\": \"rekognition-job-id\", \"Status\": \"SUCCEEDED\", \"JobTag\": \"job-12345\"}"
                }
            }
        ]
    }
    """
    
    try:
        logger.info(f"Results processor triggered with event: {json.dumps(event)}")
        
        # Process each SNS record
        for record in event.get('Records', []):
            if not is_valid_sns_record(record):
                logger.warning(f"Skipping invalid SNS record: {record}")
                continue
            
            # Parse SNS message
            sns_message = json.loads(record['Sns']['Message'])
            rekognition_job_id = sns_message.get('JobId')
            job_status = sns_message.get('Status')
            job_tag = sns_message.get('JobTag')  # This is our internal job ID
            
            logger.info(f"Processing Rekognition job {rekognition_job_id}, status: {job_status}, tag: {job_tag}")
            
            if not rekognition_job_id or not job_tag:
                logger.error(f"Missing required fields in SNS message: {sns_message}")
                continue
            
            # Get bucket name from environment
            bucket_name = os.environ.get('STORAGE_BUCKET_NAME')
            if not bucket_name:
                logger.error("STORAGE_BUCKET_NAME environment variable not set")
                continue
            
            if job_status == 'SUCCEEDED':
                # Process successful job
                success = process_successful_job(
                    rekognition_job_id=rekognition_job_id,
                    job_id=job_tag,
                    bucket_name=bucket_name
                )
                
                if success:
                    logger.info(f"Successfully processed job {job_tag}")
                else:
                    logger.error(f"Failed to process job {job_tag}")
                    create_error_result(bucket_name, job_tag, "Failed to process Rekognition results")
                    
            elif job_status == 'FAILED':
                # Handle failed Rekognition job
                error_message = sns_message.get('StatusMessage', 'Rekognition job failed')
                logger.error(f"Rekognition job {rekognition_job_id} failed: {error_message}")
                create_error_result(bucket_name, job_tag, f"Video analysis failed: {error_message}")
            
            else:
                logger.warning(f"Unknown job status: {job_status}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(event.get("Records", []))} result(s)',
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in results processor: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'timestamp': datetime.utcnow().isoformat()
            })
        }


def is_valid_sns_record(record: Dict[str, Any]) -> bool:
    """Validate SNS event record structure"""
    try:
        return (
            'Sns' in record and
            'Message' in record['Sns']
        )
    except (KeyError, TypeError):
        return False


def process_successful_job(rekognition_job_id: str, job_id: str, bucket_name: str) -> bool:
    """
    Process a successful Rekognition job and generate vehicle counting results
    
    Args:
        rekognition_job_id: Rekognition job identifier
        job_id: Internal job identifier
        bucket_name: S3 bucket name
        
    Returns:
        True if processing successful, False otherwise
    """
    try:
        # Get Rekognition results
        rekognition_results = get_rekognition_results(rekognition_job_id)
        if not rekognition_results:
            logger.error(f"Failed to get Rekognition results for job {rekognition_job_id}")
            return False
        
        # Get job metadata for context
        job_metadata = get_job_metadata(bucket_name, job_id)
        if not job_metadata:
            logger.warning(f"Could not get job metadata for {job_id}, proceeding with defaults")
            job_metadata = {'filename': 'unknown.mp4'}
        
        # Process the labels and detect vehicles
        vehicle_detections = process_vehicle_labels(rekognition_results)
        
        # Generate analysis results
        analysis_results = generate_analysis_results(
            job_id=job_id,
            job_metadata=job_metadata,
            vehicle_detections=vehicle_detections,
            rekognition_results=rekognition_results
        )
        
        # Save results to S3
        success = save_results_to_s3(bucket_name, job_id, analysis_results, vehicle_detections)
        
        if success:
            # Clean up processing marker
            cleanup_processing_marker(bucket_name, job_id)
            logger.info(f"Successfully processed and saved results for job {job_id}")
            return True
        else:
            logger.error(f"Failed to save results for job {job_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing successful job {job_id}: {str(e)}")
        return False


def get_rekognition_results(job_id: str) -> Dict[str, Any]:
    """
    Retrieve complete Rekognition label detection results
    
    Args:
        job_id: Rekognition job identifier
        
    Returns:
        Complete results dictionary or None if error
    """
    try:
        all_labels = []
        next_token = None
        
        while True:
            # Build request parameters
            params = {'JobId': job_id}
            if next_token:
                params['NextToken'] = next_token
            
            # Get results page
            response = rekognition.get_label_detection(**params)
            
            # Check job status
            if response['JobStatus'] != 'SUCCEEDED':
                logger.error(f"Rekognition job {job_id} not successful: {response['JobStatus']}")
                return None
            
            # Collect labels from this page
            labels = response.get('Labels', [])
            all_labels.extend(labels)
            
            # Check for more pages
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        # Get video metadata
        video_metadata = response.get('VideoMetadata', {})
        
        return {
            'Labels': all_labels,
            'VideoMetadata': video_metadata,
            'JobStatus': response['JobStatus']
        }
        
    except Exception as e:
        logger.error(f"Failed to get Rekognition results: {str(e)}")
        return None


def get_job_metadata(bucket_name: str, job_id: str) -> Dict[str, Any]:
    """Get job metadata from S3"""
    try:
        metadata_key = f"jobs/{job_id}/metadata.json"
        response = s3_client.get_object(Bucket=bucket_name, Key=metadata_key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        logger.warning(f"Could not get job metadata: {str(e)}")
        return None


def process_vehicle_labels(rekognition_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process Rekognition labels and extract vehicle detections
    
    Args:
        rekognition_results: Complete Rekognition results
        
    Returns:
        List of vehicle detection dictionaries
    """
    vehicle_detections = []
    labels = rekognition_results.get('Labels', [])
    
    for label_detection in labels:
        timestamp = label_detection.get('Timestamp', 0) / 1000.0  # Convert to seconds
        label = label_detection.get('Label', {})
        
        label_name = label.get('Name', '')
        confidence = label.get('Confidence', 0)
        
        # Skip low confidence detections
        if confidence < MIN_CONFIDENCE:
            continue
        
        # Check if this label represents a vehicle
        vehicle_type = classify_vehicle_label(label_name)
        if not vehicle_type:
            continue
        
        # Process instances (individual detections)
        instances = label.get('Instances', [])
        for instance in instances:
            instance_confidence = instance.get('Confidence', confidence)
            
            # Skip low confidence instances
            if instance_confidence < MIN_CONFIDENCE:
                continue
            
            # Extract bounding box
            bbox = instance.get('BoundingBox', {})
            
            detection = {
                'timestamp': timestamp,
                'vehicle_type': vehicle_type,
                'label_name': label_name,
                'confidence': round(instance_confidence, 2),
                'bounding_box': {
                    'left': round(bbox.get('Left', 0), 4),
                    'top': round(bbox.get('Top', 0), 4),
                    'width': round(bbox.get('Width', 0), 4),
                    'height': round(bbox.get('Height', 0), 4)
                }
            }
            
            vehicle_detections.append(detection)
    
    # Sort by timestamp
    vehicle_detections.sort(key=lambda x: x['timestamp'])
    
    logger.info(f"Found {len(vehicle_detections)} vehicle detections")
    return vehicle_detections


def classify_vehicle_label(label_name: str) -> str:
    """
    Classify a Rekognition label as a vehicle type
    
    Args:
        label_name: Rekognition label name
        
    Returns:
        Vehicle type category or None if not a vehicle
    """
    for vehicle_type, labels in VEHICLE_LABELS.items():
        if label_name in labels:
            return vehicle_type
    return None


def generate_analysis_results(
    job_id: str,
    job_metadata: Dict[str, Any],
    vehicle_detections: List[Dict[str, Any]],
    rekognition_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate comprehensive analysis results
    
    Args:
        job_id: Job identifier
        job_metadata: Job metadata from S3
        vehicle_detections: Processed vehicle detections
        rekognition_results: Raw Rekognition results
        
    Returns:
        Complete analysis results dictionary
    """
    video_metadata = rekognition_results.get('VideoMetadata', {})
    
    # Count vehicles by type
    vehicle_counts = count_vehicles_by_type(vehicle_detections)
    
    # Generate timeline
    timeline = generate_detection_timeline(vehicle_detections)
    
    # Calculate statistics
    processing_stats = calculate_processing_stats(video_metadata, vehicle_detections, rekognition_results)
    
    # Create final results
    results = {
        'video_info': {
            'filename': job_metadata.get('filename', 'unknown.mp4'),
            'duration_seconds': round(video_metadata.get('DurationMillis', 0) / 1000.0, 2),
            'frame_rate': video_metadata.get('FrameRate', 0),
            'format': video_metadata.get('Format', 'unknown'),
            'processed_at': datetime.utcnow().isoformat(),
            'analysis_id': job_id
        },
        'vehicle_counts': vehicle_counts,
        'timeline': timeline[:100],  # Limit timeline entries for performance
        'processing_stats': processing_stats,
        'confidence_threshold': MIN_CONFIDENCE,
        'total_detections': len(vehicle_detections)
    }
    
    return results


def count_vehicles_by_type(vehicle_detections: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count unique vehicles by type using spatial and temporal clustering
    
    Args:
        vehicle_detections: List of vehicle detections
        
    Returns:
        Dictionary with vehicle counts by type
    """
    # Simple counting approach - can be enhanced with tracking algorithms
    vehicle_counts = defaultdict(int)
    
    # Group detections by vehicle type and timestamp windows
    type_groups = defaultdict(list)
    for detection in vehicle_detections:
        vehicle_type = detection['vehicle_type']
        type_groups[vehicle_type].append(detection)
    
    # Count unique vehicles per type using spatial clustering
    for vehicle_type, detections in type_groups.items():
        unique_count = estimate_unique_vehicles(detections)
        vehicle_counts[vehicle_type] = unique_count
    
    # Calculate total
    total_vehicles = sum(vehicle_counts.values())
    vehicle_counts['total_vehicles'] = total_vehicles
    
    return dict(vehicle_counts)


def estimate_unique_vehicles(detections: List[Dict[str, Any]]) -> int:
    """
    Estimate unique vehicle count using simple spatial-temporal clustering
    
    This is a simplified approach. In production, you might want to use
    more sophisticated tracking algorithms.
    
    Args:
        detections: List of detections for a specific vehicle type
        
    Returns:
        Estimated count of unique vehicles
    """
    if not detections:
        return 0
    
    # Simple approach: count distinct time windows with detections
    # Assumes vehicles appear for multiple consecutive frames
    
    TIME_WINDOW = 2.0  # 2 seconds
    SPATIAL_THRESHOLD = 0.1  # 10% of frame
    
    unique_vehicles = []
    
    for detection in detections:
        timestamp = detection['timestamp']
        bbox = detection['bounding_box']
        
        # Check if this detection matches an existing vehicle
        matched = False
        for vehicle in unique_vehicles:
            # Check temporal proximity
            time_diff = abs(timestamp - vehicle['last_seen'])
            
            # Check spatial proximity
            spatial_distance = calculate_bbox_distance(bbox, vehicle['bbox'])
            
            if time_diff <= TIME_WINDOW and spatial_distance <= SPATIAL_THRESHOLD:
                # Update existing vehicle
                vehicle['last_seen'] = max(vehicle['last_seen'], timestamp)
                vehicle['bbox'] = bbox  # Update position
                matched = True
                break
        
        if not matched:
            # New unique vehicle
            unique_vehicles.append({
                'first_seen': timestamp,
                'last_seen': timestamp,
                'bbox': bbox
            })
    
    return len(unique_vehicles)


def calculate_bbox_distance(bbox1: Dict[str, float], bbox2: Dict[str, float]) -> float:
    """Calculate normalized distance between two bounding boxes"""
    center1_x = bbox1['left'] + bbox1['width'] / 2
    center1_y = bbox1['top'] + bbox1['height'] / 2
    
    center2_x = bbox2['left'] + bbox2['width'] / 2
    center2_y = bbox2['top'] + bbox2['height'] / 2
    
    distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
    return distance


def generate_detection_timeline(vehicle_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate a timeline of vehicle detections
    
    Args:
        vehicle_detections: List of vehicle detections
        
    Returns:
        List of timeline entries
    """
    timeline = []
    
    for detection in vehicle_detections:
        timeline_entry = {
            'timestamp': detection['timestamp'],
            'vehicle_type': detection['vehicle_type'],
            'label_name': detection['label_name'],
            'confidence': detection['confidence']
        }
        timeline.append(timeline_entry)
    
    return timeline


def calculate_processing_stats(
    video_metadata: Dict[str, Any],
    vehicle_detections: List[Dict[str, Any]],
    rekognition_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate processing statistics"""
    
    duration_ms = video_metadata.get('DurationMillis', 0)
    frame_rate = video_metadata.get('FrameRate', 30)
    
    # Calculate estimated frames
    estimated_frames = int((duration_ms / 1000.0) * frame_rate) if frame_rate > 0 else 0
    
    # Count detections by confidence ranges
    confidence_distribution = {
        'high_confidence': len([d for d in vehicle_detections if d['confidence'] >= 90]),
        'medium_confidence': len([d for d in vehicle_detections if 80 <= d['confidence'] < 90]),
        'low_confidence': len([d for d in vehicle_detections if MIN_CONFIDENCE <= d['confidence'] < 80])
    }
    
    return {
        'estimated_frames_analyzed': estimated_frames,
        'total_detections': len(vehicle_detections),
        'analysis_duration_seconds': round(duration_ms / 1000.0, 2),
        'confidence_distribution': confidence_distribution,
        'detection_rate': round(len(vehicle_detections) / max(1, duration_ms / 1000.0), 2)
    }


def save_results_to_s3(
    bucket_name: str,
    job_id: str,
    analysis_results: Dict[str, Any],
    vehicle_detections: List[Dict[str, Any]]
) -> bool:
    """
    Save analysis results to S3 in multiple formats
    
    Args:
        bucket_name: S3 bucket name
        job_id: Job identifier
        analysis_results: Complete analysis results
        vehicle_detections: Raw vehicle detections
        
    Returns:
        True if successful, False otherwise
    """
    try:
        results_prefix = f"results/{job_id}"
        
        # Save JSON summary
        json_key = f"{results_prefix}/analysis.json"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=json_key,
            Body=json.dumps(analysis_results, indent=2),
            ContentType='application/json'
        )
        
        # Save detailed CSV
        csv_content = generate_csv_report(vehicle_detections)
        csv_key = f"{results_prefix}/detections.csv"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=csv_key,
            Body=csv_content,
            ContentType='text/csv'
        )
        
        # Save processing completion marker
        completion_key = f"{results_prefix}/completed.json"
        completion_data = {
            'jobId': job_id,
            'status': 'completed',
            'completedAt': datetime.utcnow().isoformat(),
            'resultsFiles': {
                'summary': json_key,
                'detections': csv_key
            }
        }
        s3_client.put_object(
            Bucket=bucket_name,
            Key=completion_key,
            Body=json.dumps(completion_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Saved results to S3: {results_prefix}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save results to S3: {str(e)}")
        return False


def generate_csv_report(vehicle_detections: List[Dict[str, Any]]) -> str:
    """Generate CSV report of vehicle detections"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'timestamp',
        'vehicle_type',
        'label_name',
        'confidence',
        'bbox_left',
        'bbox_top',
        'bbox_width',
        'bbox_height'
    ])
    
    # Write detections
    for detection in vehicle_detections:
        bbox = detection['bounding_box']
        writer.writerow([
            detection['timestamp'],
            detection['vehicle_type'],
            detection['label_name'],
            detection['confidence'],
            bbox['left'],
            bbox['top'],
            bbox['width'],
            bbox['height']
        ])
    
    return output.getvalue()


def create_error_result(bucket_name: str, job_id: str, error_message: str) -> bool:
    """Create error result file in S3"""
    try:
        error_key = f"errors/{job_id}/error.json"
        error_data = {
            'jobId': job_id,
            'status': 'failed',
            'error': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'stage': 'results_processing'
        }
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=error_key,
            Body=json.dumps(error_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Created error result for job {job_id}: {error_message}")
        return True
    except Exception as e:
        logger.error(f"Failed to create error result: {str(e)}")
        return False


def cleanup_processing_marker(bucket_name: str, job_id: str) -> bool:
    """Remove processing marker file"""
    try:
        marker_key = f"processing/{job_id}.processing"
        s3_client.delete_object(Bucket=bucket_name, Key=marker_key)
        logger.info(f"Cleaned up processing marker for job {job_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to cleanup processing marker: {str(e)}")
        return False
