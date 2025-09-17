import json
import pytest
from moto import mock_aws
import boto3
from unittest.mock import patch, MagicMock
import os
import sys
import importlib.util

# Load upload handler module directly to avoid path conflicts
def load_upload_handler():
    handler_path = os.path.join(os.path.dirname(__file__), '..', 'upload-handler', 'handler.py')
    spec = importlib.util.spec_from_file_location("upload_handler", handler_path)
    upload_handler = importlib.util.module_from_spec(spec)
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


if __name__ == '__main__':
    pytest.main([__file__])
