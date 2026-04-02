PYTHON_VERSION ?= 3.11

help:
	@echo "==============================================="
	@echo "SLACK APP LAMBDA COMMANDS"
	@echo "==============================================="
	@echo ""
	@echo "make setup    : Show Slack app setup guide"
	@echo "make run      : Test the lambda function locally"
	@echo "make deploy   : Deploy lambda with guided setup"
	@echo "make update   : Quick code-only update (no secrets/config)"
	@echo "make delete   : Delete everything (start from scratch)"
	@echo "make libs     : Install dependencies"
	@echo "make clean    : Clean build artifacts"
	@echo ""

setup:
	@echo "==============================================="
	@echo "SLACK APP SETUP GUIDE"
	@echo "==============================================="
	@echo ""
	@echo "Step 1: Create Slack App"
	@echo "   1. Go to: https://api.slack.com/apps"
	@echo "   2. Click 'Create New App' -> 'From scratch'"
	@echo "   3. Enter app name and select workspace"
	@echo ""
	@echo "Step 2: Configure Bot Token Scopes"
	@echo "   1. Navigate to 'OAuth & Permissions'"
	@echo "   2. Add Bot Token Scopes:"
	@echo "      - commands (for slash commands)"
	@echo "      - users:read (user info)"
	@echo "      - users:read.email (email access)"
	@echo "      - users.profile:read (profile data)"
	@echo "      - im:write (direct messages)"
	@echo "      - chat:write (send messages)"
	@echo ""
	@echo "Step 3: Enable Interactive Components"
	@echo "   1. Go to 'Interactive Components'"
	@echo "   2. Enable and set Request URL (provided after deployment)"
	@echo ""
	@echo "Step 4: Create Slash Command"
	@echo "   1. Navigate to 'Slash Commands'"
	@echo "   2. Create command (e.g., /metadata)"
	@echo "   3. Set Request URL (same as interactive components)"
	@echo ""
	@echo "Step 5: Install App"
	@echo "   1. Go to 'Install App' -> Install to workspace"
	@echo "   2. Copy the Bot User OAuth Token (starts with xoxb-)"
	@echo ""
	@echo "Step 6: Get Required Info"
	@echo "   - Bot User OAuth Token (xoxb-...)"
	@echo "   - Signing Secret (from Basic Information)"
	@echo "   - User IDs for restrictions (optional)"
	@echo ""
	@echo "Ready? Run 'make deploy' to continue!"
	@echo ""

libs:
	@if [ ! -d .virtualenv ]; then virtualenv .virtualenv; fi
	@. .virtualenv/bin/activate && pip install -r requirements.txt

run: libs
	@. .virtualenv/bin/activate && python3 main.py

deploy: libs
	@./deploy.sh

update: libs
	@./update-code.sh

delete:
	@./delete.sh

clean:
	@rm -rf .virtualenv
	@rm -f deployment-package.zip
	@rm -f nohup.out

.PHONY: help setup run deploy update delete libs clean
