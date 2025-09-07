#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { CoreStack } from '../lib/core-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { ApiGatewayStack } from '../lib/api-gateway-stack';
import { getEnvironmentConfig } from '../lib/config';

const app = new cdk.App();

// Get environment from context or default to 'dev'
const envName = app.node.tryGetContext('environment') || process.env.ENVIRONMENT || 'dev';
const envConfig = getEnvironmentConfig(envName);

// Deploy Core Infrastructure Stack
const coreStack = new CoreStack(app, `VehicleAnalysis-Core-${envConfig.envName}`, {
  environment: envConfig.envName,
  env: {
    account: envConfig.account,
    region: envConfig.region,
  },
  description: `Vehicle Analysis Core Infrastructure - ${envConfig.envName.toUpperCase()} environment`,
  tags: {
    Project: 'VehicleAnalysis',
    Environment: envConfig.envName,
    ManagedBy: 'CDK',
  },
});

// Deploy Lambda Functions Stack
const lambdaStack = new LambdaStack(app, `VehicleAnalysis-Lambda-${envConfig.envName}`, {
  environment: envConfig.envName,
  coreStack: coreStack,
  env: {
    account: envConfig.account,
    region: envConfig.region,
  },
  description: `Vehicle Analysis Lambda Functions - ${envConfig.envName.toUpperCase()} environment`,
  tags: {
    Project: 'VehicleAnalysis',
    Environment: envConfig.envName,
    ManagedBy: 'CDK',
  },
});

// Deploy API Gateway Stack
const apiGatewayStack = new ApiGatewayStack(app, `VehicleAnalysis-ApiGateway-${envConfig.envName}`, {
  environment: envConfig.envName,
  lambdaStack: lambdaStack,
  env: {
    account: envConfig.account,
    region: envConfig.region,
  },
  description: `Vehicle Analysis API Gateway - ${envConfig.envName.toUpperCase()} environment`,
  tags: {
    Project: 'VehicleAnalysis',
    Environment: envConfig.envName,
    ManagedBy: 'CDK',
  },
});

// Set up dependencies
lambdaStack.addDependency(coreStack);
apiGatewayStack.addDependency(lambdaStack);

app.synth();