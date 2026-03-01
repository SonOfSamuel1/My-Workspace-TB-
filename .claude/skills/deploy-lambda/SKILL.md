---
description:
  Deploy a Python application to AWS Lambda with proper file structure and
  scripts
---

# Deploy to AWS Lambda

## Required File Structure

```text
apps/<app-name>/
├── lambda_handler.py           # Lambda entry point (top-level)
├── src/                        # Application source code
│   ├── __init__.py
│   └── <name>_main.py         # Main logic
├── scripts/
│   └── deploy-lambda-zip.sh   # Deployment script
├── requirements.txt            # Full dependencies
├── requirements-lambda.txt     # Lambda-specific deps (no dev deps)
└── Dockerfile.lambda           # Optional container deployment
```

## lambda_handler.py pattern

```python
import json
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from <name>_main import main_function

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    try:
        result = main_function()
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Success", "result": result})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
```

## Deployment script (deploy-lambda-zip.sh)

```bash
#!/bin/bash
set -euo pipefail

FUNCTION_NAME="your-function-name"
DEPLOYMENT_DIR="deployment"
PACKAGE_DIR="$DEPLOYMENT_DIR/package"

# Clean and create deployment directory
rm -rf "$DEPLOYMENT_DIR"
mkdir -p "$PACKAGE_DIR"

# Install dependencies
pip install -r requirements-lambda.txt -t "$PACKAGE_DIR"

# Copy application code
cp lambda_handler.py "$PACKAGE_DIR/"
cp -r src/ "$PACKAGE_DIR/src/"

# Create zip
cd "$PACKAGE_DIR"
zip -r "../deployment.zip" .
cd ../..

# Deploy to AWS
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$DEPLOYMENT_DIR/deployment.zip"

echo "Deployed $FUNCTION_NAME successfully"
```

## AWS Services Used

| Service         | Purpose                              |
| --------------- | ------------------------------------ |
| Lambda          | Serverless function execution        |
| Parameter Store | Secret management (API keys, tokens) |
| EventBridge     | Scheduled triggers (cron)            |
| CloudWatch      | Logs and monitoring                  |
| IAM             | Execution role and permissions       |

## Reading secrets from Parameter Store

```python
import boto3

def get_parameter(name):
    """Read secret from AWS Parameter Store."""
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response['Parameter']['Value']

API_TOKEN = get_parameter('/your-app/api-token')
```

## Deploy command

```bash
cd apps/<app-name>
./scripts/deploy-lambda-zip.sh
```
