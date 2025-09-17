# Core Infrastructure Deployment Guide

## What We've Built

The **Core Infrastructure Stack** provides the foundation for the Vehicle Counting System:

### 📦 Components Created:
- **S3 Storage Bucket**: Organized storage for videos, processing status, and results
- **S3 Web Bucket**: Static website hosting for the user interface
- **IAM Roles**: Secure permissions for Lambda functions and Rekognition service
- **Lifecycle Policies**: Automatic cleanup to control costs
- **CORS Configuration**: Secure cross-origin requests for web uploads

### 🏗️ Stack Architecture:
```
Core Infrastructure Stack
├── S3 Storage Bucket
│   ├── uploads/{job-id}/           # Video files
│   ├── processing/{job-id}.processing  # Status markers
│   ├── results/{job-id}/           # Analysis results
│   └── errors/{job-id}/            # Error logs
├── S3 Web Bucket (Static Website)
├── Lambda Execution Role
└── Rekognition Service Role
```

## 🧪 Testing the Stack

### Prerequisites:
- Node.js 18+ installed
- AWS CLI configured with credentials
- CDK CLI installed globally: `npm install -g aws-cdk`
- **CDK Bootstrap completed** (see Bootstrap section below)

### 🚀 CDK Bootstrap (Required First Time)

**You MUST bootstrap CDK before first deployment:**

```bash
# Bootstrap for your account and region
cdk bootstrap aws://YOUR-ACCOUNT-ID/YOUR-REGION

# Example (replace with your account ID and region):
cdk bootstrap aws://949010940542/eu-west-1
```

**What bootstrap does:**
- Creates CDK toolkit stack (`CDKToolkit`)
- Sets up S3 bucket for CDK assets
- Creates IAM roles for deployments
- **One-time setup per account/region**

**Find your account ID:**
```bash
aws sts get-caller-identity --query Account --output text
```

**Common regions:**
- `us-east-1` (N. Virginia)
- `eu-west-1` (Ireland) 
- `us-west-2` (Oregon)
- `ap-southeast-1` (Singapore)

### Run Tests Locally:

**Option 1: Use npm scripts (from project root)**
```bash
npm run build
npm run test:cdk
npm run synth:dev
```

**Option 2: Manual testing**
```bash
cd infrastructure
npm run build
npm test
npm run synth:dev
```

## 🚀 Deployment

### Deploy to Development Environment:
```bash
# From project root
npm run deploy:dev

# Or from infrastructure directory
cd infrastructure
npm run deploy:dev
```

### Deploy to Production Environment:
```bash
# From project root  
npm run deploy:prod

# Or from infrastructure directory
cd infrastructure
npm run deploy:prod
```

### View Differences Before Deployment:
```bash
npm run diff:dev    # See what will change in dev
npm run diff:prod   # See what will change in prod
```

## 📋 Post-Deployment Verification

After successful deployment, verify in AWS Console:

### 1. S3 Buckets Created:
- `vehicle-analysis-storage-{env}-{account-id}`
- `vehicle-analysis-ui-{env}-{account-id}`

### 2. IAM Roles Created:
- `VehicleAnalysis-LambdaExecution-{env}`
- `VehicleAnalysis-RekognitionService-{env}`

### 3. Check CloudFormation Outputs:
```bash
aws cloudformation describe-stacks \
  --stack-name VehicleAnalysis-Core-dev \
  --query 'Stacks[0].Outputs'
```

## 💰 Cost Impact

**Monthly costs for Core Infrastructure:**
- **S3 Storage**: ~$1-3/month (depends on usage)
- **S3 Requests**: ~$0.10-0.50/month  
- **IAM Roles**: Free
- **Total**: ~$1-4/month

**Cost Optimization Features:**
- Automatic file deletion after 30-90 days
- Lifecycle policies for different file types
- No unnecessary versioning or encryption

## 🔧 Environment Configuration

### Supported Environments:
- **dev**: Development environment
- **staging**: Staging environment (optional)
- **prod**: Production environment

### Environment-Specific Resources:
Each environment gets its own:
- Separate S3 buckets with environment suffix
- Separate IAM roles
- Isolated CloudFormation stack

### Configure Custom Environments:
Edit `infrastructure/lib/config.ts` to add new environments:
```typescript
export const ENVIRONMENTS: Record<string, EnvironmentConfig> = {
  dev: { ... },
  staging: { ... },
  prod: { ... },
  'client-name': {
    envName: 'client-name',
    account: 'CLIENT_ACCOUNT_ID',
    region: 'us-east-1',
  },
};
```

## 🛡️ Security Features

### IAM Least Privilege:
- Lambda roles have minimum required permissions
- S3 bucket policies restrict access appropriately
- Rekognition role limited to SNS publishing

### S3 Security:
- Public read access only for web UI bucket
- Storage bucket private with controlled access
- CORS configured for secure web uploads

## 🔄 Next Steps

After Core Infrastructure is deployed:

1. **✅ Phase 1.3 Complete**: Core Infrastructure Stack
2. **➡️ Next Phase**: Lambda Functions (Phase 2)
   - Upload Handler Lambda
   - Video Processor Lambda  
   - Results Processor Lambda
   - Results API Lambda

## 📞 Troubleshooting

### Common Issues:

**CDK Bootstrap Required:**
```bash
# Error: "current credentials could not be used to assume role"
# Solution: Bootstrap CDK first
cdk bootstrap aws://YOUR-ACCOUNT-ID/YOUR-REGION

# Example:
cdk bootstrap aws://949010940542/eu-west-1
```

**Wrong Region:**
```bash
# Make sure you're bootstrapping the same region you're deploying to
aws configure get region
cdk bootstrap aws://$(aws sts get-caller-identity --query Account --output text)/$(aws configure get region)
```

**Bootstrap Status Check:**
```bash
# Check if bootstrap stack exists
aws cloudformation describe-stacks --stack-name CDKToolkit
```

**Permission Denied:**
- Ensure AWS credentials are configured
- Check IAM permissions for CDK deployment
- Verify you have permissions to create CloudFormation stacks

**Stack Already Exists:**
- Use `npm run diff:dev` to see changes
- Use `cdk destroy` to remove stack if needed

**TypeScript Compilation Errors:**
```bash
cd infrastructure
npm run build
# Fix any TypeScript errors shown
```

### Getting Help:
- Check CloudFormation events in AWS Console
- Review CDK logs: `cdk deploy --verbose`
- Validate IAM permissions in AWS Console

---

🎉 **Congratulations!** You now have a solid foundation for your Vehicle Counting System!