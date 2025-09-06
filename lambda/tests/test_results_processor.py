import pytest
import json
import boto3
from moto import mock_rekognition, mock_s3
from unittest.mock import patch, MagicMock
import os
import sys

# Add the results-processor directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'results-processor'))

from handler import (
    lambda_handler,
    is_valid_sns_record,
    process_successful_job,
    get_rekognition_results,
    process_vehicle_labels,
    classify_vehicle_label,
    count_vehicles_by_type,
    estimate_unique_vehicles,
    calculate_bbox_distance,
    generate_analysis_results,
    save_results_to_s3,
    create_error_result
)


class TestResultsProcessor:
    
    def test_lambda_handler_success(self):
        """Test successful lambda handler execution"""
        # Mock SNS event
        event = {
            'Records': [
                {
                    'Sns': {
                        'Message': json.dumps({
                            'JobId': 'rekognition-123',
                            'Status': 'SUCCEEDED',
                            'JobTag': 'job-abc123'
                        })
                    }
                }
            ]
        }
        
        with patch.dict(os.environ, {'STORAGE_BUCKET_NAME': 'test-bucket'}):
            with patch('handler.process_successful_job', return_value=True):
                response = lambda_handler(event, None)
                
                assert response['statusCode'] == 200
                response_body = json.loads(response['body'])
                assert 'message' in response_body
                assert 'Processed 1 result(s)' in response_body['message']
    
    def test_lambda_handler_failed_job(self):
        """Test handling of failed Rekognition job"""
        event = {
            'Records': [
                {
                    'Sns': {
                        'Message': json.dumps({
                            'JobId': 'rekognition-123',
                            'Status': 'FAILED',
                            'JobTag': 'job-abc123',
                            'StatusMessage': 'Video format not supported'
                        })
                    }
                }
            ]
        }
        
        with patch.dict(os.environ, {'STORAGE_BUCKET_NAME': 'test-bucket'}):
            with patch('handler.create_error_result', return_value=True) as mock_error:
                response = lambda_handler(event, None)
                
                assert response['statusCode'] == 200
                mock_error.assert_called_once()
    
    def test_lambda_handler_invalid_record(self):
        """Test handling of invalid SNS record"""
        event = {
            'Records': [
                {
                    'InvalidRecord': 'bad data'
                }
            ]
        }
        
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
    
    def test_lambda_handler_missing_env_var(self):
        """Test error when environment variable is missing"""
        event = {
            'Records': [
                {
                    'Sns': {
                        'Message': json.dumps({
                            'JobId': 'rekognition-123',
                            'Status': 'SUCCEEDED',
                            'JobTag': 'job-abc123'
                        })
                    }
                }
            ]
        }
        
        # Don't set STORAGE_BUCKET_NAME
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200  # Should continue processing other records


class TestSNSRecordValidation:
    
    def test_is_valid_sns_record_success(self):
        """Test valid SNS record validation"""
        record = {
            'Sns': {
                'Message': json.dumps({'JobId': '123'})
            }
        }
        assert is_valid_sns_record(record) is True
    
    def test_is_valid_sns_record_missing_sns(self):
        """Test invalid SNS record - missing Sns key"""
        record = {'NotSns': 'data'}
        assert is_valid_sns_record(record) is False
    
    def test_is_valid_sns_record_missing_message(self):
        """Test invalid SNS record - missing Message key"""
        record = {'Sns': {'NotMessage': 'data'}}
        assert is_valid_sns_record(record) is False


