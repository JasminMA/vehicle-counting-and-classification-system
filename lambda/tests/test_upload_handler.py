import json
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
import os
import sys
import importlib.util

# Mock AWS environment for testing
@pytest.fixture(autouse=True)
def aws_credentials():
    """Mock AWS credentials for testing"""
    with patch.dict(os.environ, {
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_SECURITY_TOKEN': 'testing',
        'AWS_SESSION_TOKEN': 'testing',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }):
        yield

# Load upload handler module directly to avoid path conflicts
def load_upload_handler():
    handler_path = os.path.join(os.path.dirname(__file__), '..', 'upload-handler', 'handler.py')
    spec = importlib.util.spec_from_file_location("upload_handler", handler_path)
    upload_handler = importlib.util.module_from_spec(spec)
    
    # Mock AWS clients before loading
    with mock_aws():
        spec.loader.exec_module(upload_handler)
    return upload_handler

upload_handler = load_upload_handler()


class TestUploadHandler:
    
    @mock_aws
    def test_upload_handler_success(self):
        """Test successful upload URL generation"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        # Setup environment
        with patch.dict(os.environ, {'STORAGE_BUCKET_NAME': bucket_name}):
            # Prepare test event
            event = {
                'body': json.dumps({
                    'filename': 'test_video.mp4',
                    'filesize': 1000000
                })
            }
            
            # Call lambda handler
            response = upload_handler.lambda_handler(event, None)
            
            # Assertions
            assert response['statusCode'] == 200
            
            response_body = json.loads(response['body'])
            assert 'jobId' in response_body
            assert 'uploadUrl' in response_body
            assert 'expiresIn' in response_body
            assert response_body['expiresIn'] == 3600
            assert response_body['jobId'].startswith('job-')

    def test_upload_handler_missing_body(self):
        """Test error when request body is missing"""
        event = {}
        
        response = upload_handler.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body

    def test_upload_handler_invalid_json(self):
        """Test error when request body contains invalid JSON"""
        event = {
            'body': 'invalid json'
        }
        
        response = upload_handler.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'Invalid JSON' in response_body['error']

    def test_upload_handler_missing_filename(self):
        """Test error when filename is missing"""
        event = {
            'body': json.dumps({
                'filesize': 1000000
            })
        }
        
        response = upload_handler.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'filename' in response_body['error']

    def test_upload_handler_missing_filesize(self):
        """Test error when filesize is missing"""
        event = {
            'body': json.dumps({
                'filename': 'test_video.mp4'
            })
        }
        
        response = upload_handler.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'filesize' in response_body['error']


class TestUtilityFunctions:
    
    def test_create_error_response(self):
        """Test error response creation"""
        response = upload_handler.create_error_response(400, "Test error message")
        
        assert response['statusCode'] == 400
        assert 'Content-Type' in response['headers']
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['error'] == "Test error message"
        assert 'timestamp' in body

    def test_get_allowed_formats(self):
        """Test getting allowed file formats"""
        formats = upload_handler.get_allowed_formats()
        
        assert isinstance(formats, list)
        assert 'mp4' in formats
        assert 'mov' in formats

    def test_get_max_file_size(self):
        """Test getting maximum file size"""
        max_size = upload_handler.get_max_file_size()
        
        assert max_size == 8 * 1024 * 1024 * 1024  # 8GB
        assert isinstance(max_size, int)

    def test_validate_file_parameters_success(self):
        """Test successful file parameter validation"""
        result = upload_handler.validate_file_parameters('test_video.mp4', 1000000)
        assert result is None

    def test_validate_file_parameters_invalid_extension(self):
        """Test validation failure for invalid file extension"""
        result = upload_handler.validate_file_parameters('test_video.txt', 1000000)
        assert result['statusCode'] == 400
        error_msg = json.loads(result['body'])['error']
        assert 'Unsupported file format' in error_msg

    def test_validate_file_parameters_file_too_large(self):
        """Test validation failure for file too large"""
        max_size = upload_handler.get_max_file_size()
        result = upload_handler.validate_file_parameters('test_video.mp4', max_size + 1)
        assert result['statusCode'] == 400
        assert 'too large' in json.loads(result['body'])['error']

    def test_generate_job_id(self):
        """Test job ID generation"""
        job_id = upload_handler.generate_job_id()
        
        assert job_id.startswith('job-')
        assert len(job_id) > 10
        
        # Generate another ID and ensure they're different
        job_id2 = upload_handler.generate_job_id()
        assert job_id != job_id2


if __name__ == '__main__':
    pytest.main([__file__])
