#!/bin/bash
# Test script for Core Infrastructure Stack

echo "🧪 Testing Core Infrastructure Stack..."

# Build the TypeScript
echo "📦 Building TypeScript..."
cd infrastructure
npm run build

if [ $? -ne 0 ]; then
    echo "❌ TypeScript build failed"
    exit 1
fi

# Run CDK tests
echo "🧪 Running CDK tests..."
npm test

if [ $? -ne 0 ]; then
    echo "❌ CDK tests failed"
    exit 1
fi

# Synthesize CloudFormation for dev environment
echo "🔧 Synthesizing CloudFormation for dev environment..."
npm run synth:dev

if [ $? -ne 0 ]; then
    echo "❌ CDK synthesis failed"
    exit 1
fi

# Synthesize CloudFormation for prod environment
echo "🔧 Synthesizing CloudFormation for prod environment..."
npm run synth:prod

if [ $? -ne 0 ]; then
    echo "❌ CDK synthesis failed"
    exit 1
fi

echo "✅ All tests passed! Core Infrastructure is ready."
echo ""
echo "📋 Next steps:"
echo "   1. Configure AWS credentials"
echo "   2. Run 'npm run deploy:dev' to deploy to development"
echo "   3. Verify resources in AWS Console"
echo ""
echo "🌐 After deployment, you'll have:"
echo "   - S3 storage bucket for videos/results"
echo "   - S3 web bucket for UI hosting"
echo "   - IAM roles for Lambda and Rekognition"
echo "   - Lifecycle policies for cost optimization"
