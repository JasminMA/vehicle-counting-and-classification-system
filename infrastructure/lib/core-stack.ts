import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sns from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';

export interface CoreStackProps extends cdk.StackProps {
  environment: string;
}

export class CoreStack extends cdk.Stack {
  public readonly storageBucket: s3.Bucket;
  public readonly webBucket: s3.Bucket;
  public readonly lambdaExecutionRole: iam.Role;
  public readonly rekognitionServiceRole: iam.Role;
  public readonly rekognitionCompletionTopic: sns.Topic;

  constructor(scope: Construct, id: string, props: CoreStackProps) {
    super(scope, id, props);

    const { environment } = props;

    // S3 bucket for videos and results with organized folder structure
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

    // S3 bucket for web UI hosting
    this.webBucket = new s3.Bucket(this, 'WebBucket', {
      bucketName: `vehicle-analysis-ui-${environment}-${this.account}`,
      websiteIndexDocument: 'index.html',
      websiteErrorDocument: 'error.html',
      publicReadAccess: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev/testing
      autoDeleteObjects: true, // For dev/testing
      blockPublicAccess: new s3.BlockPublicAccess({
        blockPublicAcls: true,
        blockPublicPolicy: false, // Allow public bucket policy for website
        ignorePublicAcls: true,
        restrictPublicBuckets: false, // Allow public bucket for website
      }),
    });

    // IAM Role for Lambda functions
    this.lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      roleName: `VehicleAnalysis-LambdaExecution-${environment}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                's3:GetObject',
                's3:PutObject',
                's3:DeleteObject',
                's3:ListBucket',
                's3:GetObjectVersion',
              ],
              resources: [
                this.storageBucket.bucketArn,
                `${this.storageBucket.bucketArn}/*`,
              ],
            }),
          ],
        }),
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

    // IAM Role for Rekognition to publish to SNS
    this.rekognitionServiceRole = new iam.Role(this, 'RekognitionServiceRole', {
      roleName: `VehicleAnalysis-RekognitionService-${environment}`,
      assumedBy: new iam.ServicePrincipal('rekognition.amazonaws.com'),
      inlinePolicies: {
        SNSPublish: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['sns:Publish'],
              resources: [`arn:aws:sns:${this.region}:${this.account}:*`],
            }),
          ],
        }),
      },
    });

    // SNS Topic for Rekognition completion notifications
    this.rekognitionCompletionTopic = new sns.Topic(this, 'RekognitionCompletionTopic', {
      topicName: `VehicleAnalysis-RekognitionCompletion-${environment}`,
      displayName: 'Vehicle Analysis Rekognition Completion Notifications',
    });

    // Grant Rekognition service role permission to publish to SNS topic
    this.rekognitionCompletionTopic.grantPublish(this.rekognitionServiceRole);

    // CloudFormation Outputs
    new cdk.CfnOutput(this, 'StorageBucketName', {
      value: this.storageBucket.bucketName,
      description: 'Name of the S3 bucket for video storage',
      exportName: `${this.stackName}-StorageBucketName`,
    });

    new cdk.CfnOutput(this, 'WebBucketName', {
      value: this.webBucket.bucketName,
      description: 'Name of the S3 bucket for web UI hosting',
      exportName: `${this.stackName}-WebBucketName`,
    });

    new cdk.CfnOutput(this, 'WebsiteURL', {
      value: this.webBucket.bucketWebsiteUrl,
      description: 'URL of the static website',
      exportName: `${this.stackName}-WebsiteURL`,
    });

    new cdk.CfnOutput(this, 'LambdaExecutionRoleArn', {
      value: this.lambdaExecutionRole.roleArn,
      description: 'ARN of the Lambda execution role',
      exportName: `${this.stackName}-LambdaExecutionRoleArn`,
    });

    new cdk.CfnOutput(this, 'RekognitionServiceRoleArn', {
      value: this.rekognitionServiceRole.roleArn,
      description: 'ARN of the Rekognition service role',
      exportName: `${this.stackName}-RekognitionServiceRoleArn`,
    });

    new cdk.CfnOutput(this, 'RekognitionCompletionTopicArn', {
      value: this.rekognitionCompletionTopic.topicArn,
      description: 'ARN of the SNS topic for Rekognition completion notifications',
      exportName: `${this.stackName}-RekognitionCompletionTopicArn`,
    });

    // Tags for cost tracking
    cdk.Tags.of(this).add('Project', 'VehicleAnalysis');
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Stack', 'Core');
  }
}
