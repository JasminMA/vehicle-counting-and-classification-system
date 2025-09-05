export interface EnvironmentConfig {
  envName: string;
  account: string;
  region: string;
  domainName?: string;
}

export const ENVIRONMENTS: Record<string, EnvironmentConfig> = {
  dev: {
    envName: 'dev',
    account: process.env.CDK_DEFAULT_ACCOUNT || '949010940542',
    region: process.env.CDK_DEFAULT_REGION || 'eu-west-1',
  },
  staging: {
    envName: 'staging',
    account: process.env.CDK_DEFAULT_ACCOUNT || '949010940542',
    region: process.env.CDK_DEFAULT_REGION || 'eu-west-1',
  },
  prod: {
    envName: 'prod',
    account: process.env.CDK_DEFAULT_ACCOUNT || '949010940542',
    region: process.env.CDK_DEFAULT_REGION || 'eu-west-1',
  },
};

export function getEnvironmentConfig(envName: string): EnvironmentConfig {
  const config = ENVIRONMENTS[envName];
  if (!config) {
    throw new Error(`Environment configuration not found for: ${envName}. Available environments: ${Object.keys(ENVIRONMENTS).join(', ')}`);
  }
  return config;
}
