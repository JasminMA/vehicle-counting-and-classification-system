# Web UI Deployment Guide

## Overview
The Vehicle Analysis Web UI is a modern, responsive single-page application built with vanilla HTML, CSS, and JavaScript. It provides a complete interface for uploading videos, monitoring analysis jobs, and viewing results.

## Features Implemented

### 📤 Upload Interface
- **Drag & Drop Support**: Modern file upload with visual feedback
- **File Validation**: Format and size checking before upload
- **Progress Tracking**: Real-time upload progress with cancellation
- **Format Support**: MP4, MOV, AVI, MKV, WEBM up to 8GB

### 📊 Job Management
- **Real-time Status**: Live job status updates with polling
- **Job History**: Persistent job tracking across sessions
- **Bulk Actions**: Clear completed jobs, refresh all statuses
- **Error Handling**: Detailed error messages and retry options

### 📈 Results Visualization
- **Vehicle Counts**: Summary cards with total and breakdown by type
- **Timeline View**: Chronological detection list with timestamps
- **Download Options**: JSON and CSV export functionality
- **Interactive Features**: Filtering, search, and export capabilities

### 🎨 User Experience
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Modern UI**: Clean, professional interface with animations
- **Accessibility**: Proper ARIA labels, keyboard navigation
- **Toast Notifications**: User-friendly status messages
- **Modal Dialogs**: Help, about, and privacy information

## File Structure

```
web-ui/
├── index.html              # Main application page
├── css/
│   └── styles.css          # Complete styling with CSS variables
└── js/
    ├── utils.js            # Utility functions and helpers
    ├── api.js              # API client and job management
    ├── upload.js           # File upload functionality
    ├── jobs.js             # Job list and status management
    ├── results.js          # Results display and visualization
    └── app.js              # Main application controller
```

## Configuration

### API Configuration
Update the API base URL in `index.html`:

```javascript
window.APP_CONFIG = {
    API_BASE_URL: 'https://your-api-gateway-url.amazonaws.com/dev/',
    MAX_FILE_SIZE: 8 * 1024 * 1024 * 1024, // 8GB
    SUPPORTED_FORMATS: ['mp4', 'mov', 'avi', 'mkv', 'webm'],
    POLL_INTERVAL: 10000, // 10 seconds
    MAX_JOBS_DISPLAY: 10
};
```

**Getting your API Gateway URL:**
```bash
# After deploying infrastructure
cd infrastructure
cdk deploy --all -c environment=dev

# The API Gateway URL will be in the outputs
# Look for: VehicleAnalysis-ApiGateway-dev.ApiGatewayUrl
```

## Deployment Options

### Option 1: S3 Static Website (Recommended)

This option hosts the UI in the same AWS account as your backend.

```bash
# 1. Get the web bucket name from CDK outputs
WEB_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name VehicleAnalysis-Core-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebBucketName`].OutputValue' \
  --output text)

# 2. Sync web UI files to S3
aws s3 sync web-ui/ s3://$WEB_BUCKET/ --delete

# 3. Get the website URL
WEBSITE_URL=$(aws cloudformation describe-stacks \
  --stack-name VehicleAnalysis-Core-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
  --output text)

echo "Web UI available at: $WEB_BUCKET"
```

**PowerShell version:**
```powershell
# Get web bucket name
$WebBucket = aws cloudformation describe-stacks `
  --stack-name VehicleAnalysis-Core-dev `
  --query 'Stacks[0].Outputs[?OutputKey==`WebBucketName`].OutputValue' `
  --output text

# Sync files
aws s3 sync web-ui/ s3://$WebBucket/ --delete

# Get website URL
$WebsiteUrl = aws cloudformation describe-stacks `
  --stack-name VehicleAnalysis-Core-dev `
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' `
  --output text

Write-Host "Web UI available at: $WebsiteUrl"
```

### Option 2: Local Development Server

For development and testing:

```bash
# Navigate to web-ui directory
cd web-ui

# Start a simple HTTP server
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000

# Node.js (if you have npx installed)
npx serve . -p 8000

