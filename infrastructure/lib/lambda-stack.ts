import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
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

    // Placeholder for other Lambda functions (to be implemented)
    this.videoProcessor = this.createPlaceholderFunction('VideoProcessor', environment);
    this.resultsProcessor = this.createPlaceholderFunction('ResultsProcessor', environment);
    this.resultsApi = this.createPlaceholderFunction('ResultsApi', environment);

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

    // Tags for cost tracking
    cdk.Tags.of(this).add('Project', 'VehicleAnalysis');
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Stack', 'Lambda');
  }

  private createPlaceholderFunction(name: string, environment: string): lambda.Function {
    return new lambda.Function(this, name, {
      functionName: `VehicleAnalysis-${name}-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
def handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Placeholder function - not implemented yet'
    }
      `),
      timeout: cdk.Duration.seconds(30),
      memorySize: 128,
      description: `Placeholder ${name} Lambda for Vehicle Analysis - ${environment}`,
    });
  }
}