class TestVehicleClassification:
    
    def test_classify_vehicle_label_car(self):
        """Test car classification"""
        assert classify_vehicle_label('Car') == 'cars'
        assert classify_vehicle_label('Sedan') == 'cars'
        assert classify_vehicle_label('SUV') == 'cars'
    
    def test_classify_vehicle_label_truck(self):
        """Test truck classification"""
        assert classify_vehicle_label('Truck') == 'trucks'
        assert classify_vehicle_label('Pickup Truck') == 'trucks'
        assert classify_vehicle_label('Semi Truck') == 'trucks'
    
    def test_classify_vehicle_label_motorcycle(self):
        """Test motorcycle classification"""
        assert classify_vehicle_label('Motorcycle') == 'motorcycles'
        assert classify_vehicle_label('Scooter') == 'motorcycles'
    
    def test_classify_vehicle_label_bus(self):
        """Test bus classification"""
        assert classify_vehicle_label('Bus') == 'buses'
        assert classify_vehicle_label('School Bus') == 'buses'
    
    def test_classify_vehicle_label_van(self):
        """Test van classification"""
        assert classify_vehicle_label('Van') == 'vans'
        assert classify_vehicle_label('Minivan') == 'vans'
    
    def test_classify_vehicle_label_emergency(self):
        """Test emergency vehicle classification"""
        assert classify_vehicle_label('Ambulance') == 'emergency_vehicles'
        assert classify_vehicle_label('Fire Truck') == 'emergency_vehicles'
        assert classify_vehicle_label('Police Car') == 'emergency_vehicles'
    
    def test_classify_vehicle_label_non_vehicle(self):
        """Test non-vehicle label"""
        assert classify_vehicle_label('Person') is None
        assert classify_vehicle_label('Building') is None
        assert classify_vehicle_label('Tree') is None


