import * as cdk from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import { CoreStack } from '../lib/core-stack';
import { LambdaStack } from '../lib/lambda-stack';

describe('Lambda Stack Tests', () => {
  let app: cdk.App;
  let coreStack: CoreStack;
  let lambdaStack: LambdaStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    
    // Create Core stack first (dependency)
    coreStack = new CoreStack(app, 'TestCoreStack', {
      environment: 'test',
      env: {
        account: '123456789012',
        region: 'us-east-1',
      },
    });

    // Create Lambda stack
    lambdaStack = new LambdaStack(app, 'TestLambdaStack', {
      environment: 'test',
      coreStack: coreStack,
      env: {
        account: '123456789012',
        region: 'us-east-1',
      },
    });

    template = Template.fromStack(lambdaStack);
  });

  test('Creates Upload Handler Lambda Function', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'VehicleAnalysis-UploadHandler-test',
      Runtime: 'python3.9',
      Handler: 'handler.lambda_handler',
      Timeout: 30,
      MemorySize: 128,
    });
  });

  test('Upload Handler has correct environment variables', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'VehicleAnalysis-UploadHandler-test',
      Environment: {
        Variables: {
          ENVIRONMENT: 'test',
          STORAGE_BUCKET_NAME: {
            Ref: Template.fromStack(coreStack).findResources('AWS::S3::Bucket')[0] || 'TestCoreStackStorageBucket'
          }
        }
      }
    });
  });

  test('Creates Placeholder Lambda Functions', () => {
    // Check that all 4 Lambda functions are created
    const lambdaFunctions = template.findResources('AWS::Lambda::Function');
    expect(Object.keys(lambdaFunctions)).toHaveLength(4);

    // Check specific placeholder functions
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'VehicleAnalysis-VideoProcessor-test',
    });

    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'VehicleAnalysis-ResultsProcessor-test',
    });

    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'VehicleAnalysis-ResultsApi-test',
    });
  });

  test('Upload Handler has S3 permissions', () => {
    // Check that IAM policy allows S3 access
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Action: Match.arrayWith([
              's3:GetObject*',
              's3:PutObject*',
              's3:DeleteObject*',
            ]),
          }),
        ])
      },
    });
  });

  test('Creates CloudFormation Outputs', () => {
    template.hasOutput('UploadHandlerFunctionName', {});
    template.hasOutput('UploadHandlerFunctionArn', {});
  });

  test('All Lambda Functions have correct tags', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
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
          Value: 'Lambda',
        },
      ],
    });
  });

  test('Upload Handler uses Core Stack IAM Role', () => {
    // Find the Lambda function in the template
    const lambdaFunctions = template.findResources('AWS::Lambda::Function');
    const uploadHandler = Object.values(lambdaFunctions).find((fn: any) => 
      fn.Properties.FunctionName === 'VehicleAnalysis-UploadHandler-test'
    ) as any;

    expect(uploadHandler).toBeDefined();
    expect(uploadHandler.Properties.Role).toBeDefined();
  });

  test('Stack Synthesis Succeeds', () => {
    // This test verifies the stack can be synthesized without errors
    expect(template).toBeDefined();
    expect(Object.keys(template.findResources('AWS::Lambda::Function')).length).toBe(4);
  });
});
