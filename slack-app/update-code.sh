#!/bin/bash
set -e

echo "🔄 Quick Code Update for Slack Lambda"
echo "====================================="
echo ""

REGION=${REGION:-us-east-1}
FUNCTION_NAME="slack-app"

# Check if function exists
if ! aws lambda get-function --region $REGION --function-name $FUNCTION_NAME &> /dev/null; then
    echo "❌ Function '$FUNCTION_NAME' not found. Run 'make deploy' first."
    exit 1
fi

echo "📦 Building deployment package..."

# Install/update dependencies if needed
if [ ! -d .virtualenv ]; then
    echo "📥 Installing dependencies..."
    virtualenv .virtualenv
    . .virtualenv/bin/activate && pip install -r requirements.txt
else
    echo "✅ Using existing virtual environment"
fi

# Detect actual Python version in virtualenv
PYTHON_SITE_PACKAGES=$(find .virtualenv/lib -name "site-packages" -type d | head -1)
echo "📂 Using site-packages: $PYTHON_SITE_PACKAGES"

# Create deployment package
echo "📦 Creating deployment package..."
# First, create zip with main.py
zip -q deployment-package.zip main.py

# Then add all dependencies from site-packages
cd $PYTHON_SITE_PACKAGES
zip -r -q ../../../deployment-package.zip *
cd -

echo "📦 Deployment package created: $(ls -lh deployment-package.zip | awk '{print $5}')"

# Update function code only
echo "🚀 Updating Lambda function code..."
aws lambda update-function-code \
    --region $REGION \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://deployment-package.zip > /dev/null

echo "✅ Code updated successfully!"

# Get function URL for reference
echo ""
echo "🔗 Function URL:"
aws lambda get-function-url-config \
    --region $REGION \
    --function-name $FUNCTION_NAME \
    --query 'FunctionUrl' \
    --output text

echo ""
echo "🧪 Test your Slack command now!"

# Clean up
rm -f deployment-package.zip