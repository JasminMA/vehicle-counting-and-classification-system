import json
import pytest
from moto import mock_s3
import boto3
from unittest.mock import patch, MagicMock
import os
import sys

# Add the upload-handler directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'upload-handler'))

from handler import lambda_handler, validate_file_parameters, generate_job_id, create_error_response


class TestUploadHandler:
    
    @mock_s3
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
            response = lambda_handler(event, None)
            
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
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'Missing request body' in response_body['error']
    
    def test_upload_handler_invalid_json(self):
        """Test error when request body contains invalid JSON"""
        event = {
            'body': 'invalid json'
        }
        
        response = lambda_handler(event, None)
        
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
        
        response = lambda_handler(event, None)
        
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
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'filesize' in response_body['error']
    
    @mock_s3
    def test_upload_handler_missing_bucket_env(self):
        """Test error when STORAGE_BUCKET_NAME environment variable is missing"""
        # Don't set STORAGE_BUCKET_NAME environment variable
        event = {
            'body': json.dumps({
                'filename': 'test_video.mp4',
                'filesize': 1000000
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'Configuration error' in response_body['error']


class TestValidateFileParameters:
    
    def test_validate_file_parameters_success(self):
        """Test successful file parameter validation"""
        result = validate_file_parameters('test_video.mp4', 1000000)
        assert result is None
    
    def test_validate_file_parameters_empty_filename(self):
        """Test validation failure for empty filename"""
        result = validate_file_parameters('', 1000000)
        assert result['statusCode'] == 400
        assert 'empty' in json.loads(result['body'])['error']
    
    def test_validate_file_parameters_long_filename(self):
        """Test validation failure for filename too long"""
        long_filename = 'a' * 256 + '.mp4'
        result = validate_file_parameters(long_filename, 1000000)
        assert result['statusCode'] == 400
        assert 'too long' in json.loads(result['body'])['error']
    
    def test_validate_file_parameters_invalid_extension(self):
        """Test validation failure for invalid file extension"""
        result = validate_file_parameters('test_video.txt', 1000000)
        assert result['statusCode'] == 400
        error_msg = json.loads(result['body'])['error']
        assert 'Unsupported file format' in error_msg
    
    def test_validate_file_parameters_file_too_large(self):
        """Test validation failure for file too large"""
        max_size = 8 * 1024 * 1024 * 1024  # 8GB
        result = validate_file_parameters('test_video.mp4', max_size + 1)
        assert result['statusCode'] == 400
        assert 'too large' in json.loads(result['body'])['error']
    
    def test_validate_file_parameters_invalid_size(self):
        """Test validation failure for invalid file size"""
        result = validate_file_parameters('test_video.mp4', 0)
        assert result['statusCode'] == 400
        assert 'Invalid file size' in json.loads(result['body'])['error']
    
    def test_validate_file_parameters_supported_formats(self):
        """Test that all supported formats are accepted"""
        supported_formats = ['mp4', 'mov', 'avi', 'mkv', 'webm']
        
        for format_ext in supported_formats:
            filename = f'test_video.{format_ext}'
            result = validate_file_parameters(filename, 1000000)
            assert result is None, f"Format {format_ext} should be supported"


class TestUtilityFunctions:
    
    def test_generate_job_id(self):
        """Test job ID generation"""
        job_id = generate_job_id()
        
        assert job_id.startswith('job-')
        assert len(job_id) > 10
        
        # Generate another ID and ensure they're different
        job_id2 = generate_job_id()
        assert job_id != job_id2
    
    def test_create_error_response(self):
        """Test error response creation"""
        response = create_error_response(400, "Test error message")
        
        assert response['statusCode'] == 400
        assert 'Content-Type' in response['headers']
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['error'] == "Test error message"
        assert 'timestamp' in body


if __name__ == '__main__':
    pytest.main([__file__])
