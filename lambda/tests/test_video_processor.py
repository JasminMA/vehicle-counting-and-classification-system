import json
import pytest
from moto import mock_aws
import boto3
from unittest.mock import patch, MagicMock
import os
import sys
import importlib.util

# Load video processor module directly to avoid path conflicts
def load_video_processor():
    handler_path = os.path.join(os.path.dirname(__file__), '..', 'video-processor', 'handler.py')
    spec = importlib.util.spec_from_file_location("video_processor", handler_path)
    video_processor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(video_processor)
    return video_processor

video_processor = load_video_processor()


class TestVideoProcessor:
    
    def test_extract_job_id_from_key_success(self):
        """Test successful job ID extraction from S3 key"""
        s3_key = "uploads/job-20241205-143022-abc123/test_video.mp4"
        job_id = video_processor.extract_job_id_from_key(s3_key)
        
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
            job_id = video_processor.extract_job_id_from_key(key)
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
            assert video_processor.is_supported_video_file(file_path) == True
        
        for file_path in unsupported_files:
            assert video_processor.is_supported_video_file(file_path) == False
    
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
        
        assert video_processor.is_valid_s3_record(valid_record) == True
        
        for record in invalid_records:
            assert video_processor.is_valid_s3_record(record) == False

    @mock_aws
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
        result = video_processor.create_processing_marker(bucket_name, job_id, video_metadata)
        
        assert result == True
        
        # Verify marker was created
        marker_key = f"processing/{job_id}.processing"
        response = s3.get_object(Bucket=bucket_name, Key=marker_key)
        marker_data = json.loads(response['Body'].read().decode('utf-8'))
        
        assert marker_data['jobId'] == job_id
        assert marker_data['status'] == 'processing'
        assert marker_data['videoMetadata'] == video_metadata

    @mock_aws
    def test_create_error_marker(self):
        """Test error marker creation"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        job_id = 'job-test-123'
        error_message = 'Test error message'
        
        # Create error marker
        result = video_processor.create_error_marker(bucket_name, job_id, error_message)
        
        assert result == True
        
        # Verify error marker was created
        error_key = f"errors/{job_id}/error.json"
        response = s3.get_object(Bucket=bucket_name, Key=error_key)
        error_data = json.loads(response['Body'].read().decode('utf-8'))
        
        assert error_data['jobId'] == job_id
        assert error_data['status'] == 'failed'
        assert error_data['error'] == error_message


if __name__ == '__main__':
    pytest.main([__file__])
