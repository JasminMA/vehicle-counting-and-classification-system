import pytest
import json
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
import os
import sys

# Add the results-processor directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'results-processor'))

# Import from the results-processor module  
import handler as results_processor_handler


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
            with patch.object(results_processor_handler, 'process_successful_job', return_value=True):
                response = results_processor_handler.lambda_handler(event, None)
                
                assert response['statusCode'] == 200
                response_body = json.loads(response['body'])
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
            with patch.object(results_processor_handler, 'create_error_result', return_value=True) as mock_error:
                response = results_processor_handler.lambda_handler(event, None)
                
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

        response = results_processor_handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert 'Processed 1 result(s)' in response_body['message']
    
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
        response = results_processor_handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert 'Processed 1 result(s)' in response_body['message']


class TestSNSRecordValidation:
    
    def test_is_valid_sns_record_success(self):
        """Test valid SNS record validation"""
        record = {
            'Sns': {
                'Message': json.dumps({'JobId': '123'})
            }
        }
        assert results_processor_handler.is_valid_sns_record(record) is True
    
    def test_is_valid_sns_record_missing_sns(self):
        """Test invalid SNS record - missing Sns key"""
        record = {'NotSns': 'data'}
        assert results_processor_handler.is_valid_sns_record(record) is False
    
    def test_is_valid_sns_record_missing_message(self):
        """Test invalid SNS record - missing Message key"""
        record = {'Sns': {'NotMessage': 'data'}}
        assert results_processor_handler.is_valid_sns_record(record) is False


class TestVehicleClassification:
    
    def test_classify_vehicle_label_car(self):
        """Test car classification"""
        assert results_processor_handler.classify_vehicle_label('Car') == 'cars'
        assert results_processor_handler.classify_vehicle_label('Sedan') == 'cars'
        assert results_processor_handler.classify_vehicle_label('SUV') == 'cars'
    
    def test_classify_vehicle_label_truck(self):
        """Test truck classification"""
        assert results_processor_handler.classify_vehicle_label('Truck') == 'trucks'
        assert results_processor_handler.classify_vehicle_label('Pickup Truck') == 'trucks'
        assert results_processor_handler.classify_vehicle_label('Semi Truck') == 'trucks'
    
    def test_classify_vehicle_label_motorcycle(self):
        """Test motorcycle classification"""
        assert results_processor_handler.classify_vehicle_label('Motorcycle') == 'motorcycles'
        assert results_processor_handler.classify_vehicle_label('Scooter') == 'motorcycles'
        assert results_processor_handler.classify_vehicle_label('Moped') == 'motorcycles'
    
    def test_classify_vehicle_label_bus(self):
        """Test bus classification"""
        assert results_processor_handler.classify_vehicle_label('Bus') == 'buses'
        assert results_processor_handler.classify_vehicle_label('School Bus') == 'buses'
    
    def test_classify_vehicle_label_van(self):
        """Test van classification"""
        assert results_processor_handler.classify_vehicle_label('Van') == 'vans'
        assert results_processor_handler.classify_vehicle_label('Minivan') == 'vans'
    
    def test_classify_vehicle_label_emergency(self):
        """Test emergency vehicle classification"""
        assert results_processor_handler.classify_vehicle_label('Ambulance') == 'emergency_vehicles'
        assert results_processor_handler.classify_vehicle_label('Fire Truck') == 'emergency_vehicles'
    
    def test_classify_vehicle_label_non_vehicle(self):
        """Test non-vehicle label"""
        assert results_processor_handler.classify_vehicle_label('Person') is None
        assert results_processor_handler.classify_vehicle_label('Building') is None


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

        vehicle_detections = results_processor_handler.process_vehicle_labels(rekognition_results)
        
        assert len(vehicle_detections) == 2  # Only vehicles, not person
        assert vehicle_detections[0]['vehicle_type'] == 'cars'
        assert vehicle_detections[1]['vehicle_type'] == 'trucks'
        assert vehicle_detections[0]['timestamp'] == 5.0
        assert vehicle_detections[1]['timestamp'] == 7.0
    
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

        vehicle_detections = results_processor_handler.process_vehicle_labels(rekognition_results)
        assert len(vehicle_detections) == 0  # Should be filtered out
    
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

        vehicle_detections = results_processor_handler.process_vehicle_labels(rekognition_results)
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

        counts = results_processor_handler.count_vehicles_by_type(vehicle_detections)
        
        assert counts['cars'] >= 1
        assert counts['trucks'] >= 1
        assert counts['motorcycles'] >= 1
        assert counts['total_vehicles'] >= 3
    
    def test_count_vehicles_by_type_empty(self):
        """Test counting with no detections"""
        vehicle_detections = []

        counts = results_processor_handler.count_vehicles_by_type(vehicle_detections)
        assert counts['total_vehicles'] == 0
    
    def test_estimate_unique_vehicles_single(self):
        """Test estimating unique vehicles with single detection"""
        detections = [
            {'timestamp': 1.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}}
        ]

        count = results_processor_handler.estimate_unique_vehicles(detections)
        assert count == 1
    
    def test_estimate_unique_vehicles_same_location(self):
        """Test estimating unique vehicles with same location detections"""
        detections = [
            {'timestamp': 1.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}},
            {'timestamp': 1.5, 'bounding_box': {'left': 0.11, 'top': 0.11, 'width': 0.2, 'height': 0.2}},  # Very close
            {'timestamp': 2.0, 'bounding_box': {'left': 0.12, 'top': 0.12, 'width': 0.2, 'height': 0.2}}   # Very close
        ]

        count = results_processor_handler.estimate_unique_vehicles(detections)
        assert count == 1  # Should be counted as one vehicle
    
    def test_estimate_unique_vehicles_different_locations(self):
        """Test estimating unique vehicles with different locations"""
        detections = [
            {'timestamp': 1.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}},
            {'timestamp': 1.5, 'bounding_box': {'left': 0.8, 'top': 0.8, 'width': 0.2, 'height': 0.2}}  # Far apart
        ]

        count = results_processor_handler.estimate_unique_vehicles(detections)
        assert count == 2  # Should be counted as two vehicles
    
    def test_calculate_bbox_distance(self):
        """Test bounding box distance calculation"""
        bbox1 = {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}  # Center at (0.2, 0.2)
        bbox2 = {'left': 0.2, 'top': 0.2, 'width': 0.2, 'height': 0.2}  # Center at (0.3, 0.3)

        distance = results_processor_handler.calculate_bbox_distance(bbox1, bbox2)
        
        # Distance should be sqrt((0.3-0.2)^2 + (0.3-0.2)^2) = sqrt(0.02) ≈ 0.141
        assert 0.1 < distance < 0.2


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

        results = results_processor_handler.generate_analysis_results(
            job_id, job_metadata, vehicle_detections, rekognition_results
        )
        
        assert results['video_info']['filename'] == 'test_video.mp4'
        assert results['video_info']['duration_seconds'] == 30.0
        assert results['video_info']['analysis_id'] == job_id
        assert 'vehicle_counts' in results
        assert 'timeline' in results
        assert 'processing_stats' in results


