import pytest
import json
import boto3
from moto import mock_aws
from unittest.mock import patch
import os
import sys

# Add the upload-handler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'upload-handler'))

# Import from the upload-handler module
import handler as upload_handler_module


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
            response = upload_handler_module.lambda_handler(event, None)

            # Assertions
            assert response['statusCode'] == 200
            response_body = json.loads(response['body'])
            assert 'jobId' in response_body
            assert 'uploadUrl' in response_body
            assert response_body['expiresIn'] == 3600
            assert response_body['jobId'].startswith('job-')
    
    def test_upload_handler_missing_body(self):
        """Test error when request body is missing"""
        event = {}

        response = upload_handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'Missing request body' in response_body['error']
    
    def test_upload_handler_invalid_json(self):
        """Test error when request body contains invalid JSON"""
        event = {
            'body': 'invalid json'
        }

        response = upload_handler_module.lambda_handler(event, None)

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

        response = upload_handler_module.lambda_handler(event, None)

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

        response = upload_handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'filesize' in response_body['error']
    
    @mock_aws
    def test_upload_handler_missing_bucket_env(self):
        """Test error when STORAGE_BUCKET_NAME environment variable is missing"""
        # Don't set STORAGE_BUCKET_NAME environment variable
        event = {
            'body': json.dumps({
                'filename': 'test_video.mp4',
                'filesize': 1000000
            })
        }

        response = upload_handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 500
        response_body = json.loads(response['body'])
        assert 'error' in response_body
        assert 'Configuration error' in response_body['error']


class TestValidateFileParameters:
    
    def test_validate_file_parameters_success(self):
        """Test successful file parameter validation"""
        result = upload_handler_module.validate_file_parameters('test_video.mp4', 1000000)
        assert result is None  # No error
    
    def test_validate_file_parameters_empty_filename(self):
        """Test validation failure for empty filename"""
        result = upload_handler_module.validate_file_parameters('', 1000000)
        assert result is not None
        assert result['statusCode'] == 400
    
    def test_validate_file_parameters_long_filename(self):
        """Test validation failure for filename too long"""
        long_filename = 'a' * 256 + '.mp4'
        result = upload_handler_module.validate_file_parameters(long_filename, 1000000)
        assert result is not None
        assert result['statusCode'] == 400
    
    def test_validate_file_parameters_invalid_extension(self):
        """Test validation failure for invalid file extension"""
        result = upload_handler_module.validate_file_parameters('test_video.txt', 1000000)
        assert result is not None
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert 'Unsupported file format' in response_body['error']
    
    def test_validate_file_parameters_file_too_large(self):
        """Test validation failure for file too large"""
        max_size = 8 * 1024 * 1024 * 1024  # 8GB
        result = upload_handler_module.validate_file_parameters('test_video.mp4', max_size + 1)
        assert result is not None
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert 'File too large' in response_body['error']
    
    def test_validate_file_parameters_invalid_size(self):
        """Test validation failure for invalid file size"""
        result = upload_handler_module.validate_file_parameters('test_video.mp4', 0)
        assert result is not None
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert 'Invalid file size' in response_body['error']
    
    def test_validate_file_parameters_supported_formats(self):
        """Test that all supported formats are accepted"""
        supported_formats = ['mp4', 'mov', 'avi', 'mkv', 'webm']

        for format_ext in supported_formats:
            filename = f'test_video.{format_ext}'
            result = upload_handler_module.validate_file_parameters(filename, 1000000)
            assert result is None, f"Format {format_ext} should be supported"


class TestUtilityFunctions:
    
    def test_generate_job_id(self):
        """Test job ID generation"""
        job_id = upload_handler_module.generate_job_id()
        
        assert job_id.startswith('job-')
        assert len(job_id) > 10  # Should be reasonable length
        
        # Generate another and ensure they're different
        job_id2 = upload_handler_module.generate_job_id()
        assert job_id != job_id2
    
    def test_create_error_response(self):
        """Test error response creation"""
        response = upload_handler_module.create_error_response(400, 'Test error')
        
        assert response['statusCode'] == 400
        assert 'Content-Type' in response['headers']
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['error'] == 'Test error'
        assert 'timestamp' in body
    
    def test_get_allowed_formats(self):
        """Test getting allowed formats"""
        formats = upload_handler_module.get_allowed_formats()
        expected_formats = ['mp4', 'mov', 'avi', 'mkv', 'webm']
        
        assert isinstance(formats, list)
        assert all(fmt in formats for fmt in expected_formats)
    
    def test_get_max_file_size(self):
        """Test getting maximum file size"""
        max_size = upload_handler_module.get_max_file_size()
        expected_size = 8 * 1024 * 1024 * 1024  # 8GB
        
        assert max_size == expected_size
    
    @mock_aws
    def test_generate_presigned_upload_url(self):
        """Test generating presigned upload URL"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        url = upload_handler_module.generate_presigned_upload_url(
            bucket_name=bucket_name,
            s3_key='uploads/job-123/test.mp4',
            expiration=3600
        )
        
        assert url is not None
        assert bucket_name in url
        assert 'uploads/job-123/test.mp4' in url
        assert 'Expires=' in url  # AWS uses 'Expires=' not 'X-Amz-Expires'


if __name__ == '__main__':
    pytest.main([__file__])