# Access at: http://localhost:8000
```

### Option 3: Custom Web Server

Deploy to your own web server (Apache, Nginx, etc.):

```bash
# Copy files to web server document root
cp -r web-ui/* /var/www/html/

# Or create a tarball for transfer
tar -czf vehicle-analysis-ui.tar.gz web-ui/
```

## CORS Configuration

The API Gateway is configured to allow requests from any origin (`*`). For production, you may want to restrict this to your specific domain.

**Current CORS headers (in API Gateway):**
```javascript
'Access-Control-Allow-Origin': '*'
'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key'
```

**To restrict to specific domain:**
Update the API Gateway stack to use your domain instead of `*`.

## Custom Domain (Optional)

### With CloudFront and Route 53

```bash
# 1. Create CloudFront distribution (optional CDK stack)
# 2. Configure custom domain in Route 53
# 3. Update API base URL to use custom domain
```

Example custom domain setup:
- Web UI: `https://vehicle-analysis.yourcompany.com`
- API: `https://api.vehicle-analysis.yourcompany.com`

## Environment-Specific Deployment

### Development Environment
```bash
# Deploy to dev environment
cd infrastructure
cdk deploy --all -c environment=dev

# Sync UI with dev API URL
# Update APP_CONFIG.API_BASE_URL to dev API Gateway URL
aws s3 sync web-ui/ s3://vehicle-analysis-ui-dev-123456789012/
```

### Production Environment
```bash
# Deploy to production
cd infrastructure
cdk deploy --all -c environment=prod

# Update API URL for production
# Update APP_CONFIG.API_BASE_URL to prod API Gateway URL
aws s3 sync web-ui/ s3://vehicle-analysis-ui-prod-123456789012/
```

## Security Considerations

### Content Security Policy (Optional)
Add CSP headers for enhanced security:

```html
<meta http-equiv="Content-Security-Policy" content="
    default-src 'self'; 
    script-src 'self' 'unsafe-inline'; 
    style-src 'self' 'unsafe-inline' fonts.googleapis.com; 
    font-src 'self' fonts.gstatic.com; 
    connect-src 'self' *.amazonaws.com;
    img-src 'self' data:;
">
```

### HTTPS Enforcement
For production, ensure all traffic uses HTTPS:
- S3 static website hosting supports HTTPS
- API Gateway provides HTTPS by default
- Consider CloudFront for custom domain HTTPS

## Monitoring & Analytics

### Basic Monitoring
The UI includes built-in error tracking and user feedback:

```javascript
// Global error handling
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    // Could send to analytics service
});

// API call tracking
// See api.js for request/response logging
```

## Performance Optimization

### Implemented Optimizations
- **CSS Variables**: Efficient theming and consistent styling
- **Debounced/Throttled Events**: Optimized scroll and resize handlers
- **Local Storage**: Persistent job data reduces API calls
- **Efficient DOM Updates**: Minimal re-renders and targeted updates
- **Image Optimization**: CSS-based icons and minimal assets

### Additional Optimizations (Optional)
- **Service Worker**: Offline functionality and caching
- **Bundle Optimization**: Minify CSS/JS for production
- **CDN**: Use CloudFront for global distribution

## Browser Support

### Supported Browsers
- **Chrome**: 80+ (recommended)
- **Firefox**: 75+
- **Safari**: 13+
- **Edge**: 80+

### Required Features
- **ES6+**: Arrow functions, async/await, classes
- **CSS Grid**: Layout system
- **Fetch API**: HTTP requests
- **Local Storage**: Data persistence
- **File API**: File upload functionality

### Fallbacks
The UI gracefully degrades for older browsers:
- Basic upload functionality without drag & drop
- Simplified animations and transitions
- Fallback styling for unsupported CSS features

## Troubleshooting

### Common Issues

#### 1. "API connection failed"
**Cause**: Incorrect API base URL or CORS issues
**Solution**: 
- Verify API Gateway URL in `APP_CONFIG`
- Check API Gateway deployment status
- Verify CORS configuration

#### 2. "Upload failed"
**Cause**: File too large, unsupported format, or network issues
**Solution**:
- Check file size (max 8GB)
- Verify file format is supported
- Check network connectivity

#### 3. "Jobs not loading"
**Cause**: Local storage issues or API connectivity
**Solution**:
- Clear browser local storage
- Refresh page and check API status
- Verify job IDs are valid format

#### 4. "Results not displaying"
**Cause**: Job not completed or API errors
**Solution**:
- Wait for job completion
- Check job status in jobs list
- Verify API connectivity

### Debug Mode
Enable debug logging in browser console:

```javascript
// In browser console
localStorage.setItem('vehicleAnalysis_debug', 'true');
// Reload page for detailed logging

// Disable debug mode
localStorage.removeItem('vehicleAnalysis_debug');
```

### Network Debugging
Monitor network requests in browser dev tools:
1. Open Developer Tools (F12)
2. Go to Network tab
3. Perform action (upload, check status)
4. Check for failed requests or errors

## Customization

### Theming
Customize colors by updating CSS variables in `styles.css`:

```css
:root {
    --primary-color: #your-brand-color;
    --success-color: #your-success-color;
    /* ... other variables ... */
}
```

### Branding
Update branding elements:
- Logo/title in `index.html`
- Favicon (add to `/web-ui/` directory)
- Footer text and links
- About modal content

### Feature Customization
- Modify polling interval in `APP_CONFIG`
- Change file size limits
- Add/remove supported formats
- Customize UI text and messages

## API Integration

### API Endpoints Used
The UI integrates with these API endpoints:

- `GET /health` - API health check
- `POST /upload` - Initiate file upload
- `GET /results/{jobId}/status` - Get job status
- `GET /results/{jobId}` - Get complete results
- `GET /results/{jobId}/download/{format}` - Download results

### Error Handling
The UI handles all API error scenarios:
- Network connectivity issues
- API server errors (5xx)
- Client errors (4xx)
- Timeout scenarios
- Invalid responses

## Deployment Checklist

### Pre-Deployment
- [ ] Update `APP_CONFIG.API_BASE_URL` with correct API Gateway URL
- [ ] Test API connectivity from local development
- [ ] Verify all features work with actual backend
- [ ] Update any branding/customization
- [ ] Test responsive design on multiple devices

### Deployment Steps
- [ ] Deploy infrastructure with CDK
- [ ] Get API Gateway URL from CDK outputs
- [ ] Update web UI configuration
- [ ] Sync files to S3 bucket
- [ ] Test deployed application
- [ ] Verify CORS and connectivity

### Post-Deployment
- [ ] Test complete upload → processing → results workflow
- [ ] Verify download functionality
- [ ] Check mobile responsiveness
- [ ] Test error scenarios
- [ ] Monitor for any console errors

## Production Deployment

### Infrastructure Updates for Production

1. **Update CDK for production:**
```typescript
// Change in core-stack.ts for production
removalPolicy: cdk.RemovalPolicy.RETAIN, // Don't destroy data
autoDeleteObjects: false, // Keep data on stack deletion
```

2. **Enable CloudFront (optional):**
```typescript
// Add CloudFront distribution for better performance
const distribution = new cloudfront.Distribution(this, 'WebDistribution', {
    defaultBehavior: {
        origin: new origins.S3Origin(webBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    },
});
```

3. **Custom domain setup:**
```typescript
// Add custom domain and SSL certificate
const certificate = new acm.Certificate(this, 'Certificate', {
    domainName: 'vehicle-analysis.yourcompany.com',
    validation: acm.CertificateValidation.fromDns(),
});
```

### Production Checklist
- [ ] Use production API Gateway URL
- [ ] Enable HTTPS-only access
- [ ] Configure proper CORS origins (not `*`)
- [ ] Set up monitoring and alerting
- [ ] Configure backup and disaster recovery
- [ ] Document access URLs and credentials
- [ ] Set up user training documentation

---

## Complete Deployment Example

Here's a complete deployment workflow:

```bash
#!/bin/bash
# Complete deployment script

set -e

echo "🚀 Deploying Vehicle Analysis System"
echo "===================================="

# 1. Deploy infrastructure
echo "📦 Deploying infrastructure..."
cd infrastructure
npm run build
cdk deploy --all -c environment=dev --require-approval never

# 2. Get API Gateway URL
echo "🔗 Getting API Gateway URL..."
API_URL=$(aws cloudformation describe-stacks \
  --stack-name VehicleAnalysis-ApiGateway-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
  --output text)

echo "API Gateway URL: $API_URL"

# 3. Update web UI configuration
echo "⚙️  Updating web UI configuration..."
cd ../web-ui
sed -i "s|API_BASE_URL: '.*'|API_BASE_URL: '$API_URL'|g" index.html

# 4. Get web bucket name
WEB_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name VehicleAnalysis-Core-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebBucketName`].OutputValue' \
  --output text)

# 5. Deploy web UI
echo "🌐 Deploying web UI to S3..."
aws s3 sync . s3://$WEB_BUCKET/ --delete

# 6. Get website URL
WEBSITE_URL=$(aws cloudformation describe-stacks \
  --stack-name VehicleAnalysis-Core-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
  --output text)

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Web UI: $WEBSITE_URL"
echo "🔗 API:    $API_URL"
echo ""
echo "📋 Next steps:"
echo "   1. Open the web UI URL in your browser"
echo "   2. Test upload functionality with a sample video"
echo "   3. Monitor the jobs section for processing status"
echo "   4. Review results when analysis completes"
echo ""
```

The Vehicle Analysis Web UI is now fully implemented and ready for deployment! 🎉
