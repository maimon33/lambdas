#!/bin/bash
set -e

echo "🗑️  Delete Slack Lambda Function and Resources"
echo "=============================================="
echo ""

REGION=${REGION:-us-east-1}
FUNCTION_NAME="slack-app"

echo "⚠️  This will DELETE:"
echo "   • Lambda function: $FUNCTION_NAME"
echo "   • Function URL configuration"
echo "   • IAM role: ${FUNCTION_NAME}LambdaRole"
echo "   • All permissions and policies"
echo ""

read -p "Are you sure? Type 'DELETE' to confirm: " confirmation
if [ "$confirmation" != "DELETE" ]; then
    echo "❌ Aborted"
    exit 1
fi

echo ""
echo "🗑️  Deleting resources..."

# Delete Function URL
echo "🔗 Deleting Function URL..."
aws lambda delete-function-url-config \
    --region $REGION \
    --function-name $FUNCTION_NAME 2>/dev/null || echo "  No Function URL to delete"

# Delete Lambda function
echo "⚡ Deleting Lambda function..."
aws lambda delete-function \
    --region $REGION \
    --function-name $FUNCTION_NAME 2>/dev/null || echo "  Function not found"

# Delete IAM role policy
echo "🔐 Deleting IAM role policy..."
aws iam delete-role-policy \
    --role-name "${FUNCTION_NAME}LambdaRole" \
    --policy-name "${FUNCTION_NAME}Policy" 2>/dev/null || echo "  Policy not found"

# Delete IAM role
echo "👤 Deleting IAM role..."
aws iam delete-role \
    --role-name "${FUNCTION_NAME}LambdaRole" 2>/dev/null || echo "  Role not found"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📝 NEXT STEPS:"
echo "1. Run 'make deploy' to create everything from scratch"
echo "2. Update your Slack app URLs with the new Function URL"
echo ""