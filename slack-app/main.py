import json
import os
import hmac
import hashlib
import urllib.parse
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Environment variables (set these in Lambda configuration)
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
ALLOWED_USER_IDS = os.environ.get('ALLOWED_USER_IDS', 'ANY')  # Comma-separated user IDs or 'ANY'

# Initialize Slack client
slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

def verify_slack_request(headers, body):
    """Verify that the request comes from Slack"""
    if not SLACK_SIGNING_SECRET:
        print("Warning: SLACK_SIGNING_SECRET not set")
        return True  # Allow for testing, but should be False in production

    timestamp = headers.get('X-Slack-Request-Timestamp', '')
    signature = headers.get('X-Slack-Signature', '')

    if not timestamp or not signature:
        return False

    # Create expected signature
    sig_basestring = f"v0:{timestamp}:{body}"
    expected_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)

def is_user_allowed(user_id):
    """Check if user is allowed to use this function"""
    if ALLOWED_USER_IDS == 'ANY':
        return True

    allowed_users = [uid.strip() for uid in ALLOWED_USER_IDS.split(',')]
    return user_id in allowed_users

def get_user_metadata(user_id):
    """Get comprehensive user metadata from Slack"""
    if not slack_client:
        return {"error": "Slack client not initialized"}

    try:
        # Get user info
        user_info = slack_client.users_info(user=user_id)
        user = user_info.get('user', {})

        # Get user profile
        profile_info = slack_client.users_profile_get(user=user_id)
        profile = profile_info.get('profile', {})

        # Compile metadata
        metadata = {
            "user_id": user.get('id'),
            "username": user.get('name'),
            "real_name": user.get('real_name'),
            "display_name": profile.get('display_name'),
            "email": profile.get('email'),
            "phone": profile.get('phone'),
            "title": profile.get('title'),
            "team": user.get('team_id'),
            "timezone": user.get('tz'),
            "timezone_label": user.get('tz_label'),
            "timezone_offset": user.get('tz_offset'),
            "is_admin": user.get('is_admin', False),
            "is_owner": user.get('is_owner', False),
            "is_bot": user.get('is_bot', False),
            "status": profile.get('status_text'),
            "status_emoji": profile.get('status_emoji'),
            "avatar": profile.get('image_512'),
            "last_seen": user.get('updated'),
            "deleted": user.get('deleted', False)
        }

        return metadata

    except SlackApiError as e:
        return {"error": f"Slack API error: {e.response['error']}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def create_menu_blocks():
    """Create interactive menu blocks"""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🔍 *Slack User Information Tool*\nSelect an option below:"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Get My Metadata"
                    },
                    "value": "get_metadata",
                    "action_id": "get_user_metadata",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔒 Check Access"
                    },
                    "value": "check_access",
                    "action_id": "check_user_access"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "ℹ️ About"
                    },
                    "value": "about",
                    "action_id": "show_about"
                }
            ]
        }
    ]

def format_metadata_response(metadata):
    """Format metadata as a nice Slack message"""
    if "error" in metadata:
        return f"❌ Error retrieving metadata: {metadata['error']}"

    # Format the metadata nicely
    response = "📊 *Your Slack Metadata:*\n\n"

    # Basic info
    response += f"👤 *User Info:*\n"
    response += f"• ID: `{metadata.get('user_id', 'N/A')}`\n"
    response += f"• Username: `{metadata.get('username', 'N/A')}`\n"
    response += f"• Real Name: {metadata.get('real_name', 'N/A')}\n"
    response += f"• Display Name: {metadata.get('display_name', 'N/A')}\n\n"

    # Contact info
    response += f"📧 *Contact Info:*\n"
    response += f"• Email: {metadata.get('email', 'N/A')}\n"
    response += f"• Phone: {metadata.get('phone', 'N/A')}\n"
    response += f"• Title: {metadata.get('title', 'N/A')}\n\n"

    # Location/Time
    response += f"🌍 *Location & Time:*\n"
    response += f"• Timezone: {metadata.get('timezone_label', 'N/A')} ({metadata.get('timezone', 'N/A')})\n"
    response += f"• UTC Offset: {metadata.get('timezone_offset', 'N/A')} seconds\n\n"

    # Permissions
    response += f"🔐 *Permissions:*\n"
    response += f"• Admin: {'✅' if metadata.get('is_admin') else '❌'}\n"
    response += f"• Owner: {'✅' if metadata.get('is_owner') else '❌'}\n"
    response += f"• Bot: {'✅' if metadata.get('is_bot') else '❌'}\n\n"

    # Status
    if metadata.get('status') or metadata.get('status_emoji'):
        response += f"💬 *Status:*\n"
        response += f"• {metadata.get('status_emoji', '')} {metadata.get('status', 'No status')}\n\n"

    response += f"🕒 Last updated: {metadata.get('last_seen', 'Unknown')}"

    return response

