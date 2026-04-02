#!/bin/bash
set -e

echo "🔧 Fixing Lambda Function URL Authorization"
echo "=========================================="
echo ""

REGION=${REGION:-us-east-1}
FUNCTION_NAME="slack-app"

echo "📋 Current Function URL configuration:"
aws lambda get-function-url-config \
    --region $REGION \
    --function-name $FUNCTION_NAME 2>/dev/null || echo "❌ No Function URL found"

echo ""
echo "🔄 Deleting and recreating Function URL with correct auth..."

# Delete existing Function URL
aws lambda delete-function-url-config \
    --region $REGION \
    --function-name $FUNCTION_NAME 2>/dev/null || echo "No existing URL to delete"

# Create Function URL with NONE auth (public access for Slack)
echo "🔗 Creating new Function URL..."
FUNCTION_URL=$(aws lambda create-function-url-config \
    --region $REGION \
    --function-name $FUNCTION_NAME \
    --cors '{
        "AllowCredentials": false,
        "AllowHeaders": ["content-type", "x-slack-signature", "x-slack-request-timestamp"],
        "AllowMethods": ["POST"],
        "AllowOrigins": ["https://slack.com"],
        "MaxAge": 86400
    }' \
    --auth-type NONE \
    --query 'FunctionUrl' \
    --output text)

# Add resource-based policy for public access
echo "🔐 Adding public access permissions..."
aws lambda add-permission \
    --region $REGION \
    --function-name $FUNCTION_NAME \
    --statement-id FunctionURLAllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE 2>/dev/null || echo "Permission already exists"

echo ""
echo "✅ Function URL fixed!"
echo "🔗 New URL: $FUNCTION_URL"
echo ""
echo "📝 NEXT STEPS:"
echo "1. Copy this URL: $FUNCTION_URL"
echo "2. Go to your Slack app settings: https://api.slack.com/apps"
echo "3. Update these URLs:"
echo "   • Slash Commands → Request URL"
echo "   • Interactive Components → Request URL"
echo ""
echo "🧪 Test your slash command in Slack!"