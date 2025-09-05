import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { CoreStack } from '../lib/core-stack';

describe('Core Infrastructure Tests', () => {
  let app: cdk.App;
  let stack: CoreStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    stack = new CoreStack(app, 'TestCoreStack', {
      environment: 'test',
      env: {
        account: '123456789012',
        region: 'us-east-1',
      },
    });
    template = Template.fromStack(stack);
  });

  test('Creates S3 Storage Bucket', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketName: 'vehicle-analysis-storage-test-123456789012',
      VersioningConfiguration: {
        Status: 'Suspended',
      },
    });
  });

  test('Creates S3 Web Bucket with Website Configuration', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketName: 'vehicle-analysis-ui-test-123456789012',
      WebsiteConfiguration: {
        IndexDocument: 'index.html',
        ErrorDocument: 'error.html',
      },
    });
  });

  test('Creates Lambda Execution Role with Correct Permissions', () => {
    template.hasResourceProperties('AWS::IAM::Role', {
      RoleName: 'VehicleAnalysis-LambdaExecution-test',
      AssumeRolePolicyDocument: {
        Statement: [
          {
            Effect: 'Allow',
            Principal: {
              Service: 'lambda.amazonaws.com',
            },
            Action: 'sts:AssumeRole',
          },
        ],
      },
    });
  });

  test('Creates Rekognition Service Role', () => {
    template.hasResourceProperties('AWS::IAM::Role', {
      RoleName: 'VehicleAnalysis-RekognitionService-test',
      AssumeRolePolicyDocument: {
        Statement: [
          {
            Effect: 'Allow',
            Principal: {
              Service: 'rekognition.amazonaws.com',
            },
            Action: 'sts:AssumeRole',
          },
        ],
      },
    });
  });

  test('Storage Bucket has Lifecycle Rules', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      LifecycleConfiguration: {
        Rules: [
          {
            Id: 'DeleteOldUploads',
            Status: 'Enabled',
            Prefix: 'uploads/',
            ExpirationInDays: 30,
          },
          {
            Id: 'DeleteOldProcessing',
            Status: 'Enabled',
            Prefix: 'processing/',
            ExpirationInDays: 7,
          },
          {
            Id: 'DeleteOldResults',
            Status: 'Enabled',
            Prefix: 'results/',
            ExpirationInDays: 90,
          },
          {
            Id: 'DeleteOldErrors',
            Status: 'Enabled',
            Prefix: 'errors/',
            ExpirationInDays: 30,
          },
        ],
      },
    });
  });

  test('Storage Bucket has CORS Configuration', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      CorsConfiguration: {
        CorsRules: [
          {
            AllowedMethods: ['GET', 'POST', 'PUT', 'DELETE'],
            AllowedOrigins: ['*'],
            AllowedHeaders: ['*'],
            MaxAge: 3000,
          },
        ],
      },
    });
  });

  test('Creates Required CloudFormation Outputs', () => {
    template.hasOutput('StorageBucketName', {});
    template.hasOutput('WebBucketName', {});
    template.hasOutput('WebsiteURL', {});
    template.hasOutput('LambdaExecutionRoleArn', {});
    template.hasOutput('RekognitionServiceRoleArn', {});
  });

  test('All Resources have Correct Tags', () => {
    // Check that resources are tagged
    template.hasResourceProperties('AWS::S3::Bucket', {
      Tags: [
        {
          Key: 'Project',
          Value: 'VehicleAnalysis',
        },
        {
          Key: 'Environment',
          Value: 'test',
        },
        {
          Key: 'Stack',
          Value: 'Core',
        },
      ],
    });
  });

  test('Stack Synthesis Succeeds', () => {
    // This test verifies the stack can be synthesized without errors
    expect(template).toBeDefined();
    expect(Object.keys(template.findResources('AWS::S3::Bucket')).length).toBeGreaterThan(0);
    expect(Object.keys(template.findResources('AWS::IAM::Role')).length).toBeGreaterThan(0);
  });
});
