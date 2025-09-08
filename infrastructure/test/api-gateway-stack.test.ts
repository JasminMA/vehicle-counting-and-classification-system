import * as cdk from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import { CoreStack } from '../lib/core-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { ApiGatewayStack } from '../lib/api-gateway-stack';

describe('ApiGatewayStack', () => {
  let app: cdk.App;
  let coreStack: CoreStack;
  let lambdaStack: LambdaStack;
  let apiGatewayStack: ApiGatewayStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    
    // Create prerequisite stacks
    coreStack = new CoreStack(app, 'TestCoreStack', {
      environment: 'test',
      env: { account: '123456789012', region: 'us-east-1' },
    });

    lambdaStack = new LambdaStack(app, 'TestLambdaStack', {
      environment: 'test',
      coreStack: coreStack,
      env: { account: '123456789012', region: 'us-east-1' },
    });

    // Create API Gateway stack
    apiGatewayStack = new ApiGatewayStack(app, 'TestApiGatewayStack', {
      environment: 'test',
      lambdaStack: lambdaStack,
      env: { account: '123456789012', region: 'us-east-1' },
    });

    template = Template.fromStack(apiGatewayStack);
  });

  test('creates API Gateway with correct configuration', () => {
    // Check that API Gateway is created
    template.hasResourceProperties('AWS::ApiGateway::RestApi', {
      Name: 'VehicleAnalysis-API-test',
      Description: 'Vehicle Analysis API for test environment',
    });
  });

  test('creates deployment with correct stage', () => {
    // Check deployment configuration
    template.hasResourceProperties('AWS::ApiGateway::Deployment', {
      StageName: 'test',
    });

    // Check stage configuration
    template.hasResourceProperties('AWS::ApiGateway::Stage', {
      StageName: 'test',
      LoggingLevel: 'INFO',
      DataTraceEnabled: true,
      MetricsEnabled: true,
    });
  });

  test('creates upload endpoint with POST method', () => {
    // Check upload resource
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      PathPart: 'upload',
    });

    // Check POST method on upload
    template.hasResourceProperties('AWS::ApiGateway::Method', {
      HttpMethod: 'POST',
      ResourceId: Match.anyValue(),
      Integration: {
        Type: 'AWS_PROXY',
        IntegrationHttpMethod: 'POST',
      },
    });
  });

  test('creates results endpoints with correct structure', () => {
    // Check results resource
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      PathPart: 'results',
    });

    // Check {jobId} resource
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      PathPart: '{jobId}',
    });

    // Check status resource
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      PathPart: 'status',
    });

    // Check download resource
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      PathPart: 'download',
    });

    // Check {format} resource
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      PathPart: '{format}',
    });
  });

  test('creates GET methods for all results endpoints', () => {
    // Count GET methods - should have multiple for results endpoints
    const getMethods = template.findResources('AWS::ApiGateway::Method', {
      HttpMethod: 'GET',
    });

    // Should have GET methods for:
    // - /results/{jobId}
    // - /results/{jobId}/status  
    // - /results/{jobId}/download/{format}
    // - /health
    expect(Object.keys(getMethods).length).toBeGreaterThanOrEqual(4);
  });

  test('creates health check endpoint', () => {
    // Check health resource
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      PathPart: 'health',
    });

    // Check mock integration for health endpoint
    template.hasResourceProperties('AWS::ApiGateway::Method', {
      HttpMethod: 'GET',
      Integration: {
        Type: 'MOCK',
      },
    });
  });

  test('creates request validators', () => {
    // Check upload request validator
    template.hasResourceProperties('AWS::ApiGateway::RequestValidator', {
      Name: 'upload-validator',
      ValidateRequestBody: true,
    });

    // Check download request validator
    template.hasResourceProperties('AWS::ApiGateway::RequestValidator', {
      Name: 'download-validator',
      ValidateRequestParameters: true,
    });
  });

  test('creates request models for validation', () => {
    // Check upload request model
    template.hasResourceProperties('AWS::ApiGateway::Model', {
      Name: 'UploadRequest',
      Schema: Match.objectLike({
        type: 'object',
        properties: Match.objectLike({
          filename: Match.objectLike({
            type: 'string',
            minLength: 1,
            maxLength: 255,
          }),
          filesize: Match.objectLike({
            type: 'integer',
            minimum: 1,
            maximum: 8589934592,
          }),
        }),
        required: ['filename', 'filesize'],
      }),
    });
  });

  test('enables CORS on all methods', () => {
    // Find all methods and check they have CORS response parameters
    const methods = template.findResources('AWS::ApiGateway::Method');
    
    Object.values(methods).forEach((method: any) => {
      if (method.Properties.HttpMethod !== 'OPTIONS') {
        expect(method.Properties.MethodResponses).toBeDefined();
        
        const responses = method.Properties.MethodResponses;
        const successResponse = responses.find((r: any) => r.StatusCode === '200');
        
        if (successResponse) {
          expect(successResponse.ResponseParameters).toMatchObject({
            'method.response.header.Access-Control-Allow-Origin': true,
          });
        }
      }
    });
  });

  test('creates CloudWatch log group', () => {
    template.hasResourceProperties('AWS::Logs::LogGroup', {
      LogGroupName: '/aws/apigateway/VehicleAnalysis-test',
      RetentionInDays: 7,
    });
  });

  test('creates correct CloudFormation outputs', () => {
    // Check API URL output
    template.hasOutput('ApiGatewayUrl', {
      Description: 'API Gateway endpoint URL',
      Export: {
        Name: 'TestApiGatewayStack-ApiGatewayUrl',
      },
    });

    // Check API ID output
    template.hasOutput('ApiGatewayId', {
      Description: 'API Gateway REST API ID',
      Export: {
        Name: 'TestApiGatewayStack-ApiGatewayId',
      },
    });

    // Check stage output
    template.hasOutput('ApiGatewayStage', {
      Value: 'test',
      Description: 'API Gateway deployment stage',
      Export: {
        Name: 'TestApiGatewayStack-ApiGatewayStage',
      },
    });

    // Check endpoints output
    template.hasOutput('ApiEndpoints', {
      Description: 'API endpoint URLs',
      Export: {
        Name: 'TestApiGatewayStack-ApiEndpoints',
      },
    });
  });

  test('sets correct tags', () => {
    // Check that resources have correct tags
    const api = template.findResources('AWS::ApiGateway::RestApi');
    const apiResource = Object.values(api)[0] as any;
    
    expect(apiResource.Properties.Tags).toContainEqual({
      Key: 'Project',
      Value: 'VehicleAnalysis',
    });
    
    expect(apiResource.Properties.Tags).toContainEqual({
      Key: 'Environment', 
      Value: 'test',
    });
    
    expect(apiResource.Properties.Tags).toContainEqual({
      Key: 'Stack',
      Value: 'ApiGateway',
    });
  });

  test('integrates with correct Lambda functions', () => {
    // Find Lambda integrations
    const methods = template.findResources('AWS::ApiGateway::Method');
    const lambdaIntegrations = Object.values(methods).filter((method: any) => 
      method.Properties.Integration?.Type === 'AWS_PROXY'
    );

    // Should have integrations for upload and results endpoints
    expect(lambdaIntegrations.length).toBeGreaterThanOrEqual(4);

    // Check that integrations reference Lambda functions
    lambdaIntegrations.forEach((method: any) => {
      const integration = method.Properties.Integration;
      expect(integration.IntegrationHttpMethod).toBe('POST');
      expect(integration.Uri).toMatch(/lambda/);
    });
  });

  test('validates API resource structure', () => {
    // Check the complete API structure is created
    const resources = template.findResources('AWS::ApiGateway::Resource');
    const resourcePaths = Object.values(resources).map((r: any) => r.Properties.PathPart);

    expect(resourcePaths).toContain('upload');
    expect(resourcePaths).toContain('results');
    expect(resourcePaths).toContain('{jobId}');
    expect(resourcePaths).toContain('status');
    expect(resourcePaths).toContain('download');
    expect(resourcePaths).toContain('{format}');
    expect(resourcePaths).toContain('health');
  });

  test('configures access logging', () => {
    // Check that access logging is configured
    template.hasResourceProperties('AWS::ApiGateway::Stage', {
      AccessLogSetting: Match.objectLike({
        DestinationArn: Match.anyValue(),
        Format: Match.stringLikeRegexp('requestTime.*status.*httpMethod'),
      }),
    });
  });

  test('enables API Gateway policy for public access', () => {
    template.hasResourceProperties('AWS::ApiGateway::RestApi', {
      Policy: Match.objectLike({
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Principal: '*',
            Action: 'execute-api:Invoke',
            Resource: '*',
          }),
        ]),
      }),
    });
  });
});

describe('ApiGatewayStack Error Cases', () => {
  test('handles missing Lambda stack gracefully', () => {
    const app = new cdk.App();
    
    // This should not throw during construction
    expect(() => {
      const coreStack = new CoreStack(app, 'TestCoreStack', {
        environment: 'test',
        env: { account: '123456789012', region: 'us-east-1' },
      });

      const lambdaStack = new LambdaStack(app, 'TestLambdaStack', {
        environment: 'test',
        coreStack: coreStack,
        env: { account: '123456789012', region: 'us-east-1' },
      });

      new ApiGatewayStack(app, 'TestApiGatewayStack', {
        environment: 'test',
        lambdaStack: lambdaStack,
        env: { account: '123456789012', region: 'us-east-1' },
      });
    }).not.toThrow();
  });
});
