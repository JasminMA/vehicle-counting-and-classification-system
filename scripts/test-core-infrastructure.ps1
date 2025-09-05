# Test script for Core Infrastructure Stack (PowerShell)

Write-Host "🧪 Testing Core Infrastructure Stack..." -ForegroundColor Cyan

# Build the TypeScript
Write-Host "📦 Building TypeScript..." -ForegroundColor Yellow
Set-Location infrastructure
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ TypeScript build failed" -ForegroundColor Red
    exit 1
}

# Run CDK tests
Write-Host "🧪 Running CDK tests..." -ForegroundColor Yellow
npm test

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ CDK tests failed" -ForegroundColor Red
    exit 1
}

# Synthesize CloudFormation for dev environment
Write-Host "🔧 Synthesizing CloudFormation for dev environment..." -ForegroundColor Yellow
npm run synth:dev

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ CDK synthesis failed" -ForegroundColor Red
    exit 1
}

# Synthesize CloudFormation for prod environment
Write-Host "🔧 Synthesizing CloudFormation for prod environment..." -ForegroundColor Yellow
npm run synth:prod

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ CDK synthesis failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ All tests passed! Core Infrastructure is ready." -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Configure AWS credentials"
Write-Host "   2. Run 'npm run deploy:dev' to deploy to development"
Write-Host "   3. Verify resources in AWS Console"
Write-Host ""
Write-Host "🌐 After deployment, you'll have:" -ForegroundColor Cyan
Write-Host "   - S3 storage bucket for videos/results"
Write-Host "   - S3 web bucket for UI hosting"
Write-Host "   - IAM roles for Lambda and Rekognition"
Write-Host "   - Lifecycle policies for cost optimization"
