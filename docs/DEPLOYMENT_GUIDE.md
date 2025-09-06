# Simplified Deployment Guide

## 🚀 Standard Deployment Workflow

### Daily Development Commands:
```bash
# 1. Build TypeScript and run tests
npm run build
npm test

# 2. Preview changes (optional but recommended)
npm run diff:dev

# 3. Deploy all stacks
npm run deploy:dev
```

### Environment-Specific Deployment:
```bash
# Deploy to development
npm run deploy:dev

# Deploy to production
npm run deploy:prod
```

### Testing After Deployment:

#### Test Upload Handler Function:
```bash
# Get function name
FUNCTION_NAME=$(aws cloudformation describe-stacks \
  --stack-name VehicleAnalysis-Lambda-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UploadHandlerFunctionName`].OutputValue' \
  --output text)

# Test the function
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --payload '{"body": "{\"filename\": \"test_video.mp4\", \"filesize\": 1000000}"}' \
  response.json

# View response
cat response.json | jq .
```

#### Verify S3 Buckets:
```bash
# List created buckets
aws s3 ls | grep vehicle-analysis

# Check bucket contents
aws s3 ls s3://vehicle-analysis-storage-dev-{account-id}/
```

#### Check CloudFormation Stacks:
```bash
# List all project stacks
aws cloudformation list-stacks \
  --query 'StackSummaries[?contains(StackName, `VehicleAnalysis`)].{Name:StackName,Status:StackStatus}' \
  --output table
```

## 🔄 Development Cycle:

1. **Edit code** (TypeScript CDK or Python Lambda)
2. **Build**: `npm run build`
3. **Test**: `npm test`
4. **Deploy**: `npm run deploy:dev`
5. **Verify**: Test functions and check AWS console

## ⚠️ What NOT to Use:

- ❌ Individual deployment scripts for single components
- ❌ Manual CDK commands (use npm scripts instead)
- ❌ Direct AWS CLI for infrastructure changes

## ✅ Why This Approach:

- **Simple**: One command deploys everything
- **Reliable**: Dependencies handled automatically
- **Consistent**: Same process for all environments
- **Maintainable**: Fewer scripts to maintain

---

**Bottom Line**: Use `npm run deploy:dev` for everything. It's simple, reliable, and handles all dependencies correctly.
