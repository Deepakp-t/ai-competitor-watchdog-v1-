#!/usr/bin/env python3
"""
Minimal test script to verify Slack Incoming Webhook integration.
Sends a single test message to Slack using Block Kit formatting.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def send_test_message():
    """Send a test message to Slack via webhook"""
    
    # Read webhook URL from environment variable
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        print("ERROR: SLACK_WEBHOOK_URL environment variable not set")
        print("Please set it in your .env file or export it as an environment variable")
        sys.exit(1)
    
    # Create test message using Slack Block Kit
    message = {
        "text": "Test alert from Competitor Watchdog V1",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🧪 Test Alert from Competitor Watchdog V1"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This is a *test message* to verify Slack webhook integration.\n\n✅ If you see this message, your Slack integration is working correctly!"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Test sent from Competitor Watchdog V1"
                    }
                ]
            }
        ]
    }
    
    # Send message to Slack
    try:
        print(f"Sending test message to Slack...")
        response = requests.post(
            webhook_url,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        print("SUCCESS: Test message sent to Slack!")
        print(f"Response status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to send message to Slack")
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return False


if __name__ == "__main__":
    success = send_test_message()
    sys.exit(0 if success else 1)
