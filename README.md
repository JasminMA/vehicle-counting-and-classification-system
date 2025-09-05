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

## Development Status
- [x] Project setup and CI/CD
- [ ] Core infrastructure (S3, IAM)
- [ ] Lambda functions
- [ ] API Gateway integration
- [ ] Web UI
- [ ] Testing and deployment

## License
MIT
