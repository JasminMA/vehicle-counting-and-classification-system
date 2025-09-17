# Vehicle Analysis System

> AI-powered vehicle counting and classification system using AWS services

## ✨ Features

- 🚗 **Vehicle Detection** - Automatically detect cars, trucks, motorcycles, buses
- 📊 **Real-time Analytics** - Get detailed counts and classifications
- ☁️ **Cloud Native** - Built on AWS Lambda, S3, and Rekognition
- 🔄 **Async Processing** - Upload videos and get results when ready
- 📱 **Web Interface** - Easy-to-use web UI for uploads and results

## 🚀 Quick Start

### Prerequisites
- **Python 3.13** ([Download](https://python.org/downloads/))
- **Node.js 18+** ([Download](https://nodejs.org/))
- **AWS CLI** ([Setup Guide](https://aws.amazon.com/cli/))

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/JasminMA/vehicle-counting-system.git
cd vehicle-counting-system

# Install dependencies
pip install -r requirements.txt
cd infrastructure && npm install
```

### 2. AWS Setup
```bash
# Configure AWS credentials
aws configure

# Bootstrap CDK (one-time setup)
npx cdk bootstrap
```

### 3. Deploy
```bash
# Deploy to development
cd infrastructure
npx cdk deploy --all -c environment=dev
```

### 4. Run Frontend
```bash
# Navigate to web-ui directory
cd web-ui

# Start local development server
python -m http.server 8000

# Open in browser
# http://localhost:8000
```

### 5. Use the System
1. **Upload** a video file through the web UI
2. **Wait** for processing (2-5 minutes for typical videos)
3. **View** results with vehicle counts and timeline

## 📁 Project Structure

```
vehicle-counting-system/
├── 🏗️ infrastructure/          # AWS CDK infrastructure
├── ⚡ lambda/                  # Lambda functions
│   ├── upload-handler/         # Handle file uploads
│   ├── video-processor/        # Process videos with AI
│   ├── results-processor/      # Analyze AI results
│   └── results-api/           # Serve results via API
├── 🌐 web-ui/                 # Frontend web interface
└── 📋 scripts/                # Deployment utilities
```

## 🛠️ Development

### Run Tests
```bash
# Python tests
python -m pytest lambda/tests/ -v

# Infrastructure tests
cd infrastructure && npm test
```

### Local Development
```bash
# Build infrastructure
cd infrastructure && npm run build

# Deploy single stack
npx cdk deploy VehicleAnalysis-Lambda-dev

# Run frontend locally
cd web-ui
python -m http.server 8000
# Then open http://localhost:8000
```

## 📊 Supported Formats

| Format | Support | Notes |
|--------|---------|--------|
| MP4 | ✅ | Recommended |
| MOV | ✅ | Good compatibility |
| AVI | ✅ | Basic support |
| MKV | ✅ | Basic support |
| WEBM | ✅ | Basic support |

**File size limit**: 8GB  
**Processing time**: 2-10 minutes depending on video length

## 🔧 Configuration

### Environment Variables
```bash
# Required for deployment
AWS_REGION=us-east-1
ENVIRONMENT=dev
```

### Costs
- **S3 Storage**: ~$0.023/GB/month
- **Lambda**: ~$0.20 per 1M requests
- **Rekognition**: ~$0.10 per minute of video
- **API Gateway**: ~$3.50 per 1M requests

*Typical cost for processing a 5-minute video: ~$0.50*

## 📚 API Reference

### Upload Video
```http
POST /upload
Content-Type: application/json

{
  "filename": "video.mp4",
  "filesize": 50000000
}
```

### Get Results
```http
GET /results/{jobId}
```

### Check Status
```http
GET /results/{jobId}/status
```

## 🚦 System Status

| Component | Status | Version |
|-----------|--------|---------|
| Infrastructure | ✅ Ready | Python 3.13 |
| Upload Handler | ✅ Ready | v1.0 |
| Video Processor | ✅ Ready | v1.0 |
| Results API | ✅ Ready | v1.0 |
| Web UI | ✅ Ready | v1.0 |

## 📝 Recent Updates

### Python 3.13 Upgrade ⚡
- **Performance**: Up to 18% faster execution
- **Security**: Extended support until 2030
- **Compatibility**: Ready for future AWS features

## 🐛 Troubleshooting

### Common Issues

**"Access Denied" error**
```bash
# Check AWS credentials
aws sts get-caller-identity
```

**Deploy fails with "Role already exists"**
```bash
# Destroy and recreate
npx cdk destroy --all
npx cdk deploy --all
```


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
