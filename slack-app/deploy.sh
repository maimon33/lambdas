#!/bin/bash
set -e

# Display Slack setup guide
echo "==============================================="
echo "🚀 SLACK APP LAMBDA DEPLOYMENT"
echo "==============================================="
echo ""
echo "📋 BEFORE PROCEEDING, ENSURE YOU HAVE:"
echo ""
echo "1. ✅ Created Slack app at: https://api.slack.com/apps"
echo "2. ✅ Configured Bot Token Scopes (see README.md)"
echo "3. ✅ Your Bot User OAuth Token (xoxb-...)"
echo "4. ✅ Your Signing Secret"
echo ""
echo "⚠️  WARNING: You'll need to update Slack app URLs after deployment!"
echo ""

# Prompt for tokens
read -p "🔑 Enter your Slack Bot Token (xoxb-...): " SLACK_BOT_TOKEN
if [[ ! $SLACK_BOT_TOKEN =~ ^xoxb- ]]; then
    echo "❌ Invalid bot token format. Should start with 'xoxb-'"
    exit 1
fi

read -p "🔒 Enter your Slack Signing Secret: " SLACK_SIGNING_SECRET
if [[ -z "$SLACK_SIGNING_SECRET" ]]; then
    echo "❌ Signing secret cannot be empty"
    exit 1
fi

echo ""
echo "👥 User Access Control:"
echo "1) Allow ANY user (default)"
echo "2) Restrict to specific users"
read -p "Select option (1-2): " access_option

if [[ "$access_option" == "2" ]]; then
    read -p "📝 Enter comma-separated Slack User IDs: " ALLOWED_USER_IDS
else
    ALLOWED_USER_IDS="ANY"
fi

echo ""
echo "🏗️  Starting deployment..."
echo ""

REGION=${REGION:-us-east-1}
PYTHON_VERSION=${PYTHON_VERSION:-python3.11}
FUNCTION_NAME="slack-app"

user_info=$(aws sts get-caller-identity --output text || echo "Failed to auth AWS")
ACCOUNT_ID="`echo $user_info | awk ' {print $1} '`"
USER_NAME="`echo $user_info | awk ' {print $3} '`"

# Create IAM role if it doesn't exist
if ! aws iam list-roles --region $REGION | grep "${FUNCTION_NAME}LambdaRole" > /dev/null; then
    echo "🔧 Creating IAM role..."
    aws iam create-role --region $REGION --role-name "${FUNCTION_NAME}LambdaRole" \
    --assume-role-policy-document file://lambda-role-trust-policy.json

    echo "⏳ Waiting for IAM role to be ready..."
    sleep 10  # Wait for role to propagate
fi

aws iam put-role-policy --region $REGION --role-name "${FUNCTION_NAME}LambdaRole" \
    --policy-name "${FUNCTION_NAME}Policy" --policy-document file://lambda-role-policy.json

# Additional wait to ensure role is fully ready
echo "⏳ Ensuring IAM role is ready for Lambda..."
sleep 5

# Build deployment package
echo "📦 Building deployment package..."
if [ ! -d .virtualenv ]; then virtualenv .virtualenv; fi
. .virtualenv/bin/activate && pip install -r requirements.txt

# Detect actual Python version in virtualenv
PYTHON_SITE_PACKAGES=$(find .virtualenv/lib -name "site-packages" -type d | head -1)
echo "📂 Using site-packages: $PYTHON_SITE_PACKAGES"

# Create deployment package
echo "📦 Creating deployment package..."
# First, create zip with main.py
zip deployment-package.zip main.py

# Then add all dependencies from site-packages
cd $PYTHON_SITE_PACKAGES
zip -r -q ../../../deployment-package.zip *
cd -

echo "📦 Deployment package created: $(ls -lh deployment-package.zip | awk '{print $5}')"

# Create or update function
if ! aws lambda get-function --region $REGION --function-name $FUNCTION_NAME &> /dev/null; then
    echo "🚀 Creating Lambda function..."
    ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/${FUNCTION_NAME}LambdaRole"
    aws lambda create-function \
        --region $REGION \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://deployment-package.zip \
        --handler main.lambda_handler \
        --runtime $PYTHON_VERSION \
        --memory-size 512 \
        --timeout 30 \
        --role "$ROLE_ARN" > /dev/null
    echo "✅ Lambda function created successfully"
else
    echo "🔄 Function exists, updating code..."
    aws lambda update-function-code \
        --region $REGION \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://deployment-package.zip > /dev/null
    echo "✅ Lambda function updated successfully"
fi

# Set environment variables
echo "🔧 Setting environment variables..."
aws lambda update-function-configuration \
    --region $REGION \
    --function-name $FUNCTION_NAME \
    --environment "Variables={SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN,SLACK_SIGNING_SECRET=$SLACK_SIGNING_SECRET,ALLOWED_USER_IDS=$ALLOWED_USER_IDS}" > /dev/null
echo "✅ Environment variables set"

# Create Function URL
echo "🔗 Creating Function URL..."
FUNCTION_URL=$(aws lambda create-function-url-config \
    --region $REGION \
    --function-name $FUNCTION_NAME \
    --cors '{"AllowCredentials":false,"AllowMethods":["POST"],"AllowOrigins":["https://slack.com"]}' \
    --auth-type NONE \
    --query 'FunctionUrl' \
    --output text 2>/dev/null || \
aws lambda get-function-url-config \
    --region $REGION \
    --function-name $FUNCTION_NAME \
    --query 'FunctionUrl' \
    --output text)
echo "✅ Function URL configured"

echo ""
echo "==============================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "==============================================="
echo ""
echo "🔗 Function URL: $FUNCTION_URL"
echo ""
echo "📝 NEXT STEPS:"
echo "1. Copy the Function URL above"
echo "2. Go to https://api.slack.com/apps"
echo "3. Select your app"
echo "4. Update these settings with the Function URL:"
echo "   • Interactive Components → Request URL"
echo "   • Slash Commands → Request URL"
echo ""
echo "🧪 Test your slash command in Slack (e.g., /metadata)"
echo ""
echo "🛡️  Security Settings:"
echo "   • Bot Token: ${SLACK_BOT_TOKEN:0:10}..."
echo "   • Allowed Users: $ALLOWED_USER_IDS"
echo ""

# Clean up
rm -f deployment-package.zip