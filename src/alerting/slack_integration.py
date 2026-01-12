"""
Slack integration for sending alerts
"""
import os
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SlackIntegration:
    """Handles Slack webhook integration and message formatting"""
    
    def __init__(self, webhook_url: str = None):
        """
        Initialize Slack integration
        
        Args:
            webhook_url: Slack webhook URL (defaults to env var)
        """
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL not found in environment variables")
    
    def format_message(self, company: str, priority: str, asset: str, 
                      change_type: str, summary: str, why_it_matters: str,
                      url: str, timestamp: datetime) -> Dict[str, Any]:
        """
        Format alert message according to fixed schema
        
        Args:
            company: Competitor company name
            priority: Priority level (high, medium, low)
            asset: Asset type
            change_type: Type of change
            summary: Summary (Before → After)
            why_it_matters: Why it matters explanation
            url: URL of the changed asset
            timestamp: Detection timestamp
        
        Returns:
            Slack message payload (Block Kit format)
        """
        # Format timestamp
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Priority emoji
        priority_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }.get(priority.lower(), '⚪')
        
        # Build message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{priority_emoji} Competitor Change Detected"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Company:*\n{company}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:*\n{priority.upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Asset:*\n{asset}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Change Type:*\n{change_type}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary (Before → After):*\n{summary}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Why It Matters:*\n{why_it_matters}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Citation:*\n<{url}|{url}>\n(Detected: {timestamp_str})"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        return {
            "text": f"Competitive Intelligence Alert: {company} - {change_type}",
            "blocks": blocks
        }
    
    def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message to Slack via webhook
        
        Args:
            message: Slack message payload
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            logger.info("Slack message sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return False
    
    def send_alert(self, company: str, priority: str, asset: str,
                   change_type: str, summary: str, why_it_matters: str,
                   url: str, timestamp: datetime) -> bool:
        """
        Format and send an alert to Slack
        
        Args:
            company: Competitor company name
            priority: Priority level
            asset: Asset type
            change_type: Type of change
            summary: Summary
            why_it_matters: Why it matters
            url: URL
            timestamp: Detection timestamp
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = self.format_message(
            company=company,
            priority=priority,
            asset=asset,
            change_type=change_type,
            summary=summary,
            why_it_matters=why_it_matters,
            url=url,
            timestamp=timestamp
        )
        
        return self.send_message(message)
    
    def format_digest(self, alerts: list, title: str, priority: str = None) -> Dict[str, Any]:
        """
        Format a digest message (daily or weekly)
        
        Args:
            alerts: List of alert dictionaries with change information
            title: Digest title (e.g., "Daily Digest", "Weekly Summary")
            priority: Priority level if filtering by priority
        
        Returns:
            Slack message payload
        """
        if not alerts:
            return None
        
        # Build digest blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 {title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{len(alerts)} change(s) detected*"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Group by company
        by_company = {}
        for alert in alerts:
            company = alert.get('company', 'Unknown')
            if company not in by_company:
                by_company[company] = []
            by_company[company].append(alert)
        
        # Add sections for each company
        for company, company_alerts in by_company.items():
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{company}* ({len(company_alerts)} change(s))"
                }
            })
            
            for alert in company_alerts:
                priority_emoji = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(alert.get('priority', 'medium').lower(), '⚪')
                
                summary = alert.get('summary', 'No summary')
                url = alert.get('url', '')
                change_type = alert.get('change_type', 'unknown')
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{priority_emoji} *{change_type}*: {summary}\n<{url}|View changes>"
                    }
                })
            
            blocks.append({"type": "divider"})
        
        return {
            "text": f"{title}: {len(alerts)} changes",
            "blocks": blocks
        }
    
    def send_digest(self, alerts: list, title: str, priority: str = None) -> bool:
        """
        Format and send a digest message
        
        Args:
            alerts: List of alert dictionaries
            title: Digest title
            priority: Priority level filter
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = self.format_digest(alerts, title, priority)
        if not message:
            logger.info(f"No alerts to send in {title}")
            return True  # Not an error, just no alerts
        
        return self.send_message(message)

