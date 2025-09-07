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
  public readonly uploadHandler: lambda.Function;
  public readonly videoProcessor: lambda.Function;
  public readonly resultsProcessor: lambda.Function;
  public readonly resultsApi: lambda.Function;

  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    const { environment, coreStack } = props;

    // Upload Handler Lambda
    this.uploadHandler = new lambda.Function(this, 'UploadHandler', {
      functionName: `VehicleAnalysis-UploadHandler-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/upload-handler'),
      timeout: cdk.Duration.seconds(30),
      memorySize: 128,
      role: coreStack.lambdaExecutionRole,
      environment: {
        STORAGE_BUCKET_NAME: coreStack.storageBucket.bucketName,
        ENVIRONMENT: environment,
      },
      description: `Upload Handler Lambda for Vehicle Analysis - ${environment}`,
    });

    // Grant S3 permissions to Upload Handler
    coreStack.storageBucket.grantReadWrite(this.uploadHandler);

    // Video Processor Lambda
    this.videoProcessor = new lambda.Function(this, 'VideoProcessor', {
      functionName: `VehicleAnalysis-VideoProcessor-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/video-processor'),
      timeout: cdk.Duration.minutes(5),
      memorySize: 256,
      role: coreStack.lambdaExecutionRole,
      environment: {
        SNS_TOPIC_ARN: coreStack.rekognitionCompletionTopic.topicArn,
        REKOGNITION_ROLE_ARN: coreStack.rekognitionServiceRole.roleArn,
        ENVIRONMENT: environment,
      },
      description: `Video Processor Lambda for Vehicle Analysis - ${environment}`,
    });

    // Grant permissions to Video Processor
    coreStack.storageBucket.grantReadWrite(this.videoProcessor);
    coreStack.rekognitionCompletionTopic.grantPublish(this.videoProcessor);
    
    // Grant Rekognition permissions to Video Processor
    this.videoProcessor.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'rekognition:StartLabelDetection',
          'rekognition:GetLabelDetection',
          'rekognition:DescribeCollection',
        ],
        resources: ['*'],
      })
    );

    // Add S3 event trigger for Video Processor
    coreStack.storageBucket.addEventNotification(
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
      coreStack.storageBucket.addEventNotification(
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
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/results-processor'),
      timeout: cdk.Duration.minutes(10),
      memorySize: 512,
      role: coreStack.lambdaExecutionRole,
      environment: {
        STORAGE_BUCKET_NAME: coreStack.storageBucket.bucketName,
        ENVIRONMENT: environment,
      },
      description: `Results Processor Lambda for Vehicle Analysis - ${environment}`,
    });

    // Grant permissions to Results Processor
    coreStack.storageBucket.grantReadWrite(this.resultsProcessor);
    
    // Grant Rekognition permissions to Results Processor
    this.resultsProcessor.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'rekognition:GetLabelDetection',
          'rekognition:DescribeCollection',
        ],
        resources: ['*'],
      })
    );

    // Add SNS trigger for Results Processor
    coreStack.rekognitionCompletionTopic.addSubscription(
      new snsSubscriptions.LambdaSubscription(this.resultsProcessor)
    );

    // Results API Lambda
    this.resultsApi = new lambda.Function(this, 'ResultsApi', {
      functionName: `VehicleAnalysis-ResultsApi-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/results-api'),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      role: coreStack.lambdaExecutionRole,
      environment: {
        STORAGE_BUCKET_NAME: coreStack.storageBucket.bucketName,
        ENVIRONMENT: environment,
      },
      description: `Results API Lambda for Vehicle Analysis - ${environment}`,
    });

    // Grant S3 permissions to Results API
    coreStack.storageBucket.grantRead(this.resultsApi);

    // CloudFormation Outputs
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
