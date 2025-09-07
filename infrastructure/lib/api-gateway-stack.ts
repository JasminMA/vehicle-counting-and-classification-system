import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { LambdaStack } from './lambda-stack';

export interface ApiGatewayStackProps extends cdk.StackProps {
  environment: string;
  lambdaStack: LambdaStack;
}

export class ApiGatewayStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;
  public readonly apiUrl: string;

  constructor(scope: Construct, id: string, props: ApiGatewayStackProps) {
    super(scope, id, props);

    const { environment, lambdaStack } = props;

    // Create CloudWatch Log Group for API Gateway
    const apiLogGroup = new logs.LogGroup(this, 'ApiGatewayLogGroup', {
      logGroupName: `/aws/apigateway/VehicleAnalysis-${environment}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Create API Gateway
    this.api = new apigateway.RestApi(this, 'VehicleAnalysisApi', {
      restApiName: `VehicleAnalysis-API-${environment}`,
      description: `Vehicle Analysis API for ${environment} environment`,
      
      // Enable CORS for all routes
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: ['GET', 'POST', 'OPTIONS'],
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
          'X-Amz-User-Agent'
        ],
        maxAge: cdk.Duration.seconds(86400), // 24 hours
      },

      // API Gateway configuration
      deployOptions: {
        stageName: environment,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
        accessLogDestination: new apigateway.LogGroupLogDestination(apiLogGroup),
        accessLogFormat: apigateway.AccessLogFormat.jsonWithStandardFields({
          caller: true,
          httpMethod: true,
          ip: true,
          protocol: true,
          requestTime: true,
          resourcePath: true,
          responseLength: true,
          status: true,
          user: true,
        }),
      },

      // Enable request validation
      policy: new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            principals: [new iam.AnyPrincipal()],
            actions: ['execute-api:Invoke'],
            resources: ['*'],
          }),
        ],
      }),
    });

    // Create Lambda integrations
    const uploadIntegration = new apigateway.LambdaIntegration(lambdaStack.uploadHandler, {
      requestTemplates: { 'application/json': '{ "statusCode": "200" }' },
      proxy: true,
      integrationResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
          },
        },
      ],
    });

    const resultsIntegration = new apigateway.LambdaIntegration(lambdaStack.resultsApi, {
      proxy: true,
      integrationResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
          },
        },
      ],
    });

    // Create API resources and methods

    // 1. Upload endpoint: POST /upload
    const uploadResource = this.api.root.addResource('upload');
    uploadResource.addMethod('POST', uploadIntegration, {
      methodResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        {
          statusCode: '400',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        {
          statusCode: '500',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
      ],
      requestValidator: new apigateway.RequestValidator(this, 'UploadRequestValidator', {
        restApi: this.api,
        requestValidatorName: 'upload-validator',
        validateRequestBody: true,
      }),
      requestModels: {
        'application/json': new apigateway.Model(this, 'UploadRequestModel', {
          restApi: this.api,
          modelName: 'UploadRequest',
          schema: {
            type: apigateway.JsonSchemaType.OBJECT,
            properties: {
              filename: {
                type: apigateway.JsonSchemaType.STRING,
                minLength: 1,
                maxLength: 255,
              },
              filesize: {
                type: apigateway.JsonSchemaType.INTEGER,
                minimum: 1,
                maximum: 8589934592, // 8GB
              },
            },
            required: ['filename', 'filesize'],
          },
        }),
      },
    });

    // 2. Results endpoints: GET /results/{jobId}
    const resultsResource = this.api.root.addResource('results');
    const jobResource = resultsResource.addResource('{jobId}');

    // GET /results/{jobId} - Get complete results
    jobResource.addMethod('GET', resultsIntegration, {
      requestParameters: {
        'method.request.path.jobId': true,
        'method.request.querystring.details': false,
      },
      methodResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        {
          statusCode: '404',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
      ],
    });

    // GET /results/{jobId}/status - Get job status only
    const statusResource = jobResource.addResource('status');
    statusResource.addMethod('GET', resultsIntegration, {
      requestParameters: {
        'method.request.path.jobId': true,
      },
      methodResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        {
          statusCode: '404',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
      ],
    });

    // GET /results/{jobId}/download/{format} - Download results
    const downloadResource = jobResource.addResource('download');
    const formatResource = downloadResource.addResource('{format}');
    formatResource.addMethod('GET', resultsIntegration, {
      requestParameters: {
        'method.request.path.jobId': true,
        'method.request.path.format': true,
      },
      requestValidator: new apigateway.RequestValidator(this, 'DownloadRequestValidator', {
        restApi: this.api,
        requestValidatorName: 'download-validator',
        validateRequestParameters: true,
      }),
      methodResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        {
          statusCode: '400',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        {
          statusCode: '404',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
      ],
    });

    // 3. Health check endpoint: GET /health
    const healthResource = this.api.root.addResource('health');
    healthResource.addMethod('GET', new apigateway.MockIntegration({
      integrationResponses: [
        {
          statusCode: '200',
          responseTemplates: {
            'application/json': JSON.stringify({
              status: 'healthy',
              timestamp: '$context.requestTime',
              environment: environment,
              version: '1.0.0',
            }),
          },
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
          },
        },
      ],
      requestTemplates: {
        'application/json': '{ "statusCode": 200 }',
      },
    }), {
      methodResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
      ],
    });

    // Store API URL for outputs
    this.apiUrl = this.api.url;

    // CloudFormation Outputs
    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: this.api.url,
      description: 'API Gateway endpoint URL',
      exportName: `${this.stackName}-ApiGatewayUrl`,
    });

    new cdk.CfnOutput(this, 'ApiGatewayId', {
      value: this.api.restApiId,
      description: 'API Gateway REST API ID',
      exportName: `${this.stackName}-ApiGatewayId`,
    });

    new cdk.CfnOutput(this, 'ApiGatewayStage', {
      value: environment,
      description: 'API Gateway deployment stage',
      exportName: `${this.stackName}-ApiGatewayStage`,
    });

    // API Documentation
    new cdk.CfnOutput(this, 'ApiDocumentationUrl', {
      value: `https://console.aws.amazon.com/apigateway/home?region=${this.region}#/apis/${this.api.restApiId}/resources`,
      description: 'API Gateway console URL for documentation',
      exportName: `${this.stackName}-ApiDocumentationUrl`,
    });

    // API Endpoints Summary
    new cdk.CfnOutput(this, 'ApiEndpoints', {
      value: JSON.stringify({
        upload: `${this.api.url}upload`,
        results: `${this.api.url}results/{jobId}`,
        status: `${this.api.url}results/{jobId}/status`,
        download: `${this.api.url}results/{jobId}/download/{format}`,
        health: `${this.api.url}health`,
      }),
      description: 'API endpoint URLs',
      exportName: `${this.stackName}-ApiEndpoints`,
    });

    // Tags for cost tracking
    cdk.Tags.of(this).add('Project', 'VehicleAnalysis');
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Stack', 'ApiGateway');
  }
}
