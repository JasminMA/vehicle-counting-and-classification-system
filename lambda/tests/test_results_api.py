import pytest
import json
import boto3
from moto import mock_s3
from unittest.mock import patch, MagicMock
import os
import sys

# Add the results-api directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'results-api'))

from handler import (
    lambda_handler,
    handle_results_request,
    handle_status_request,
    handle_download_request,
    get_job_status,
    get_analysis_results,
    s3_object_exists,
    generate_download_url,
    is_valid_job_id,
    create_success_response,
    create_error_response
)


class TestResultsAPI:
    
    @mock_s3
    def test_lambda_handler_results_success(self):
        """Test successful results request"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        job_id = 'job-test-123'
        
        # Create completed marker
        s3.put_object(
            Bucket=bucket_name,
            Key=f'results/{job_id}/completed.json',
            Body=json.dumps({'jobId': job_id, 'status': 'completed'})
        )
        
        # Create analysis results
        analysis_data = {
            'video_info': {'filename': 'test.mp4'},
            'vehicle_counts': {'cars': 5, 'total_vehicles': 5},
            'timeline': []
        }
        s3.put_object(
            Bucket=bucket_name,
            Key=f'results/{job_id}/analysis.json',
            Body=json.dumps(analysis_data)
        )
        
        # API Gateway event
        event = {
            'httpMethod': 'GET',
            'resource': '/results/{jobId}',
            'pathParameters': {'jobId': job_id},
            'queryStringParameters': None
        }
        
        with patch.dict(os.environ, {'STORAGE_BUCKET_NAME': bucket_name}):
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            response_body = json.loads(response['body'])
            assert response_body['jobId'] == job_id
            assert response_body['status'] == 'completed'
            assert 'results' in response_body
    
    def test_lambda_handler_invalid_method(self):
        """Test invalid HTTP method"""
        event = {
            'httpMethod': 'POST',
            'resource': '/results/{jobId}',
            'pathParameters': {'jobId': 'job-test-123'}
        }
        
        response = lambda_handler(event, None)
        assert response['statusCode'] == 405
    
    def test_lambda_handler_missing_job_id(self):
        """Test missing job ID"""
        event = {
            'httpMethod': 'GET',
            'resource': '/results/{jobId}',
            'pathParameters': None
        }
        
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
    
    def test_lambda_handler_invalid_job_id(self):
        """Test invalid job ID format"""
        event = {
            'httpMethod': 'GET',
            'resource': '/results/{jobId}',
            'pathParameters': {'jobId': '../invalid'}
        }
        
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
    
    def test_lambda_handler_missing_bucket_env(self):
        """Test missing bucket environment variable"""
        event = {
            'httpMethod': 'GET',
            'resource': '/results/{jobId}',
            'pathParameters': {'jobId': 'job-test-123'}
        }
        
        response = lambda_handler(event, None)
        assert response['statusCode'] == 500


class TestJobIDValidation:
    
    def test_is_valid_job_id_success(self):
        """Test valid job IDs"""
        assert is_valid_job_id('job-test-123') is True
        assert is_valid_job_id('job-20240101-120000-abc123') is True
        assert is_valid_job_id('job-abc123def456') is True
    
    def test_is_valid_job_id_invalid_prefix(self):
        """Test invalid prefix"""
        assert is_valid_job_id('invalid-123') is False
        assert is_valid_job_id('test-123') is False
    
    def test_is_valid_job_id_too_short(self):
        """Test too short job ID"""
        assert is_valid_job_id('job-123') is False
        assert is_valid_job_id('job-') is False
    
    def test_is_valid_job_id_too_long(self):
        """Test too long job ID"""
        long_id = 'job-' + 'a' * 100
        assert is_valid_job_id(long_id) is False
    
    def test_is_valid_job_id_path_traversal(self):
        """Test path traversal attempts"""
        assert is_valid_job_id('job-../test') is False
        assert is_valid_job_id('job-test/path') is False
        assert is_valid_job_id('job-test\\path') is False
    
    def test_is_valid_job_id_none_or_empty(self):
        """Test None or empty job ID"""
        assert is_valid_job_id(None) is False
        assert is_valid_job_id('') is False
        assert is_valid_job_id(123) is False


@mock_s3
class TestJobStatus:
    
    def setup_method(self):
        """Setup for each test"""
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.bucket_name = 'test-bucket'
        self.s3.create_bucket(Bucket=self.bucket_name)
        self.job_id = 'job-test-123'
    
    def test_get_job_status_completed(self):
        """Test completed job status"""
        completion_data = {
            'jobId': self.job_id,
            'status': 'completed',
            'completedAt': '2024-01-01T12:00:00Z'
        }
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/completed.json',
            Body=json.dumps(completion_data)
        )
        
        status = get_job_status(self.bucket_name, self.job_id)
        assert status['status'] == 'completed'
        assert status['timestamp'] == '2024-01-01T12:00:00Z'
    
    def test_get_job_status_failed(self):
        """Test failed job status"""
        error_data = {
            'jobId': self.job_id,
            'status': 'failed',
            'error': 'Video format not supported',
            'timestamp': '2024-01-01T12:00:00Z'
        }
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'errors/{self.job_id}/error.json',
            Body=json.dumps(error_data)
        )
        
        status = get_job_status(self.bucket_name, self.job_id)
        assert status['status'] == 'failed'
        assert status['error'] == 'Video format not supported'
    
    def test_get_job_status_processing(self):
        """Test processing job status"""
        processing_data = {
            'jobId': self.job_id,
            'status': 'processing',
            'stage': 'rekognition_running',
            'startTime': '2024-01-01T11:55:00Z'
        }
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'processing/{self.job_id}.processing',
            Body=json.dumps(processing_data)
        )
        
        status = get_job_status(self.bucket_name, self.job_id)
        assert status['status'] == 'processing'
        assert status['stage'] == 'rekognition_running'
    
    def test_get_job_status_pending(self):
        """Test pending job status (uploaded but not started)"""
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'uploads/{self.job_id}/test_video.mp4',
            Body=b'fake video content'
        )
        
        status = get_job_status(self.bucket_name, self.job_id)
        assert status['status'] == 'pending'
    
    def test_get_job_status_not_found(self):
        """Test job not found"""
        status = get_job_status(self.bucket_name, 'nonexistent-job')
        assert status['status'] == 'not_found'


@mock_s3
class TestResultsRetrieval:
    
    def setup_method(self):
        """Setup for each test"""
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.bucket_name = 'test-bucket'
        self.s3.create_bucket(Bucket=self.bucket_name)
        self.job_id = 'job-test-123'
    
    def test_get_analysis_results_success(self):
        """Test successful analysis results retrieval"""
        analysis_data = {
            'video_info': {
                'filename': 'test_video.mp4',
                'duration_seconds': 30.0
            },
            'vehicle_counts': {
                'cars': 5,
                'trucks': 2,
                'total_vehicles': 7
            },
            'timeline': [
                {'timestamp': 5.0, 'vehicle_type': 'cars', 'confidence': 85.5}
            ]
        }
        
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/analysis.json',
            Body=json.dumps(analysis_data)
        )
        
        results = get_analysis_results(self.bucket_name, self.job_id)
        assert results is not None
        assert results['video_info']['filename'] == 'test_video.mp4'
        assert results['vehicle_counts']['total_vehicles'] == 7
        assert len(results['timeline']) == 1
    
    def test_get_analysis_results_not_found(self):
        """Test analysis results not found"""
        results = get_analysis_results(self.bucket_name, 'nonexistent-job')
        assert results is None
    
    def test_s3_object_exists_true(self):
        """Test S3 object exists check - true case"""
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key='test-key',
            Body='test content'
        )
        
        assert s3_object_exists(self.bucket_name, 'test-key') is True
    
    def test_s3_object_exists_false(self):
        """Test S3 object exists check - false case"""
        assert s3_object_exists(self.bucket_name, 'nonexistent-key') is False


@mock_s3
class TestAPIEndpoints:
    
    def setup_method(self):
        """Setup for each test"""
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.bucket_name = 'test-bucket'
        self.s3.create_bucket(Bucket=self.bucket_name)
        self.job_id = 'job-test-123'
    
    def test_handle_results_request_completed(self):
        """Test results request for completed job"""
        # Create completion marker
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/completed.json',
            Body=json.dumps({'jobId': self.job_id, 'status': 'completed'})
        )
        
        # Create analysis results
        analysis_data = {
            'video_info': {'filename': 'test.mp4'},
            'vehicle_counts': {'cars': 5, 'total_vehicles': 5},
            'timeline': [{'timestamp': i, 'vehicle_type': 'cars'} for i in range(15)]
        }
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/analysis.json',
            Body=json.dumps(analysis_data)
        )
        
        response = handle_results_request(self.bucket_name, self.job_id, include_details=False)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['status'] == 'completed'
        assert len(response_body['results']['timeline']) == 10  # Truncated
        assert response_body['results']['timeline_truncated'] is True
    
    def test_handle_results_request_processing(self):
        """Test results request for processing job"""
        processing_data = {
            'jobId': self.job_id,
            'status': 'processing',
            'stage': 'rekognition_running'
        }
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'processing/{self.job_id}.processing',
            Body=json.dumps(processing_data)
        )
        
        response = handle_results_request(self.bucket_name, self.job_id)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['status'] == 'processing'
        assert response_body['stage'] == 'rekognition_running'
    
    def test_handle_results_request_failed(self):
        """Test results request for failed job"""
        error_data = {
            'jobId': self.job_id,
            'status': 'failed',
            'error': 'Video format not supported',
            'timestamp': '2024-01-01T12:00:00Z'
        }
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'errors/{self.job_id}/error.json',
            Body=json.dumps(error_data)
        )
        
        response = handle_results_request(self.bucket_name, self.job_id)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['status'] == 'failed'
        assert response_body['error'] == 'Video format not supported'
    
    def test_handle_results_request_not_found(self):
        """Test results request for non-existent job"""
        response = handle_results_request(self.bucket_name, 'nonexistent-job')
        
        assert response['statusCode'] == 404
    
    def test_handle_status_request_completed(self):
        """Test status request for completed job"""
        completion_data = {
            'jobId': self.job_id,
            'status': 'completed',
            'completedAt': '2024-01-01T12:00:00Z'
        }
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/completed.json',
            Body=json.dumps(completion_data)
        )
        
        response = handle_status_request(self.bucket_name, self.job_id)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['status'] == 'completed'
        assert response_body['completedAt'] == '2024-01-01T12:00:00Z'
        assert response_body['message'] == 'Analysis completed successfully'
    
    def test_handle_status_request_processing(self):
        """Test status request for processing job"""
        processing_data = {
            'jobId': self.job_id,
            'status': 'processing',
            'stage': 'rekognition_running',
            'startTime': '2024-01-01T11:55:00Z'
        }
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'processing/{self.job_id}.processing',
            Body=json.dumps(processing_data)
        )
        
        response = handle_status_request(self.bucket_name, self.job_id)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['status'] == 'processing'
        assert response_body['stage'] == 'rekognition_running'
        assert response_body['startedAt'] == '2024-01-01T11:55:00Z'


@mock_s3
class TestDownloadEndpoint:
    
    def setup_method(self):
        """Setup for each test"""
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.bucket_name = 'test-bucket'
        self.s3.create_bucket(Bucket=self.bucket_name)
        self.job_id = 'job-test-123'
    
    def test_handle_download_request_json_success(self):
        """Test successful JSON download request"""
        # Create completion marker
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/completed.json',
            Body=json.dumps({'jobId': self.job_id, 'status': 'completed'})
        )
        
        # Create JSON results file
        analysis_data = {'vehicle_counts': {'cars': 5}}
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/analysis.json',
            Body=json.dumps(analysis_data)
        )
        
        with patch('handler.generate_download_url') as mock_generate:
            mock_generate.return_value = 'https://s3.example.com/download-url'
            
            response = handle_download_request(self.bucket_name, self.job_id, 'json')
            
            assert response['statusCode'] == 200
            response_body = json.loads(response['body'])
            assert response_body['format'] == 'json'
            assert response_body['downloadUrl'] == 'https://s3.example.com/download-url'
            assert response_body['filename'] == f'vehicle_analysis_{self.job_id}.json'
    
    def test_handle_download_request_csv_success(self):
        """Test successful CSV download request"""
        # Create completion marker
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/completed.json',
            Body=json.dumps({'jobId': self.job_id, 'status': 'completed'})
        )
        
        # Create CSV results file
        csv_data = 'timestamp,vehicle_type,confidence\n5.0,cars,85.5'
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/detections.csv',
            Body=csv_data
        )
        
        with patch('handler.generate_download_url') as mock_generate:
            mock_generate.return_value = 'https://s3.example.com/download-url'
            
            response = handle_download_request(self.bucket_name, self.job_id, 'csv')
            
            assert response['statusCode'] == 200
            response_body = json.loads(response['body'])
            assert response_body['format'] == 'csv'
            assert response_body['filename'] == f'vehicle_detections_{self.job_id}.csv'
    
    def test_handle_download_request_invalid_format(self):
        """Test download request with invalid format"""
        response = handle_download_request(self.bucket_name, self.job_id, 'xml')
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'Invalid format' in response_body['error']
    
    def test_handle_download_request_job_not_completed(self):
        """Test download request for job that's not completed"""
        # Create processing marker (not completed)
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'processing/{self.job_id}.processing',
            Body=json.dumps({'status': 'processing'})
        )
        
        response = handle_download_request(self.bucket_name, self.job_id, 'json')
        
        assert response['statusCode'] == 404
        response_body = json.loads(response['body'])
        assert 'Results not available' in response_body['error']
    
    def test_handle_download_request_file_not_found(self):
        """Test download request when results file doesn't exist"""
        # Create completion marker but no results file
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=f'results/{self.job_id}/completed.json',
            Body=json.dumps({'jobId': self.job_id, 'status': 'completed'})
        )
        
        response = handle_download_request(self.bucket_name, self.job_id, 'json')
        
        assert response['statusCode'] == 404
        response_body = json.loads(response['body'])
        assert 'Results file not found' in response_body['error']