class TestS3Operations:
    
    @mock_aws
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

        success = results_processor_handler.save_results_to_s3(bucket_name, job_id, analysis_results, vehicle_detections)
        
        assert success is True
        
        # Verify files were created
        assert results_processor_handler.s3_object_exists(bucket_name, f'results/{job_id}/analysis.json')
        assert results_processor_handler.s3_object_exists(bucket_name, f'results/{job_id}/detections.csv')
        assert results_processor_handler.s3_object_exists(bucket_name, f'results/{job_id}/completed.json')
    
    @mock_aws
    def test_create_error_result(self):
        """Test creating error result in S3"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)

        job_id = 'job-test-123'
        error_message = 'Test error message'

        success = results_processor_handler.create_error_result(bucket_name, job_id, error_message)
        
        assert success is True
        
        # Verify error file was created
        response = s3.get_object(Bucket=bucket_name, Key=f'errors/{job_id}/error.json')
        error_data = json.loads(response['Body'].read().decode('utf-8'))
        assert error_data['error'] == error_message
        assert error_data['status'] == 'failed'


class TestRekognitionIntegration:
    
    def test_get_rekognition_results_success(self):
        """Test getting Rekognition results"""
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

        # Mock the rekognition client at module level
        with patch.object(results_processor_handler.rekognition, 'get_label_detection', return_value=mock_response):
            results = results_processor_handler.get_rekognition_results('test-job-id')
            
            assert results is not None
            assert results['JobStatus'] == 'SUCCEEDED'
            assert len(results['Labels']) == 1
            assert results['VideoMetadata']['DurationMillis'] == 30000
    
    def test_get_rekognition_results_failed_job(self):
        """Test handling failed Rekognition job"""
        mock_response = {
            'JobStatus': 'FAILED',
            'StatusMessage': 'Invalid video format'
        }

        # Mock the rekognition client at module level
        with patch.object(results_processor_handler.rekognition, 'get_label_detection', return_value=mock_response):
            results = results_processor_handler.get_rekognition_results('test-job-id')
            
            assert results is None


if __name__ == '__main__':
    pytest.main([__file__])