class TestVehicleDetectionProcessing:
    
    def test_process_vehicle_labels_success(self):
        """Test processing vehicle labels from Rekognition results"""
        rekognition_results = {
            'Labels': [
                {
                    'Timestamp': 5000,  # 5 seconds
                    'Label': {
                        'Name': 'Car',
                        'Confidence': 85.5,
                        'Instances': [
                            {
                                'Confidence': 85.5,
                                'BoundingBox': {
                                    'Left': 0.1,
                                    'Top': 0.2,
                                    'Width': 0.3,
                                    'Height': 0.4
                                }
                            }
                        ]
                    }
                },
                {
                    'Timestamp': 7000,  # 7 seconds
                    'Label': {
                        'Name': 'Truck',
                        'Confidence': 92.1,
                        'Instances': [
                            {
                                'Confidence': 92.1,
                                'BoundingBox': {
                                    'Left': 0.5,
                                    'Top': 0.3,
                                    'Width': 0.2,
                                    'Height': 0.3
                                }
                            }
                        ]
                    }
                },
                {
                    'Timestamp': 10000,  # 10 seconds
                    'Label': {
                        'Name': 'Person',  # Non-vehicle label
                        'Confidence': 95.0,
                        'Instances': [
                            {
                                'Confidence': 95.0,
                                'BoundingBox': {
                                    'Left': 0.7,
                                    'Top': 0.8,
                                    'Width': 0.1,
                                    'Height': 0.1
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        vehicle_detections = process_vehicle_labels(rekognition_results)
        
        # Should find 2 vehicle detections (Car and Truck), not Person
        assert len(vehicle_detections) == 2
        
        # Check first detection (Car)
        car_detection = vehicle_detections[0]
        assert car_detection['timestamp'] == 5.0
        assert car_detection['vehicle_type'] == 'cars'
        assert car_detection['label_name'] == 'Car'
        assert car_detection['confidence'] == 85.5
        
        # Check second detection (Truck)
        truck_detection = vehicle_detections[1]
        assert truck_detection['timestamp'] == 7.0
        assert truck_detection['vehicle_type'] == 'trucks'
        assert truck_detection['label_name'] == 'Truck'
        assert truck_detection['confidence'] == 92.1
    
    def test_process_vehicle_labels_low_confidence_filtered(self):
        """Test that low confidence detections are filtered out"""
        rekognition_results = {
            'Labels': [
                {
                    'Timestamp': 5000,
                    'Label': {
                        'Name': 'Car',
                        'Confidence': 60.0,  # Below MIN_CONFIDENCE (70)
                        'Instances': [
                            {
                                'Confidence': 60.0,
                                'BoundingBox': {
                                    'Left': 0.1,
                                    'Top': 0.2,
                                    'Width': 0.3,
                                    'Height': 0.4
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        vehicle_detections = process_vehicle_labels(rekognition_results)
        
        # Should be empty due to low confidence
        assert len(vehicle_detections) == 0
    
    def test_process_vehicle_labels_no_instances(self):
        """Test handling of labels with no instances"""
        rekognition_results = {
            'Labels': [
                {
                    'Timestamp': 5000,
                    'Label': {
                        'Name': 'Car',
                        'Confidence': 85.0,
                        'Instances': []  # No instances
                    }
                }
            ]
        }
        
        vehicle_detections = process_vehicle_labels(rekognition_results)
        
        # Should be empty since no instances
        assert len(vehicle_detections) == 0


class TestVehicleCounting:
    
    def test_count_vehicles_by_type_simple(self):
        """Test simple vehicle counting"""
        vehicle_detections = [
            {'vehicle_type': 'cars', 'timestamp': 1.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}},
            {'vehicle_type': 'cars', 'timestamp': 2.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}},
            {'vehicle_type': 'trucks', 'timestamp': 3.0, 'bounding_box': {'left': 0.5, 'top': 0.5, 'width': 0.3, 'height': 0.3}},
            {'vehicle_type': 'motorcycles', 'timestamp': 4.0, 'bounding_box': {'left': 0.8, 'top': 0.8, 'width': 0.1, 'height': 0.1}}
        ]
        
        counts = count_vehicles_by_type(vehicle_detections)
        
        assert counts['cars'] >= 1
        assert counts['trucks'] >= 1
        assert counts['motorcycles'] >= 1
        assert counts['total_vehicles'] >= 3
    
    def test_count_vehicles_by_type_empty(self):
        """Test counting with no detections"""
        vehicle_detections = []
        
        counts = count_vehicles_by_type(vehicle_detections)
        
        assert counts['total_vehicles'] == 0
    
    def test_estimate_unique_vehicles_single(self):
        """Test estimating unique vehicles with single detection"""
        detections = [
            {'timestamp': 1.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}}
        ]
        
        count = estimate_unique_vehicles(detections)
        assert count == 1
    
    def test_estimate_unique_vehicles_same_location(self):
        """Test estimating unique vehicles with same location detections"""
        detections = [
            {'timestamp': 1.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}},
            {'timestamp': 1.5, 'bounding_box': {'left': 0.11, 'top': 0.11, 'width': 0.2, 'height': 0.2}},  # Very close
            {'timestamp': 2.0, 'bounding_box': {'left': 0.12, 'top': 0.12, 'width': 0.2, 'height': 0.2}}   # Very close
        ]
        
        count = estimate_unique_vehicles(detections)
        assert count == 1  # Should be counted as same vehicle
    
    def test_estimate_unique_vehicles_different_locations(self):
        """Test estimating unique vehicles with different locations"""
        detections = [
            {'timestamp': 1.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}},
            {'timestamp': 1.5, 'bounding_box': {'left': 0.8, 'top': 0.8, 'width': 0.2, 'height': 0.2}}  # Far apart
        ]
        
        count = estimate_unique_vehicles(detections)
        assert count == 2  # Should be counted as different vehicles
    
    def test_calculate_bbox_distance(self):
        """Test bounding box distance calculation"""
        bbox1 = {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}  # Center at (0.2, 0.2)
        bbox2 = {'left': 0.2, 'top': 0.2, 'width': 0.2, 'height': 0.2}  # Center at (0.3, 0.3)
        
        distance = calculate_bbox_distance(bbox1, bbox2)
        
        # Distance between (0.2, 0.2) and (0.3, 0.3) should be sqrt(0.02) ≈ 0.141
        assert abs(distance - 0.141) < 0.01


class TestAnalysisResults:
    
    def test_generate_analysis_results(self):
        """Test generating complete analysis results"""
        job_id = 'job-test-123'
        job_metadata = {'filename': 'test_video.mp4'}
        vehicle_detections = [
            {
                'timestamp': 5.0,
                'vehicle_type': 'cars',
                'label_name': 'Car',
                'confidence': 85.5,
                'bounding_box': {'left': 0.1, 'top': 0.2, 'width': 0.3, 'height': 0.4}
            }
        ]
        rekognition_results = {
            'VideoMetadata': {
                'DurationMillis': 30000,  # 30 seconds
                'FrameRate': 30,
                'Format': 'mp4'
            }
        }
        
        results = generate_analysis_results(
            job_id, job_metadata, vehicle_detections, rekognition_results
        )
        
        # Check structure
        assert 'video_info' in results
        assert 'vehicle_counts' in results
        assert 'timeline' in results
        assert 'processing_stats' in results
        
        # Check video info
        video_info = results['video_info']
        assert video_info['filename'] == 'test_video.mp4'
        assert video_info['duration_seconds'] == 30.0
        assert video_info['analysis_id'] == job_id
        
        # Check counts
        vehicle_counts = results['vehicle_counts']
        assert 'total_vehicles' in vehicle_counts
        
        # Check timeline
        timeline = results['timeline']
        assert len(timeline) >= 1
        assert timeline[0]['timestamp'] == 5.0
        assert timeline[0]['vehicle_type'] == 'cars'


@mock_s3
class TestS3Operations:
    
    def test_save_results_to_s3(self):
        """Test saving results to S3"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        job_id = 'job-test-123'
        analysis_results = {
            'video_info': {'filename': 'test.mp4'},
            'vehicle_counts': {'cars': 2, 'total_vehicles': 2},
            'timeline': []
        }
        vehicle_detections = [
            {
                'timestamp': 5.0,
                'vehicle_type': 'cars',
                'label_name': 'Car',
                'confidence': 85.5,
                'bounding_box': {'left': 0.1, 'top': 0.2, 'width': 0.3, 'height': 0.4}
            }
        ]
        
        success = save_results_to_s3(bucket_name, job_id, analysis_results, vehicle_detections)
        
        assert success is True
        
        # Check that files were created
        objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=f'results/{job_id}/')
        assert objects['KeyCount'] == 3  # analysis.json, detections.csv, completed.json
    
    def test_create_error_result(self):
        """Test creating error result in S3"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        job_id = 'job-test-123'
        error_message = 'Test error message'
        
        success = create_error_result(bucket_name, job_id, error_message)
        
        assert success is True
        
        # Check that error file was created
        error_key = f'errors/{job_id}/error.json'
        response = s3.get_object(Bucket=bucket_name, Key=error_key)
        error_data = json.loads(response['Body'].read().decode('utf-8'))
        
        assert error_data['jobId'] == job_id
        assert error_data['status'] == 'failed'
        assert error_data['error'] == error_message


@mock_rekognition
class TestRekognitionIntegration:
    
    def test_get_rekognition_results_success(self):
        """Test getting Rekognition results"""
        # Mock Rekognition client
        rekognition = boto3.client('rekognition', region_name='us-east-1')
        
        # Mock the get_label_detection response
        mock_response = {
            'JobStatus': 'SUCCEEDED',
            'VideoMetadata': {
                'DurationMillis': 30000,
                'FrameRate': 30
            },
            'Labels': [
                {
                    'Timestamp': 5000,
                    'Label': {
                        'Name': 'Car',
                        'Confidence': 85.5,
                        'Instances': []
                    }
                }
            ]
        }
        
        with patch.object(rekognition, 'get_label_detection', return_value=mock_response):
            results = get_rekognition_results('test-job-id')
            
            assert results is not None
            assert results['JobStatus'] == 'SUCCEEDED'
            assert len(results['Labels']) == 1
            assert results['Labels'][0]['Label']['Name'] == 'Car'
    
    def test_get_rekognition_results_failed_job(self):
        """Test handling failed Rekognition job"""
        rekognition = boto3.client('rekognition', region_name='us-east-1')
        
        mock_response = {
            'JobStatus': 'FAILED',
            'StatusMessage': 'Invalid video format'
        }
        
        with patch.object(rekognition, 'get_label_detection', return_value=mock_response):
            results = get_rekognition_results('test-job-id')
            
            assert results is None  # Should return None for failed jobs


if __name__ == '__main__':
    pytest.main([__file__])
