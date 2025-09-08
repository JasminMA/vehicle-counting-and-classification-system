import pytest
import json
import boto3
from moto import mock_aws
from unittest.mock import patch
import os
import sys

# Add the video-processor directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'video-processor'))

# Import from the video-processor module
import handler as video_processor_module


class TestVideoProcessor:
    
    def test_extract_job_id_from_key_success(self):
        """Test successful job ID extraction from S3 key"""
        s3_key = "uploads/job-20241205-143022-abc123/test_video.mp4"
        job_id = video_processor_module.extract_job_id_from_key(s3_key)
        assert job_id == "job-20241205-143022-abc123"
        
        # Test another format
        s3_key2 = "uploads/job-test-123/video.mov"
        job_id2 = video_processor_module.extract_job_id_from_key(s3_key2)
        assert job_id2 == "job-test-123"
    
    def test_extract_job_id_from_key_invalid_pattern(self):
        """Test job ID extraction with invalid key pattern"""
        invalid_keys = [
            "invalid/path/video.mp4",
            "uploads/",
            "uploads",
            "results/job-123/analysis.json"
        ]

        for key in invalid_keys:
            job_id = video_processor_module.extract_job_id_from_key(key)
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
            assert video_processor_module.is_supported_video_file(file_path) == True
        
        for file_path in unsupported_files:
            assert video_processor_module.is_supported_video_file(file_path) == False
    
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

        assert video_processor_module.is_valid_s3_record(valid_record) == True
        
        for record in invalid_records:
            assert video_processor_module.is_valid_s3_record(record) == False
    
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
        result = video_processor_module.create_processing_marker(bucket_name, job_id, video_metadata)
        
        assert result is True
        
        # Verify marker was created
        response = s3.get_object(Bucket=bucket_name, Key=f'processing/{job_id}.processing')
        marker_data = json.loads(response['Body'].read().decode('utf-8'))
        assert marker_data['jobId'] == job_id
        assert marker_data['status'] == 'processing'
        assert marker_data['stage'] == 'rekognition_started'
    
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
        result = video_processor_module.create_error_marker(bucket_name, job_id, error_message)
        
        assert result is True
        
        # Verify error marker was created
        response = s3.get_object(Bucket=bucket_name, Key=f'errors/{job_id}/error.json')
        error_data = json.loads(response['Body'].read().decode('utf-8'))
        assert error_data['jobId'] == job_id
        assert error_data['status'] == 'failed'
        assert error_data['error'] == error_message
    
    @mock_aws
    def test_get_video_metadata(self):
        """Test getting video metadata from S3"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        # Upload a test file
        s3_key = 'uploads/job-123/test.mp4'
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=b'fake video content',
            ContentType='video/mp4'
        )
        
        metadata = video_processor_module.get_video_metadata(bucket_name, s3_key)
        
        assert metadata is not None
        assert metadata['size'] > 0
        assert metadata['contentType'] == 'video/mp4'
        assert 'lastModified' in metadata
        assert 'etag' in metadata
    
    @mock_aws
    def test_lambda_handler_success(self):
        """Test successful lambda handler execution"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        # Upload a test video file
        s3_key = 'uploads/job-test-123/test_video.mp4'
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=b'fake video content',
            ContentType='video/mp4'
        )
        
        # Prepare S3 event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': bucket_name},
                        'object': {'key': s3_key}
                    }
                }
            ]
        }
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'SNS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:test-topic',
            'REKOGNITION_ROLE_ARN': 'arn:aws:iam::123456789012:role/RekognitionServiceRole'
        }):
            with patch.object(video_processor_module, 'start_rekognition_analysis', return_value='rekognition-job-123'):
                response = video_processor_module.lambda_handler(event, None)
                
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

        response = video_processor_module.lambda_handler(event, None)

        assert response['statusCode'] == 200  # Should handle gracefully
        response_body = json.loads(response['body'])
        assert 'Processed 1 video(s)' in response_body['message']
    
    @mock_aws
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

        response = video_processor_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert 'Processed 1 video(s)' in response_body['message']
    
    def test_start_rekognition_analysis(self):
        """Test starting Rekognition analysis"""
        bucket_name = 'test-bucket'
        s3_key = 'uploads/job-123/video.mp4'
        job_id = 'job-123'
        
        mock_response = {'JobId': 'rekognition-job-123'}
        
        # Mock the rekognition client at module level
        with patch.object(video_processor_module.rekognition, 'start_label_detection', return_value=mock_response):
            with patch.dict(os.environ, {
                'SNS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:test-topic',
                'REKOGNITION_ROLE_ARN': 'arn:aws:iam::123456789012:role/RekognitionServiceRole'
            }):
                rekognition_job_id = video_processor_module.start_rekognition_analysis(
                    bucket_name, s3_key, job_id
                )
                
                assert rekognition_job_id == 'rekognition-job-123'
    
    def test_start_rekognition_analysis_missing_env(self):
        """Test starting Rekognition analysis with missing environment variables"""
        bucket_name = 'test-bucket'
        s3_key = 'uploads/job-123/video.mp4'
        job_id = 'job-123'
        
        # Don't set environment variables
        rekognition_job_id = video_processor_module.start_rekognition_analysis(
            bucket_name, s3_key, job_id
        )
        
        assert rekognition_job_id is None
    
    @mock_aws
    def test_update_processing_marker(self):
        """Test updating processing marker with Rekognition job ID"""
        # Setup mock S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        job_id = 'job-test-123'
        
        # Create initial processing marker
        initial_data = {
            'jobId': job_id,
            'status': 'processing',
            'stage': 'rekognition_started'
        }
        s3.put_object(
            Bucket=bucket_name,
            Key=f'processing/{job_id}.processing',
            Body=json.dumps(initial_data),
            ContentType='application/json'
        )
        
        # Update with Rekognition job ID
        rekognition_job_id = 'rekognition-123'
        result = video_processor_module.update_processing_marker(bucket_name, job_id, rekognition_job_id)
        
        assert result is True
        
        # Verify update
        response = s3.get_object(Bucket=bucket_name, Key=f'processing/{job_id}.processing')
        updated_data = json.loads(response['Body'].read().decode('utf-8'))
        assert updated_data['rekognitionJobId'] == rekognition_job_id
        assert updated_data['stage'] == 'rekognition_running'
        assert 'lastUpdated' in updated_data


if __name__ == '__main__':
    pytest.main([__file__])
