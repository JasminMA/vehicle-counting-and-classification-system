#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { CoreStack } from '../lib/core-stack';
import { getEnvironmentConfig } from '../lib/config';

const app = new cdk.App();

// Get environment from context or default to 'dev'
const envName = app.node.tryGetContext('environment') || process.env.ENVIRONMENT || 'dev';
const envConfig = getEnvironmentConfig(envName);

// Deploy Core Infrastructure Stack
new CoreStack(app, `VehicleAnalysis-Core-${envConfig.envName}`, {
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

// Add a comment about upcoming stacks
app.synth();