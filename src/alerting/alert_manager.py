"""
Alert manager for routing and delivering alerts based on priority
"""
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.storage.database import DatabaseSession
from src.storage.models import Change, Asset, Competitor, Alert
from src.alerting.slack_integration import SlackIntegration

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alert delivery based on priority and schedule"""
    
    def __init__(self, slack_webhook_url: str = None):
        """
        Initialize alert manager
        
        Args:
            slack_webhook_url: Slack webhook URL (optional, uses env var if not provided)
        """
        try:
            self.slack = SlackIntegration(slack_webhook_url)
            self.has_slack = True
        except Exception as e:
            logger.warning(f"Slack integration not available: {e}. Alerts will be queued but not sent.")
            self.slack = None
            self.has_slack = False
    
    def send_immediate_alert(self, change: Change) -> bool:
        """
        Send immediate alert for high-priority changes
        
        Args:
            change: Change object to alert about
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.has_slack:
            logger.warning("Slack not available, cannot send immediate alert")
            return False
        
        if change.priority != 'high':
            logger.debug(f"Change {change.id} is not high priority, skipping immediate alert")
            return False
        
        # Get asset and competitor info
        with DatabaseSession() as session:
            change = session.query(Change).filter(Change.id == change.id).first()
            asset = session.query(Asset).filter(Asset.id == change.asset_id).first()
            if not asset:
                logger.error(f"Asset {change.asset_id} not found for change {change.id}")
                return False
            
            competitor = session.query(Competitor).filter(Competitor.id == asset.competitor_id).first()
            if not competitor:
                logger.error(f"Competitor not found for asset {asset.id}")
                return False
        
        # Send alert
        success = self.slack.send_alert(
            company=competitor.name,
            priority=change.priority or 'medium',
            asset=asset.asset_type,
            change_type=change.change_type or 'unknown',
            summary=change.summary or 'Change detected',
            why_it_matters=change.why_it_matters or 'Monitor for competitive intelligence',
            url=asset.url,
            timestamp=change.detected_at or datetime.utcnow()
        )
        
        if success:
            # Record alert
            with DatabaseSession() as session:
                alert = Alert(
                    change_id=change.id,
                    priority=change.priority or 'medium',
                    sent_at=datetime.utcnow(),
                    delivery_type='immediate'
                )
                session.add(alert)
                
                # Mark change as alerted
                change = session.query(Change).filter(Change.id == change.id).first()
                change.alert_sent = True
                change.alert_sent_at = datetime.utcnow()
                session.commit()
            
            logger.info(f"Sent immediate alert for change {change.id}")
        
        return success
    
    def get_pending_alerts(self, priority: str = None, 
                          since: datetime = None) -> List[Change]:
        """
        Get pending alerts that haven't been sent yet
        
        Args:
            priority: Filter by priority (high, medium, low)
            since: Only get changes detected since this time
        
        Returns:
            List of Change objects
        """
        with DatabaseSession() as session:
            query = session.query(Change)\
                .join(Asset)\
                .filter(Change.alert_sent == False)\
                .filter(Change.priority != None)  # Only classified changes
            
            if priority:
                query = query.filter(Change.priority == priority)
            
            if since:
                query = query.filter(Change.detected_at >= since)
            
            return query.all()
    
    def send_daily_digest(self):
        """Send daily digest of medium-priority changes"""
        if not self.has_slack:
            logger.warning("Slack not available, cannot send daily digest")
            return
        
        # Get medium-priority changes from last 24 hours that haven't been alerted
        since = datetime.utcnow() - timedelta(days=1)
        changes = self.get_pending_alerts(priority='medium', since=since)
        
        if not changes:
            logger.info("No medium-priority changes for daily digest")
            return
        
        # Format alerts
        alerts = []
        change_ids = []
        
        with DatabaseSession() as session:
            for change in changes:
                asset = session.query(Asset).filter(Asset.id == change.asset_id).first()
                competitor = session.query(Competitor).filter(Competitor.id == asset.competitor_id).first()
                
                alerts.append({
                    'company': competitor.name,
                    'priority': change.priority,
                    'asset': asset.asset_type,
                    'change_type': change.change_type or 'unknown',
                    'summary': change.summary or 'Change detected',
                    'why_it_matters': change.why_it_matters or 'Monitor for competitive intelligence',
                    'url': asset.url,
                    'timestamp': change.detected_at
                })
                change_ids.append(change.id)
        
        # Send digest
        success = self.slack.send_digest(
            alerts=alerts,
            title="Daily Competitive Intelligence Digest",
            priority='medium'
        )
        
        if success:
            # Mark changes as alerted
            with DatabaseSession() as session:
                for change_id in change_ids:
                    change = session.query(Change).filter(Change.id == change_id).first()
                    if change:
                        change.alert_sent = True
                        change.alert_sent_at = datetime.utcnow()
                        
                        alert = Alert(
                            change_id=change.id,
                            priority=change.priority,
                            sent_at=datetime.utcnow(),
                            delivery_type='daily_digest'
                        )
                        session.add(alert)
                
                session.commit()
            
            logger.info(f"Sent daily digest with {len(alerts)} medium-priority changes")
    
    def send_weekly_summary(self):
        """Send weekly summary of low-priority changes"""
        if not self.has_slack:
            logger.warning("Slack not available, cannot send weekly summary")
            return
        
        # Get low-priority changes from last 7 days that haven't been alerted
        since = datetime.utcnow() - timedelta(days=7)
        changes = self.get_pending_alerts(priority='low', since=since)
        
        if not changes:
            logger.info("No low-priority changes for weekly summary")
            return
        
        # Format alerts
        alerts = []
        change_ids = []
        
        with DatabaseSession() as session:
            for change in changes:
                asset = session.query(Asset).filter(Asset.id == change.asset_id).first()
                competitor = session.query(Competitor).filter(Competitor.id == asset.competitor_id).first()
                
                alerts.append({
                    'company': competitor.name,
                    'priority': change.priority,
                    'asset': asset.asset_type,
                    'change_type': change.change_type or 'unknown',
                    'summary': change.summary or 'Change detected',
                    'why_it_matters': change.why_it_matters or 'Monitor for competitive intelligence',
                    'url': asset.url,
                    'timestamp': change.detected_at
                })
                change_ids.append(change.id)
        
        # Send summary
        success = self.slack.send_digest(
            alerts=alerts,
            title="Weekly Competitive Intelligence Summary",
            priority='low'
        )
        
        if success:
            # Mark changes as alerted
            with DatabaseSession() as session:
                for change_id in change_ids:
                    change = session.query(Change).filter(Change.id == change_id).first()
                    if change:
                        change.alert_sent = True
                        change.alert_sent_at = datetime.utcnow()
                        
                        alert = Alert(
                            change_id=change.id,
                            priority=change.priority,
                            sent_at=datetime.utcnow(),
                            delivery_type='weekly_summary'
                        )
                        session.add(alert)
                
                session.commit()
            
            logger.info(f"Sent weekly summary with {len(alerts)} low-priority changes")
    
    def process_pending_alerts(self):
        """
        Process all pending alerts based on priority
        
        - High priority: Send immediately
        - Medium priority: Queue for daily digest
        - Low priority: Queue for weekly summary
        """
        # Get all pending high-priority changes and send immediately
        high_priority = self.get_pending_alerts(priority='high')
        for change in high_priority:
            try:
                self.send_immediate_alert(change)
            except Exception as e:
                logger.error(f"Error sending immediate alert for change {change.id}: {e}", exc_info=True)
        
        # Medium and low priority are handled by scheduled digests
        logger.info(f"Processed {len(high_priority)} high-priority alerts")
    
    def start_scheduler(self):
        """Start alert delivery scheduler"""
        if not self.has_slack:
            logger.warning("Slack not available, alert scheduler will not send messages")
        
        # Schedule daily digest at 9 AM
        schedule.every().day.at("09:00").do(self.send_daily_digest)
        
        # Schedule weekly summary on Monday at 9 AM
        schedule.every().monday.at("09:00").do(self.send_weekly_summary)
        
        logger.info("Alert scheduler started:")
        logger.info("  - Daily digest: 9:00 AM daily")
        logger.info("  - Weekly summary: Monday 9:00 AM")
        
        # Process pending high-priority alerts immediately
        self.process_pending_alerts()
        
        # Run scheduler loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Alert scheduler stopped by user")

