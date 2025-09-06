#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { CoreStack } from '../lib/core-stack';
import { LambdaStack } from '../lib/lambda-stack';
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

// Ensure Lambda stack depends on Core stack
lambdaStack.addDependency(coreStack);

app.synth();