class TestUtilityFunctions:
    
    @mock_s3
    def test_generate_download_url_success(self):
        """Test successful download URL generation"""
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        # Put a test file
        s3.put_object(
            Bucket=bucket_name,
            Key='test-file.json',
            Body='{"test": "data"}'
        )
        
        url = generate_download_url(bucket_name, 'test-file.json', 'test.json', 'application/json')
        
        assert url is not None
        assert 'test-file.json' in url
        assert 'X-Amz-Expires' in url
    
    def test_create_success_response(self):
        """Test success response creation"""
        data = {'message': 'success', 'data': 123}
        response = create_success_response(data)
        
        assert response['statusCode'] == 200
        assert 'Content-Type' in response['headers']
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['message'] == 'success'
        assert body['data'] == 123
    
    def test_create_error_response(self):
        """Test error response creation"""
        response = create_error_response(400, 'Bad request')
        
        assert response['statusCode'] == 400
        assert 'Content-Type' in response['headers']
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['error'] == 'Bad request'
        assert 'timestamp' in body


@mock_s3
class TestEndToEndScenarios:
    
    def setup_method(self):
        """Setup for each test"""
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.bucket_name = 'test-bucket'
        self.s3.create_bucket(Bucket=self.bucket_name)
        self.job_id = 'job-test-123'
    
    def test_complete_workflow_success(self):
        """Test complete workflow from upload to results"""
        with patch.dict(os.environ, {'STORAGE_BUCKET_NAME': self.bucket_name}):
            
            # 1. Check status when job is just uploaded (pending)
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=f'uploads/{self.job_id}/test_video.mp4',
                Body=b'fake video'
            )
            
            event = {
                'httpMethod': 'GET',
                'resource': '/results/{jobId}/status',
                'pathParameters': {'jobId': self.job_id}
            }
            
            response = lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['status'] == 'pending'
            
            # 2. Check status when processing starts
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=f'processing/{self.job_id}.processing',
                Body=json.dumps({'status': 'processing', 'stage': 'rekognition_running'})
            )
            
            response = lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['status'] == 'processing'
            
            # 3. Check results when completed
            # Remove processing marker
            self.s3.delete_object(Bucket=self.bucket_name, Key=f'processing/{self.job_id}.processing')
            
            # Add completion marker and results
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=f'results/{self.job_id}/completed.json',
                Body=json.dumps({'jobId': self.job_id, 'status': 'completed'})
            )
            
            analysis_data = {
                'video_info': {'filename': 'test_video.mp4'},
                'vehicle_counts': {'cars': 10, 'trucks': 2, 'total_vehicles': 12}
            }
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=f'results/{self.job_id}/analysis.json',
                Body=json.dumps(analysis_data)
            )
            
            # Test full results endpoint
            event['resource'] = '/results/{jobId}'
            response = lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['status'] == 'completed'
            assert body['results']['vehicle_counts']['total_vehicles'] == 12
    
    def test_error_handling_workflow(self):
        """Test error handling throughout the workflow"""
        with patch.dict(os.environ, {'STORAGE_BUCKET_NAME': self.bucket_name}):
            
            # 1. Test job not found
            event = {
                'httpMethod': 'GET',
                'resource': '/results/{jobId}',
                'pathParameters': {'jobId': 'nonexistent-job'}
            }
            
            response = lambda_handler(event, None)
            assert response['statusCode'] == 404
            
            # 2. Test failed job
            error_data = {
                'jobId': self.job_id,
                'status': 'failed',
                'error': 'Video format not supported'
            }
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=f'errors/{self.job_id}/error.json',
                Body=json.dumps(error_data)
            )
            
            event['pathParameters']['jobId'] = self.job_id
            response = lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['status'] == 'failed'
            assert 'Video format not supported' in body['error']


if __name__ == '__main__':
    pytest.main([__file__])
