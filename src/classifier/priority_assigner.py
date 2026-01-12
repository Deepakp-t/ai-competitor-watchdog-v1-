"""
Priority assignment and quality validation
"""
import logging
from typing import Dict, Optional, Any, Tuple
from src.storage.models import Change

logger = logging.getLogger(__name__)


class PriorityAssigner:
    """Assigns priority to changes and validates quality"""
    
    # Priority rules from architecture
    HIGH_PRIORITY_KEYWORDS = [
        'pricing', 'price', 'tier', 'plan', 'free tier',
        'certification', 'compliance', 'SOC', 'ISO', 'GDPR', 'HIPAA',
        'integration', 'launch', 'release', 'feature'
    ]
    
    MEDIUM_PRIORITY_KEYWORDS = [
        'changelog', 'update', 'news', 'press release',
        'case study', 'customer', 'logo', 'twitter', 'tweet'
    ]
    
    LOW_PRIORITY_KEYWORDS = [
        'homepage', 'landing', 'testimonial', 'blog',
        'thought leadership', 'industry'
    ]
    
    def assign_priority(self, change: Change, classification: Dict[str, Any]) -> str:
        """
        Assign priority to a change
        
        Args:
            change: Change object
            classification: Classification result from classifier
        
        Returns:
            Priority level: 'high', 'medium', or 'low'
        """
        # Use classification priority if available and confident
        if classification.get('confidence', 0.0) >= 0.7:
            priority = classification.get('priority', 'medium').lower()
            if priority in ['high', 'medium', 'low']:
                return priority
        
        # Fallback to rule-based assignment
        return self._rule_based_priority(change, classification)
    
    def _rule_based_priority(self, change: Change, classification: Dict[str, Any]) -> str:
        """Assign priority based on rules"""
        change_type = (classification.get('change_type') or change.change_type or '').lower()
        summary = (classification.get('summary') or change.summary or '').lower()
        why_it_matters = (classification.get('why_it_matters') or change.why_it_matters or '').lower()
        
        combined_text = f"{change_type} {summary} {why_it_matters}"
        
        # Check for high priority indicators
        if any(keyword in combined_text for keyword in self.HIGH_PRIORITY_KEYWORDS):
            # But exclude if it's clearly low priority context
            if not any(keyword in combined_text for keyword in self.LOW_PRIORITY_KEYWORDS):
                return 'high'
        
        # Check for medium priority indicators
        if any(keyword in combined_text for keyword in self.MEDIUM_PRIORITY_KEYWORDS):
            return 'medium'
        
        # Check for low priority indicators
        if any(keyword in combined_text for keyword in self.LOW_PRIORITY_KEYWORDS):
            return 'low'
        
        # Default based on change type
        if change_type in ['pricing', 'compliance']:
            return 'high'
        elif change_type in ['changelog', 'news']:
            return 'medium'
        else:
            return 'low'
    
    def validate_quality(self, change: Change, classification: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate that change meets quality bar
        
        Args:
            change: Change object
            classification: Classification result
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check summary length (≤3 sentences)
        summary = classification.get('summary') or change.summary
        if not summary:
            return False, "Summary is missing"
        
        sentences = summary.split('. ')
        if len(sentences) > 3:
            return False, f"Summary has {len(sentences)} sentences (max 3)"
        
        # Check "why it matters" is present and non-empty
        why_it_matters = classification.get('why_it_matters') or change.why_it_matters
        if not why_it_matters or len(why_it_matters.strip()) < 10:
            return False, "Why it matters is missing or too short"
        
        # Check for speculative language (common patterns)
        speculative_words = ['might', 'could', 'possibly', 'perhaps', 'maybe', 'potentially']
        why_lower = why_it_matters.lower()
        if any(word in why_lower for word in speculative_words):
            # Allow if it's part of a valid phrase, but flag if standalone
            if not any(phrase in why_lower for phrase in ['could indicate', 'might suggest']):
                return False, "Why it matters contains speculative language"
        
        # Check confidence threshold
        confidence = classification.get('confidence', 0.0)
        if confidence < 0.3:
            return False, f"Classification confidence too low: {confidence}"
        
        # Check that before/after content exists
        if not change.before_content or not change.after_content:
            return False, "Before/after content is missing"
        
        return True, None
    
    def should_alert(self, change: Change, classification: Dict[str, Any], 
                    priority_threshold: str = None) -> bool:
        """
        Determine if change should trigger an alert
        
        Args:
            change: Change object
            classification: Classification result
            priority_threshold: Minimum priority threshold from asset config
        
        Returns:
            True if alert should be sent, False otherwise
        """
        # Validate quality first
        is_valid, error = self.validate_quality(change, classification)
        if not is_valid:
            logger.debug(f"Change {change.id} failed quality check: {error}")
            return False
        
        # Assign priority
        priority = self.assign_priority(change, classification)
        
        # Check against threshold
        if priority_threshold:
            priority_levels = {'high': 3, 'medium': 2, 'low': 1}
            threshold_level = priority_levels.get(priority_threshold.lower(), 2)
            change_level = priority_levels.get(priority, 2)
            
            if change_level < threshold_level:
                logger.debug(f"Change {change.id} priority {priority} below threshold {priority_threshold}")
                return False
        
        return True

