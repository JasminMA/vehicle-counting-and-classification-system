import pytest
import json
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
import os
import sys
import importlib.util

# Load results processor module directly to avoid path conflicts
def load_results_processor():
    handler_path = os.path.join(os.path.dirname(__file__), '..', 'results-processor', 'handler.py')
    spec = importlib.util.spec_from_file_location("results_processor", handler_path)
    results_processor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(results_processor)
    return results_processor

results_processor = load_results_processor()


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
            with patch.object(results_processor, 'process_successful_job', return_value=True):
                response = results_processor.lambda_handler(event, None)
                
                assert response['statusCode'] == 200
                response_body = json.loads(response['body'])
                assert 'message' in response_body
                assert 'Processed 1 result(s)' in response_body['message']


class TestSNSRecordValidation:
    
    def test_is_valid_sns_record_success(self):
        """Test valid SNS record validation"""
        record = {
            'Sns': {
                'Message': json.dumps({'JobId': '123'})
            }
        }
        assert results_processor.is_valid_sns_record(record) is True
    
    def test_is_valid_sns_record_missing_sns(self):
        """Test invalid SNS record - missing Sns key"""
        record = {'NotSns': 'data'}
        assert results_processor.is_valid_sns_record(record) is False


class TestVehicleClassification:
    
    def test_classify_vehicle_label_car(self):
        """Test car classification"""
        assert results_processor.classify_vehicle_label('Car') == 'cars'
        assert results_processor.classify_vehicle_label('Sedan') == 'cars'
        assert results_processor.classify_vehicle_label('SUV') == 'cars'
    
    def test_classify_vehicle_label_truck(self):
        """Test truck classification"""
        assert results_processor.classify_vehicle_label('Truck') == 'trucks'
        assert results_processor.classify_vehicle_label('Pickup Truck') == 'trucks'
        assert results_processor.classify_vehicle_label('Semi Truck') == 'trucks'
    
    def test_classify_vehicle_label_motorcycle(self):
        """Test motorcycle classification"""
        assert results_processor.classify_vehicle_label('Motorcycle') == 'motorcycles'
        assert results_processor.classify_vehicle_label('Scooter') == 'motorcycles'
    
    def test_classify_vehicle_label_bus(self):
        """Test bus classification"""
        assert results_processor.classify_vehicle_label('Bus') == 'buses'
        assert results_processor.classify_vehicle_label('School Bus') == 'buses'
    
    def test_classify_vehicle_label_van(self):
        """Test van classification"""
        assert results_processor.classify_vehicle_label('Van') == 'vans'
        assert results_processor.classify_vehicle_label('Minivan') == 'vans'
    
    def test_classify_vehicle_label_emergency(self):
        """Test emergency vehicle classification"""
        assert results_processor.classify_vehicle_label('Ambulance') == 'emergency_vehicles'
        assert results_processor.classify_vehicle_label('Fire Truck') == 'emergency_vehicles'
        assert results_processor.classify_vehicle_label('Police Car') == 'emergency_vehicles'
    
    def test_classify_vehicle_label_non_vehicle(self):
        """Test non-vehicle label"""
        assert results_processor.classify_vehicle_label('Person') is None
        assert results_processor.classify_vehicle_label('Building') is None
        assert results_processor.classify_vehicle_label('Tree') is None


class TestVehicleCounting:
    
    def test_count_vehicles_by_type_simple(self):
        """Test simple vehicle counting"""
        vehicle_detections = [
            {'vehicle_type': 'cars', 'timestamp': 1.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}},
            {'vehicle_type': 'cars', 'timestamp': 2.0, 'bounding_box': {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}},
            {'vehicle_type': 'trucks', 'timestamp': 3.0, 'bounding_box': {'left': 0.5, 'top': 0.5, 'width': 0.3, 'height': 0.3}},
            {'vehicle_type': 'motorcycles', 'timestamp': 4.0, 'bounding_box': {'left': 0.8, 'top': 0.8, 'width': 0.1, 'height': 0.1}}
        ]
        
        counts = results_processor.count_vehicles_by_type(vehicle_detections)
        
        assert counts['cars'] >= 1
        assert counts['trucks'] >= 1
        assert counts['motorcycles'] >= 1
        assert counts['total_vehicles'] >= 3
    
    def test_count_vehicles_by_type_empty(self):
        """Test counting with no detections"""
        vehicle_detections = []
        
        counts = results_processor.count_vehicles_by_type(vehicle_detections)
        
        assert counts['total_vehicles'] == 0

    def test_calculate_bbox_distance(self):
        """Test bounding box distance calculation"""
        bbox1 = {'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}  # Center at (0.2, 0.2)
        bbox2 = {'left': 0.2, 'top': 0.2, 'width': 0.2, 'height': 0.2}  # Center at (0.3, 0.3)
        
        distance = results_processor.calculate_bbox_distance(bbox1, bbox2)
        
        # Distance between (0.2, 0.2) and (0.3, 0.3) should be sqrt(0.02) ≈ 0.141
        assert abs(distance - 0.141) < 0.01


@mock_aws
class TestS3Operations:
    
    def test_create_error_result(self):
        """Test creating error result in S3"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        job_id = 'job-test-123'
        error_message = 'Test error message'
        
        success = results_processor.create_error_result(bucket_name, job_id, error_message)
        
        assert success is True
        
        # Check that error file was created
        error_key = f'errors/{job_id}/error.json'
        response = s3.get_object(Bucket=bucket_name, Key=error_key)
        error_data = json.loads(response['Body'].read().decode('utf-8'))
        
        assert error_data['jobId'] == job_id
        assert error_data['status'] == 'failed'
        assert error_data['error'] == error_message


if __name__ == '__main__':
    pytest.main([__file__])
