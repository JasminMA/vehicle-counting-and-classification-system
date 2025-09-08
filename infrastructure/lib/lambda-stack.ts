import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';
import { CoreStack } from './core-stack';

export interface LambdaStackProps extends cdk.StackProps {
  environment: string;
  coreStack: CoreStack;
}

export class LambdaStack extends cdk.Stack {
  public readonly storageBucket: s3.Bucket;
  public readonly lambdaExecutionRole: iam.Role;
  public readonly uploadHandler: lambda.Function;
  public readonly videoProcessor: lambda.Function;
  public readonly resultsProcessor: lambda.Function;
  public readonly resultsApi: lambda.Function;

  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    const { environment, coreStack } = props;

    // S3 bucket for videos and results with organized folder structure
    // Moved here from Core stack to avoid circular dependencies
    this.storageBucket = new s3.Bucket(this, 'StorageBucket', {
      bucketName: `vehicle-analysis-storage-${environment}-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev/testing - change for production
      autoDeleteObjects: true, // For dev/testing - change for production
      versioned: false,
      lifecycleRules: [
        {
          id: 'DeleteOldUploads',
          enabled: true,
          prefix: 'uploads/',
          expiration: cdk.Duration.days(30),
        },
        {
          id: 'DeleteOldProcessing',
          enabled: true,
          prefix: 'processing/',
          expiration: cdk.Duration.days(7),
        },
        {
          id: 'DeleteOldResults',
          enabled: true,
          prefix: 'results/',
          expiration: cdk.Duration.days(90),
        },
        {
          id: 'DeleteOldErrors',
          enabled: true,
          prefix: 'errors/',
          expiration: cdk.Duration.days(30),
        },
      ],
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.POST,
            s3.HttpMethods.PUT,
            s3.HttpMethods.DELETE,
          ],
          allowedOrigins: ['*'], // Will be restricted later to specific domain
          allowedHeaders: ['*'],
          maxAge: 3000,
        },
      ],
    });

    // Note: S3 access policy will be added after bucket creation
    // to avoid circular dependencies

    // Create Lambda execution role in this stack to avoid circular dependencies
    this.lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      roleName: `VehicleAnalysis-LambdaExecution-Lambda-${environment}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        RekognitionAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'rekognition:StartLabelDetection',
                'rekognition:GetLabelDetection',
                'rekognition:DescribeCollection',
              ],
              resources: ['*'],
            }),
            // Add iam:PassRole permission to pass Rekognition service role
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['iam:PassRole'],
              resources: [`arn:aws:iam::${this.account}:role/VehicleAnalysis-RekognitionService-${environment}`],
              conditions: {
                StringEquals: {
                  'iam:PassedToService': 'rekognition.amazonaws.com'
                }
              }
            }),
          ],
        }),
        SNSAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'sns:Publish',
                'sns:Subscribe',
                'sns:Unsubscribe',
              ],
              resources: [`arn:aws:sns:${this.region}:${this.account}:*`],
            }),
          ],
        }),
      },
    });

    // Grant S3 access to the execution role
    this.storageBucket.grantReadWrite(this.lambdaExecutionRole);

    // Upload Handler Lambda
    this.uploadHandler = new lambda.Function(this, 'UploadHandler', {
      functionName: `VehicleAnalysis-UploadHandler-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/upload-handler'),
      timeout: cdk.Duration.seconds(30),
      memorySize: 128,
      role: this.lambdaExecutionRole,
      environment: {
        STORAGE_BUCKET_NAME: this.storageBucket.bucketName,
        ENVIRONMENT: environment,
      },
      description: `Upload Handler Lambda for Vehicle Analysis - ${environment}`,
    });

    // S3 permissions are granted through the IAM role

    // Video Processor Lambda
    this.videoProcessor = new lambda.Function(this, 'VideoProcessor', {
      functionName: `VehicleAnalysis-VideoProcessor-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/video-processor'),
      timeout: cdk.Duration.minutes(5),
      memorySize: 256,
      role: this.lambdaExecutionRole,
      environment: {
        SNS_TOPIC_ARN: coreStack.rekognitionCompletionTopic.topicArn,
        REKOGNITION_ROLE_ARN: coreStack.rekognitionServiceRole.roleArn,
        ENVIRONMENT: environment,
      },
      description: `Video Processor Lambda for Vehicle Analysis - ${environment}`,
    });

    // Permissions are granted through the IAM role
    coreStack.rekognitionCompletionTopic.grantPublish(this.videoProcessor);
    
    // Note: Rekognition permissions are now included in the main IAM role

    // Configure event notifications here without circular dependencies
    this.storageBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.videoProcessor),
      {
        prefix: 'uploads/',
        suffix: '.mp4',
      }
    );
    
    // Also trigger for other video formats
    const videoExtensions = ['.mov', '.avi', '.mkv', '.webm'];
    videoExtensions.forEach(ext => {
      this.storageBucket.addEventNotification(
        s3.EventType.OBJECT_CREATED,
        new s3n.LambdaDestination(this.videoProcessor),
        {
          prefix: 'uploads/',
          suffix: ext,
        }
      );
    });

    // Results Processor Lambda
    this.resultsProcessor = new lambda.Function(this, 'ResultsProcessor', {
      functionName: `VehicleAnalysis-ResultsProcessor-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/results-processor'),
      timeout: cdk.Duration.minutes(10),
      memorySize: 512,
      role: this.lambdaExecutionRole,
      environment: {
        STORAGE_BUCKET_NAME: this.storageBucket.bucketName,
        ENVIRONMENT: environment,
      },
      description: `Results Processor Lambda for Vehicle Analysis - ${environment}`,
    });

    // Permissions are granted through the IAM role
    // Note: Rekognition permissions are now included in the main IAM role

    // Add SNS trigger for Results Processor
    coreStack.rekognitionCompletionTopic.addSubscription(
      new snsSubscriptions.LambdaSubscription(this.resultsProcessor)
    );

    // Results API Lambda
    this.resultsApi = new lambda.Function(this, 'ResultsApi', {
      functionName: `VehicleAnalysis-ResultsApi-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/results-api'),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      role: this.lambdaExecutionRole,
      environment: {
        STORAGE_BUCKET_NAME: this.storageBucket.bucketName,
        ENVIRONMENT: environment,
      },
      description: `Results API Lambda for Vehicle Analysis - ${environment}`,
    });

    // Permissions are granted through the IAM role

    // CloudFormation Outputs
    new cdk.CfnOutput(this, 'StorageBucketName', {
      value: this.storageBucket.bucketName,
      description: 'Name of the S3 bucket for video storage',
      exportName: `${this.stackName}-StorageBucketName`,
    });

    new cdk.CfnOutput(this, 'LambdaExecutionRoleArn', {
      value: this.lambdaExecutionRole.roleArn,
      description: 'ARN of the Lambda execution role',
      exportName: `${this.stackName}-LambdaExecutionRoleArn`,
    });

    new cdk.CfnOutput(this, 'UploadHandlerFunctionName', {
      value: this.uploadHandler.functionName,
      description: 'Name of the Upload Handler Lambda function',
      exportName: `${this.stackName}-UploadHandlerFunctionName`,
    });

    new cdk.CfnOutput(this, 'UploadHandlerFunctionArn', {
      value: this.uploadHandler.functionArn,
      description: 'ARN of the Upload Handler Lambda function',
      exportName: `${this.stackName}-UploadHandlerFunctionArn`,
    });

    new cdk.CfnOutput(this, 'VideoProcessorFunctionName', {
      value: this.videoProcessor.functionName,
      description: 'Name of the Video Processor Lambda function',
      exportName: `${this.stackName}-VideoProcessorFunctionName`,
    });

    new cdk.CfnOutput(this, 'VideoProcessorFunctionArn', {
      value: this.videoProcessor.functionArn,
      description: 'ARN of the Video Processor Lambda function',
      exportName: `${this.stackName}-VideoProcessorFunctionArn`,
    });

    new cdk.CfnOutput(this, 'ResultsProcessorFunctionName', {
      value: this.resultsProcessor.functionName,
      description: 'Name of the Results Processor Lambda function',
      exportName: `${this.stackName}-ResultsProcessorFunctionName`,
    });

    new cdk.CfnOutput(this, 'ResultsProcessorFunctionArn', {
      value: this.resultsProcessor.functionArn,
      description: 'ARN of the Results Processor Lambda function',
      exportName: `${this.stackName}-ResultsProcessorFunctionArn`,
    });

    new cdk.CfnOutput(this, 'ResultsApiFunctionName', {
      value: this.resultsApi.functionName,
      description: 'Name of the Results API Lambda function',
      exportName: `${this.stackName}-ResultsApiFunctionName`,
    });

    new cdk.CfnOutput(this, 'ResultsApiFunctionArn', {
      value: this.resultsApi.functionArn,
      description: 'ARN of the Results API Lambda function',
      exportName: `${this.stackName}-ResultsApiFunctionArn`,
    });

    // Tags for cost tracking
    cdk.Tags.of(this).add('Project', 'VehicleAnalysis');
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Stack', 'Lambda');
  }
}
