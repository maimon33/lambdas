#!/bin/bash

echo "🧪 Testing Slack App Lambda Function"
echo "===================================="
echo ""

# Set test environment variables
export SLACK_BOT_TOKEN="xoxb-test-token"
export SLACK_SIGNING_SECRET="test-secret"
export ALLOWED_USER_IDS="ANY"

echo "🔧 Environment:"
echo "  • Bot Token: ${SLACK_BOT_TOKEN}"
echo "  • Signing Secret: ${SLACK_SIGNING_SECRET}"
echo "  • Allowed Users: ${ALLOWED_USER_IDS}"
echo ""

if [ ! -d .virtualenv ]; then
    echo "📦 Installing dependencies..."
    make libs
    echo ""
fi

echo "▶️  Running local test..."
echo ""
. .virtualenv/bin/activate && python3 main.py