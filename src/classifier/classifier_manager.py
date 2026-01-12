"""
Classifier manager that orchestrates classification and quality validation
"""
import logging
from typing import List, Optional
from datetime import datetime

from src.storage.database import DatabaseSession
from src.storage.models import Change, Asset
from src.classifier.change_classifier import ChangeClassifier
from src.classifier.priority_assigner import PriorityAssigner
from src.alerting.alert_manager import AlertManager

logger = logging.getLogger(__name__)


class ClassifierManager:
    """Manages classification of changes"""
    
    def __init__(self, alert_manager: AlertManager = None):
        """
        Initialize classifier manager
        
        Args:
            alert_manager: Optional alert manager for sending immediate alerts
        """
        try:
            self.classifier = ChangeClassifier()
            self.has_llm = True
        except Exception as e:
            logger.warning(f"LLM not available for classification: {e}. Will use rule-based classification.")
            self.classifier = None
            self.has_llm = False
        
        self.priority_assigner = PriorityAssigner()
        self.alert_manager = alert_manager
    
    def classify_change(self, change: Change) -> bool:
        """
        Classify a change and update it in the database
        
        Args:
            change: Change object to classify
        
        Returns:
            True if classification successful and change should be alerted, False otherwise
        """
        logger.info(f"Classifying change {change.id} for asset {change.asset_id}")
        
        try:
            # Get asset for context
            with DatabaseSession() as session:
                asset = session.query(Asset).filter(Asset.id == change.asset_id).first()
                if not asset:
                    logger.error(f"Asset {change.asset_id} not found for change {change.id}")
                    return False
                
                # Get change data from diff metadata
                change_data = {
                    'structured_diff': change.diff_metadata_json if isinstance(change.diff_metadata_json, dict) else None,
                    'text_diff': change.diff_metadata_json if isinstance(change.diff_metadata_json, dict) else {},
                    'content_change_percentage': 0.0,  # Will be calculated if needed
                    'before_content': change.before_content,
                    'after_content': change.after_content
                }
                
                # Classify change
                if self.has_llm:
                    classification = self.classifier.classify_change(
                        change_data=change_data,
                        asset_type=asset.asset_type,
                        url=asset.url,
                        change_type=change.change_type,
                        summary=change.summary,
                        why_it_matters=change.why_it_matters
                    )
                else:
                    # Use rule-based classification (fallback when LLM unavailable)
                    from src.classifier.change_classifier import ChangeClassifier
                    classification = ChangeClassifier._rule_based_classification_static(
                        change_data, asset.asset_type, change.change_type
                    )
                
                # Assign priority
                priority = self.priority_assigner.assign_priority(change, classification)
                
                # Check if should alert
                should_alert = self.priority_assigner.should_alert(
                    change, classification, asset.priority_threshold
                )
                
                # Update change record
                with DatabaseSession() as session:
                    change = session.query(Change).filter(Change.id == change.id).first()
                    change.priority = priority
                    change.change_type = classification.get('change_type', change.change_type)
                    change.summary = classification.get('summary', change.summary)
                    change.why_it_matters = classification.get('why_it_matters', change.why_it_matters)
                    session.commit()
                
                if should_alert:
                    logger.info(f"Change {change.id} classified as {priority} priority - will alert")
                    
                    # Send immediate alert for high-priority changes
                    if priority == 'high' and self.alert_manager:
                        try:
                            self.alert_manager.send_immediate_alert(change)
                        except Exception as e:
                            logger.error(f"Error sending immediate alert for change {change.id}: {e}", exc_info=True)
                else:
                    logger.info(f"Change {change.id} classified but does not meet alert criteria")
                
                return should_alert
                
        except Exception as e:
            logger.error(f"Error classifying change {change.id}: {e}", exc_info=True)
            return False
    
    def classify_pending_changes(self) -> List[Change]:
        """
        Classify all pending changes (changes without priority assigned)
        
        Returns:
            List of changes that should be alerted
        """
        with DatabaseSession() as session:
            pending_changes = session.query(Change)\
                .filter(Change.priority == None)\
                .filter(Change.alert_sent == False)\
                .all()
        
        logger.info(f"Found {len(pending_changes)} pending changes to classify")
        
        changes_to_alert = []
        for change in pending_changes:
            try:
                if self.classify_change(change):
                    changes_to_alert.append(change)
            except Exception as e:
                logger.error(f"Error classifying change {change.id}: {e}", exc_info=True)
        
        logger.info(f"Classified {len(pending_changes)} changes, {len(changes_to_alert)} ready for alerting")
        return changes_to_alert
    
    def reclassify_change(self, change_id: int) -> bool:
        """
        Reclassify a specific change (useful for testing or manual review)
        
        Args:
            change_id: ID of change to reclassify
        
        Returns:
            True if reclassification successful
        """
        with DatabaseSession() as session:
            change = session.query(Change).filter(Change.id == change_id).first()
            if not change:
                logger.error(f"Change {change_id} not found")
                return False
        
        return self.classify_change(change)

