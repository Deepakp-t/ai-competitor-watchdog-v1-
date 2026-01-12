"""
Change detection orchestrator that combines diff engine and semantic analysis
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.storage.database import DatabaseSession
from src.storage.models import Asset, Snapshot, Change
from src.diff.diff_engine import DiffEngine
from src.diff.semantic_diff import SemanticDiff

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Orchestrates change detection between snapshots"""
    
    def __init__(self):
        """Initialize change detector"""
        self.diff_engine = DiffEngine()
        try:
            self.semantic_diff = SemanticDiff()
            self.has_llm = True
        except Exception as e:
            logger.warning(f"LLM not available for semantic diff: {e}. Will use basic diff only.")
            self.semantic_diff = None
            self.has_llm = False
    
    def detect_changes_for_asset(self, asset: Asset) -> List[Change]:
        """
        Detect changes for an asset by comparing latest snapshots
        
        Args:
            asset: Asset to check for changes (can be detached)
        
        Returns:
            List of Change objects (empty if no changes)
        """
        # Extract asset ID before session operations
        asset_id = asset.id
        
        with DatabaseSession() as session:
            # Reload asset in this session
            asset = session.query(Asset).filter(Asset.id == asset_id).first()
            
            if not asset:
                logger.warning(f"Asset {asset_id} not found in database")
                return []
            
            # Get last two snapshots
            snapshots = session.query(Snapshot)\
                .filter(Snapshot.asset_id == asset.id)\
                .order_by(Snapshot.crawl_timestamp.desc())\
                .limit(2)\
                .all()
            
            if len(snapshots) < 2:
                # Need at least 2 snapshots to compare
                return []
            
            snapshot_after = snapshots[0]  # Most recent
            snapshot_before = snapshots[1]  # Previous
            
            # Check if change already detected
            existing_change = session.query(Change)\
                .filter(Change.snapshot_after_id == snapshot_after.id)\
                .first()
            
            if existing_change:
                # Change already detected for this snapshot
                return []
            
            # Compare snapshots
            change_data = self.diff_engine.compare_snapshots(snapshot_before, snapshot_after)
            
            if not change_data:
                return []  # No change detected
            
            # Check if change is significant
            if not self.diff_engine.is_significant_change(change_data):
                logger.debug(f"Change detected for {asset.url} but not significant enough")
                return []  # Change too minor
            
            # Perform semantic analysis if LLM available
            semantic_analysis = None
            if self.has_llm and snapshot_before.content_text and snapshot_after.content_text:
                try:
                    semantic_analysis = self.semantic_diff.analyze_change(
                        snapshot_before.content_text,
                        snapshot_after.content_text,
                        asset.asset_type,
                        asset.url
                    )
                    
                    # Filter noise
                    if self.semantic_diff.filter_noise(change_data, semantic_analysis):
                        logger.info(f"Filtered out noise change for {asset.url}")
                        return []  # Filtered as noise
                except Exception as e:
                    logger.error(f"Error in semantic analysis for {asset.url}: {e}")
                    # Continue without semantic analysis
            
            # Create change record
            change = self._create_change_record(
                session, asset, snapshot_before, snapshot_after,
                change_data, semantic_analysis
            )
            
            return [change]
    
    def _create_change_record(self, session, asset: Asset, snapshot_before: Snapshot,
                             snapshot_after: Snapshot, change_data: Dict,
                             semantic_analysis: Optional[Dict]) -> Change:
        """
        Create a Change record in the database
        
        Args:
            session: Database session
            asset: Asset that changed
            snapshot_before: Previous snapshot
            snapshot_after: Current snapshot
            change_data: Change data from diff engine
            semantic_analysis: Semantic analysis from LLM (optional)
        
        Returns:
            Change object
        """
        # Extract information from semantic analysis if available
        if semantic_analysis:
            change_type = semantic_analysis.get('change_type', 'unknown')
            summary = semantic_analysis.get('summary', 'Change detected')
            why_it_matters = semantic_analysis.get('why_it_matters', '')
            significance = semantic_analysis.get('significance', 'medium')
        else:
            # Fallback to basic analysis
            change_type = self._infer_change_type(asset.asset_type, change_data)
            summary = self._generate_basic_summary(change_data, asset.asset_type)
            why_it_matters = f"Change detected on {asset.asset_type} page"
            significance = 'medium'
        
        # Truncate content for storage (keep first 10000 chars)
        before_content = change_data.get('before_content', '')[:10000]
        after_content = change_data.get('after_content', '')[:10000]
        
        change = Change(
            asset_id=asset.id,
            snapshot_before_id=snapshot_before.id,
            snapshot_after_id=snapshot_after.id,
            change_type=change_type,
            priority=None,  # Will be set by classifier
            summary=summary,
            why_it_matters=why_it_matters,
            before_content=before_content,
            after_content=after_content,
            diff_metadata_json=change_data.get('structured_diff') or change_data.get('text_diff'),
            detected_at=datetime.utcnow(),
            alert_sent=False
        )
        
        session.add(change)
        session.commit()
        session.refresh(change)
        
        logger.info(f"Created change record {change.id} for {asset.url} (type: {change_type})")
        
        return change
    
    def _infer_change_type(self, asset_type: str, change_data: Dict) -> str:
        """Infer change type from asset type and change data"""
        # Check structured diff first
        structured_diff = change_data.get('structured_diff')
        if structured_diff:
            if 'tier_changes' in structured_diff or 'free_tier_changed' in structured_diff:
                return 'pricing'
            elif 'features_added' in structured_diff or 'features_removed' in structured_diff:
                return 'feature'
            elif 'new_certifications' in structured_diff or 'new_standards' in structured_diff:
                return 'compliance'
            elif 'new_entries' in structured_diff:
                return 'changelog'
            elif 'new_urls' in structured_diff:
                return 'sitemap'
            elif 'new_posts' in structured_diff:
                return 'blog'
        
        # Fallback to asset type
        return asset_type
    
    def _generate_basic_summary(self, change_data: Dict, asset_type: str) -> str:
        """Generate basic summary without LLM"""
        text_diff = change_data.get('text_diff', {})
        added = text_diff.get('added_count', 0)
        removed = text_diff.get('removed_count', 0)
        change_pct = change_data.get('content_change_percentage', 0.0)
        
        if added > 0 and removed > 0:
            return f"Content updated on {asset_type} page: {added} lines added, {removed} lines removed ({change_pct}% change)"
        elif added > 0:
            return f"Content added to {asset_type} page: {added} new lines ({change_pct}% change)"
        elif removed > 0:
            return f"Content removed from {asset_type} page: {removed} lines removed ({change_pct}% change)"
        else:
            return f"Change detected on {asset_type} page ({change_pct}% change)"
    
    def detect_changes_for_all_assets(self) -> List[Change]:
        """
        Detect changes for all assets that have new snapshots
        
        Returns:
            List of all detected changes
        """
        # Get asset IDs first to avoid detached instance issues
        with DatabaseSession() as session:
            asset_ids = [asset.id for asset in session.query(Asset).all()]
        
        all_changes = []
        for asset_id in asset_ids:
            try:
                # Reload asset in a new session for each detection
                with DatabaseSession() as session:
                    asset = session.query(Asset).filter(Asset.id == asset_id).first()
                    if asset:
                        changes = self.detect_changes_for_asset(asset)
                        all_changes.extend(changes)
            except Exception as e:
                logger.error(f"Error detecting changes for asset {asset_id}: {e}", exc_info=True)
        
        logger.info(f"Detected {len(all_changes)} total changes across all assets")
        return all_changes