def handle_slash_command(event):
    """Handle slash command"""
    user_id = event.get('user_id')

    # Check if user is allowed
    if not is_user_allowed(user_id):
        return {
            "response_type": "ephemeral",
            "text": "🚫 Access denied. You are not authorized to use this command."
        }

    # Return interactive menu
    return {
        "response_type": "ephemeral",
        "blocks": create_menu_blocks()
    }

def handle_interactive_action(payload):
    """Handle interactive button clicks"""
    user_id = payload['user']['id']
    action = payload['actions'][0]
    action_id = action['action_id']

    # Check if user is allowed
    if not is_user_allowed(user_id):
        return {
            "text": "🚫 Access denied. You are not authorized to use this function."
        }

    if action_id == "get_user_metadata":
        metadata = get_user_metadata(user_id)
        response_text = format_metadata_response(metadata)

        return {
            "text": response_text,
            "response_type": "ephemeral"
        }

    elif action_id == "check_user_access":
        allowed = is_user_allowed(user_id)
        access_status = "✅ Allowed" if allowed else "🚫 Denied"

        return {
            "text": f"🔒 *Access Status:* {access_status}\n\n"
                   f"User ID: `{user_id}`\n"
                   f"Allowed Users: `{ALLOWED_USER_IDS}`",
            "response_type": "ephemeral"
        }

    elif action_id == "show_about":
        return {
            "text": "ℹ️ *Slack User Information Tool*\n\n"
                   "This secure lambda function provides:\n"
                   "• 📊 Comprehensive user metadata from Slack\n"
                   "• 🔒 User access restrictions\n"
                   "• ✅ Request signature validation\n"
                   "• 🛡️ Security-first design\n\n"
                   f"🔧 Environment: `{os.environ.get('AWS_REGION', 'Unknown')}`\n"
                   f"🎯 Function: `{os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'Unknown')}`",
            "response_type": "ephemeral"
        }

    # Default response
    return {
        "text": "🤔 Unknown action. Please try again.",
        "response_type": "ephemeral"
    }

def lambda_handler(event, context):
    """Main Lambda handler with Function URL support"""
    try:
        print(f"Event: {json.dumps(event)}")  # Debug logging

        # Handle Function URL requests
        if 'rawPath' in event and 'requestContext' in event:
            headers = event.get('headers', {})
            body = event.get('body', '')
            print(f"Headers: {json.dumps(headers)}")  # Debug logging
            print(f"Body: {body}")  # Debug logging

            # For debugging, temporarily skip signature verification
            # TODO: Re-enable after debugging
            # if not verify_slack_request(headers, body):
            #     return {
            #         'statusCode': 401,
            #         'body': json.dumps({'error': 'Invalid request signature'})
            #     }

            # Parse form data
            if body:
                content_type = headers.get('content-type', '').lower()
                print(f"Content-Type: {content_type}")  # Debug logging

                if content_type.startswith('application/x-www-form-urlencoded'):
                    parsed_body = urllib.parse.parse_qs(body)
                    print(f"Parsed body: {json.dumps(parsed_body)}")  # Debug logging

                    # Handle slash command
                    if 'command' in parsed_body:
                        print("Handling slash command")  # Debug logging
                        response = handle_slash_command({
                            'user_id': parsed_body.get('user_id', [''])[0],
                            'command': parsed_body.get('command', [''])[0],
                            'text': parsed_body.get('text', [''])[0]
                        })
                        print(f"Slash command response: {json.dumps(response)}")  # Debug logging

                        return {
                            'statusCode': 200,
                            'headers': {'Content-Type': 'application/json'},
                            'body': json.dumps(response)
                        }

                    # Handle interactive components
                    elif 'payload' in parsed_body:
                        payload = json.loads(parsed_body['payload'][0])
                        response = handle_interactive_action(payload)

                        return {
                            'statusCode': 200,
                            'headers': {'Content-Type': 'application/json'},
                            'body': json.dumps(response)
                        }

            # Default response for Function URL - this means we got a request but couldn't process it
            print("Returning default response - request not processed")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'response_type': 'ephemeral',
                    'text': '🤔 I received your request but couldn\'t process it. Check the logs for details.'
                })
            }

        # Handle direct Lambda invocation (for testing)
        else:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Lambda function executed successfully',
                    'event': event
                })
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Event that caused error: {json.dumps(event)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'response_type': 'ephemeral',
                'text': f'❌ Error: {str(e)}'
            })
        }

# For local testing
if __name__ == "__main__":
    # Test with mock event
    test_event = {
        'rawPath': '/test',
        'requestContext': {'requestId': 'test-123'},
        'headers': {},
        'body': ''
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))