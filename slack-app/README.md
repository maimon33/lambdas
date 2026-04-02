# Slack App Lambda

A secure Lambda function that integrates with Slack apps, providing user metadata retrieval and security features.

## Slack App Setup Guide

**Follow these steps BEFORE deploying the lambda:**

### Step 1: Create Slack App
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Enter app name and select workspace

### Step 2: Configure Bot Token Scopes
1. Navigate to **OAuth & Permissions**
2. Add these Bot Token Scopes:
   - `commands` (for slash commands)
   - `users:read` (user info)
   - `users:read.email` (email access)
   - `users.profile:read` (profile data)
   - `im:write` (direct messages)
   - `chat:write` (send messages)

### Step 3: Enable Interactive Components
1. Go to **Interactive Components**
2. Enable and set Request URL: `[LAMBDA_FUNCTION_URL]` (will be provided after deployment)

### Step 4: Create Slash Command
1. Navigate to **Slash Commands**
2. Create command (e.g., `/metadata`)
3. Set Request URL: `[LAMBDA_FUNCTION_URL]` (same as interactive components)

### Step 5: Install App
1. Go to **Install App** → Install to workspace
2. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 6: Get Required Tokens
Copy these values for lambda environment variables:
- **SLACK_BOT_TOKEN**: Bot User OAuth Token (`xoxb-...`)
- **SLACK_SIGNING_SECRET**: From Basic Information → App Credentials
- **ALLOWED_USER_IDS**: Comma-separated list of Slack user IDs (optional, use "ANY" to allow all)

### Step 7: Update Slack App URLs (After Lambda Deployment)
After deploying this lambda, update the following in your Slack app:
- Interactive Components Request URL
- Slash Command Request URL

## Features

- **Secure User Metadata Retrieval**: Get comprehensive user information from Slack
- **User Restriction**: Optionally limit access to specific Slack users
- **Interactive Menus**: Pop-up menu with various options
- **Request Signature Validation**: Verifies requests are from Slack

## Deployment

Run `make deploy` from this directory after setting up your Slack app.