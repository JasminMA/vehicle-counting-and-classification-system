# Vehicle Counting and Classification System

[![Test Pipeline](https://github.com/your-username/vehicle-counting-system/actions/workflows/test.yml/badge.svg)](https://github.com/your-username/vehicle-counting-system/actions/workflows/test.yml)
[![Code Quality](https://github.com/your-username/vehicle-counting-system/actions/workflows/code-quality.yml/badge.svg)](https://github.com/your-username/vehicle-counting-system/actions/workflows/code-quality.yml)

## Overview
Automated video analysis system that counts and classifies vehicles using AWS AI services.

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- AWS CLI configured
- AWS CDK installed globally

### Installation
```bash
# Install all dependencies
npm run install:all

# Or install manually
cd infrastructure && npm install
cd .. && pip install -r requirements.txt
```

### First-Time Setup
```bash
# Bootstrap CDK (required once per AWS account/region)
./scripts/bootstrap-cdk.sh          # Linux/Mac
.\scripts\bootstrap-cdk.ps1         # Windows PowerShell

# Or manually:
npm run bootstrap
# Or: cdk bootstrap aws://YOUR-ACCOUNT-ID/YOUR-REGION
```

### Development
```bash
# Run all tests
npm test

# Build CDK
npm run build

# Synthesize CloudFormation
npm run synth

# Deploy to development
npm run deploy:dev
```

## Project Structure
```
├── infrastructure/     # AWS CDK (TypeScript)
├── lambda/            # Lambda functions (Python)
├── web-ui/           # Frontend (HTML/CSS/JS)
├── .github/          # CI/CD workflows
└── docs/             # Documentation
```

## Documentation
- [System Design](SYSTEM_DESIGN.md)
- [Implementation Plan](IMPLEMENTATION_PLAN.md)
- [Client Overview](CLIENT_OVERVIEW.md)
- [AWS Deployment Strategy](AWS_DEPLOYMENT_STRATEGY.md)
- [API Documentation](docs/API_DOCUMENTATION.md)

## Development Status
- [x] Project setup and CI/CD
- [x] Core infrastructure (S3, IAM, SNS)
- [x] Upload Handler Lambda function
- [x] Video Processor Lambda function
- [x] Results Processor Lambda function
- [x] Results API Lambda function
- [x] API Gateway integration
- [x] Web UI implementation
- [ ] End-to-end testing and deployment

## License
MIT
