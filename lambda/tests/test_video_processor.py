import json
import pytest
from moto import mock_s3, mock_sns
import boto3
from unittest.mock import patch, MagicMock
import os
import sys

# Add the video-processor directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'video-processor'))

from handler import (
    lambda_handler, 
    extract_job_id_from_key, 
    is_supported_video_file,
    is_valid_s3_record,
    create_processing_marker,
    create_error_marker
)


class TestVideoProcessor:
    
    def test_extract_job_id_from_key_success(self):
        """Test successful job ID extraction from S3 key"""
        s3_key = "uploads/job-20241205-143022-abc123/test_video.mp4"
        job_id = extract_job_id_from_key(s3_key)
        
        assert job_id == "job-20241205-143022-abc123"
    
    def test_extract_job_id_from_key_invalid_pattern(self):
        """Test job ID extraction with invalid key pattern"""
        invalid_keys = [
            "invalid/path/video.mp4",
            "uploads/",
            "uploads",
            "results/job-123/analysis.json"
        ]
        
        for key in invalid_keys:
            job_id = extract_job_id_from_key(key)
            assert job_id is None
    
    def test_is_supported_video_file(self):
        """Test video file format validation"""
        supported_files = [
            "uploads/job-123/video.mp4",
            "uploads/job-123/video.MOV",
            "uploads/job-123/video.avi",
            "uploads/job-123/video.mkv",
            "uploads/job-123/video.webm"
        ]
        
        unsupported_files = [
            "uploads/job-123/document.pdf",
            "uploads/job-123/image.jpg",
            "uploads/job-123/audio.mp3",
            "uploads/job-123/video.txt"
        ]
        
        for file_path in supported_files:
            assert is_supported_video_file(file_path) == True
        
        for file_path in unsupported_files:
            assert is_supported_video_file(file_path) == False
    
    def test_is_valid_s3_record(self):
        """Test S3 record validation"""
        valid_record = {
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'uploads/job-123/video.mp4'}
            }
        }
        
        invalid_records = [
            {},
            {'s3': {}},
            {'s3': {'bucket': {}}},
            {'s3': {'bucket': {'name': 'test'}}},
            {'s3': {'object': {'key': 'test'}}}
        ]
        
        assert is_valid_s3_record(valid_record) == True
        
        for record in invalid_records:
            assert is_valid_s3_record(record) == False
    
    @mock_s3
    def test_create_processing_marker(self):
        """Test processing marker creation"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        job_id = 'job-test-123'
        video_metadata = {
            'size': 1000000,
            'contentType': 'video/mp4'
        }
        
        # Create processing marker
        result = create_processing_marker(bucket_name, job_id, video_metadata)
        
        assert result == True
        
        # Verify marker was created
        marker_key = f"processing/{job_id}.processing"
        response = s3.get_object(Bucket=bucket_name, Key=marker_key)
        marker_data = json.loads(response['Body'].read().decode('utf-8'))
        
        assert marker_data['jobId'] == job_id
        assert marker_data['status'] == 'processing'
        assert marker_data['videoMetadata'] == video_metadata
    
    @mock_s3
    def test_create_error_marker(self):
        """Test error marker creation"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        job_id = 'job-test-123'
        error_message = 'Test error message'
        
        # Create error marker
        result = create_error_marker(bucket_name, job_id, error_message)
        
        assert result == True
        
        # Verify error marker was created
        error_key = f"errors/{job_id}/error.json"
        response = s3.get_object(Bucket=bucket_name, Key=error_key)
        error_data = json.loads(response['Body'].read().decode('utf-8'))
        
        assert error_data['jobId'] == job_id
        assert error_data['status'] == 'failed'
        assert error_data['error'] == error_message
    
    @mock_s3
    @patch('handler.rekognition')
    def test_lambda_handler_success(self, mock_rekognition):
        """Test successful lambda handler execution"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        # Create test video object
        video_key = 'uploads/job-test-123/video.mp4'
        s3.put_object(
            Bucket=bucket_name,
            Key=video_key,
            Body=b'fake video content',
            ContentType='video/mp4'
        )
        
        # Mock Rekognition response
        mock_rekognition.start_label_detection.return_value = {
            'JobId': 'rekognition-job-456'
        }
        
        # Prepare S3 event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': bucket_name},
                        'object': {'key': video_key}
                    }
                }
            ]
        }
        
        # Set environment variables
        with patch.dict(os.environ, {
            'SNS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:test-topic',
            'REKOGNITION_ROLE_ARN': 'arn:aws:iam::123456789012:role/test-role'
        }):
            # Call lambda handler
            response = lambda_handler(event, None)
            
            # Assertions
            assert response['statusCode'] == 200
            response_body = json.loads(response['body'])
            assert 'Processed 1 video(s)' in response_body['message']
    
    def test_lambda_handler_invalid_event(self):
        """Test lambda handler with invalid event"""
        event = {
            'Records': [
                {
                    'invalid': 'record'
                }
            ]
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200  # Should handle gracefully
        response_body = json.loads(response['body'])
        assert 'Processed 0 video(s)' in response_body['message']
    
    @mock_s3
    def test_lambda_handler_unsupported_file_format(self):
        """Test lambda handler with unsupported file format"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        # Prepare S3 event with unsupported file
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': bucket_name},
                        'object': {'key': 'uploads/job-test-123/document.pdf'}
                    }
                }
            ]
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        
        # Verify error marker was created
        error_key = "errors/job-test-123/error.json"
        error_response = s3.get_object(Bucket=bucket_name, Key=error_key)
        error_data = json.loads(error_response['Body'].read().decode('utf-8'))
        
        assert error_data['error'] == 'Unsupported video format'


if __name__ == '__main__':
    pytest.main([__file__])
