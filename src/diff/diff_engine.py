"""
Diff engine for detecting changes between snapshots
"""
import difflib
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import json

from src.storage.database import DatabaseSession
from src.storage.models import Asset, Snapshot, Change


class DiffEngine:
    """Engine for detecting changes between content snapshots"""
    
    def __init__(self):
        """Initialize diff engine"""
        pass
    
    def compare_snapshots(self, snapshot_before: Snapshot, snapshot_after: Snapshot) -> Optional[Dict[str, Any]]:
        """
        Compare two snapshots and detect if there are meaningful changes
        
        Args:
            snapshot_before: Previous snapshot
            snapshot_after: Current snapshot
        
        Returns:
            Dictionary with change information if change detected, None otherwise
        """
        # Fast path: hash comparison
        if snapshot_before.content_hash == snapshot_after.content_hash:
            return None  # No change
        
        # If either snapshot has no content, can't compare
        if not snapshot_before.content_text or not snapshot_after.content_text:
            return None
        
        # Perform text diff
        diff_result = self._text_diff(
            snapshot_before.content_text,
            snapshot_after.content_text
        )
        
        # Extract structured diff if metadata exists
        structured_diff = None
        if snapshot_before.metadata_json and snapshot_after.metadata_json:
            structured_diff = self._compare_structured_data(
                snapshot_before.metadata_json,
                snapshot_after.metadata_json,
                snapshot_before.asset.asset_type
            )
        
        # Prepare change data
        change_data = {
            'before_content': snapshot_before.content_text,
            'after_content': snapshot_after.content_text,
            'text_diff': diff_result,
            'structured_diff': structured_diff,
            'content_change_percentage': self._calculate_change_percentage(
                snapshot_before.content_text,
                snapshot_after.content_text
            )
        }
        
        return change_data
    
    def _text_diff(self, text_before: str, text_after: str) -> Dict[str, Any]:
        """
        Perform line-by-line text diff
        
        Args:
            text_before: Previous text
            text_after: Current text
        
        Returns:
            Dictionary with diff statistics
        """
        lines_before = text_before.split('\n')
        lines_after = text_after.split('\n')
        
        # Use difflib to compute differences
        differ = difflib.Differ()
        diff = list(differ.compare(lines_before, lines_after))
        
        # Count changes
        added = sum(1 for line in diff if line.startswith('+ '))
        removed = sum(1 for line in diff if line.startswith('- '))
        modified = sum(1 for line in diff if line.startswith('? '))
        
        # Extract added and removed lines (for summary)
        added_lines = [line[2:] for line in diff if line.startswith('+ ') and not line.startswith('+++')]
        removed_lines = [line[2:] for line in diff if line.startswith('- ') and not line.startswith('---')]
        
        return {
            'added_count': added,
            'removed_count': removed,
            'modified_count': modified,
            'added_lines': added_lines[:20],  # Limit to first 20 for summary
            'removed_lines': removed_lines[:20],
            'total_lines_before': len(lines_before),
            'total_lines_after': len(lines_after)
        }
    
    def _compare_structured_data(self, metadata_before: Dict, metadata_after: Dict, asset_type: str) -> Optional[Dict[str, Any]]:
        """
        Compare structured metadata (pricing, features, etc.)
        
        Args:
            metadata_before: Previous metadata
            metadata_after: Current metadata
            asset_type: Type of asset (pricing, features, etc.)
        
        Returns:
            Dictionary with structured diff or None
        """
        if asset_type == 'pricing':
            return self._compare_pricing(metadata_before, metadata_after)
        elif asset_type == 'features':
            return self._compare_features(metadata_before, metadata_after)
        elif asset_type == 'changelog':
            return self._compare_changelog(metadata_before, metadata_after)
        elif asset_type == 'sitemap':
            return self._compare_sitemap(metadata_before, metadata_after)
        elif asset_type == 'blog':
            return self._compare_blog(metadata_before, metadata_after)
        elif asset_type == 'compliance':
            return self._compare_compliance(metadata_before, metadata_after)
        elif asset_type == 'twitter':
            return self._compare_twitter(metadata_before, metadata_after)
        elif asset_type == 'news':
            return self._compare_news(metadata_before, metadata_after)
        
        return None
    
    def _compare_pricing(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare pricing metadata"""
        changes = {
            'tier_changes': [],
            'free_tier_changed': False,
            'new_tiers': [],
            'removed_tiers': []
        }
        
        tiers_before = {tier.get('name', ''): tier for tier in before.get('tiers', [])}
        tiers_after = {tier.get('name', ''): tier for tier in after.get('tiers', [])}
        
        # Find new tiers
        for name, tier in tiers_after.items():
            if name not in tiers_before:
                changes['new_tiers'].append(tier)
        
        # Find removed tiers
        for name, tier in tiers_before.items():
            if name not in tiers_after:
                changes['removed_tiers'].append(tier)
        
        # Find changed tiers
        for name in set(tiers_before.keys()) & set(tiers_after.keys()):
            tier_before = tiers_before[name]
            tier_after = tiers_after[name]
            
            if tier_before.get('price') != tier_after.get('price'):
                changes['tier_changes'].append({
                    'tier': name,
                    'price_before': tier_before.get('price'),
                    'price_after': tier_after.get('price')
                })
            
            # Check for feature changes
            features_before = set(tier_before.get('features', []))
            features_after = set(tier_after.get('features', []))
            if features_before != features_after:
                changes['tier_changes'].append({
                    'tier': name,
                    'features_added': list(features_after - features_before),
                    'features_removed': list(features_before - features_after)
                })
        
        # Check free tier
        if before.get('has_free_tier') != after.get('has_free_tier'):
            changes['free_tier_changed'] = True
            changes['free_tier_before'] = before.get('has_free_tier')
            changes['free_tier_after'] = after.get('has_free_tier')
        
        return changes if any([changes['tier_changes'], changes['new_tiers'], 
                               changes['removed_tiers'], changes['free_tier_changed']]) else None
    
    def _compare_features(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare feature metadata"""
        features_before = set(before.get('features', []))
        features_after = set(after.get('features', []))
        
        added = list(features_after - features_before)
        removed = list(features_before - features_after)
        
        if not added and not removed:
            return None
        
        return {
            'features_added': added,
            'features_removed': removed
        }
    
    def _compare_changelog(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare changelog metadata"""
        entries_before = {(e.get('date'), e.get('content')): e for e in before.get('entries', [])}
        entries_after = {(e.get('date'), e.get('content')): e for e in after.get('entries', [])}
        
        new_entries = [e for key, e in entries_after.items() if key not in entries_before]
        
        if not new_entries:
            return None
        
        return {
            'new_entries': new_entries
        }
    
    def _compare_sitemap(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare sitemap metadata"""
        urls_before = set(before.get('urls', []))
        urls_after = set(after.get('urls', []))
        
        new_urls = list(urls_after - urls_before)
        removed_urls = list(urls_before - urls_after)
        
        if not new_urls and not removed_urls:
            return None
        
        return {
            'new_urls': new_urls,
            'removed_urls': removed_urls
        }
    
    def _compare_blog(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare blog metadata"""
        posts_before = {p.get('url'): p for p in before.get('posts', [])}
        posts_after = {p.get('url'): p for p in after.get('posts', [])}
        
        new_posts = [p for url, p in posts_after.items() if url not in posts_before]
        
        if not new_posts:
            return None
        
        return {
            'new_posts': new_posts
        }
    
    def _compare_compliance(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare compliance metadata"""
        certs_before = set(before.get('certifications', []))
        certs_after = set(after.get('certifications', []))
        
        standards_before = set(before.get('standards', []))
        standards_after = set(after.get('standards', []))
        
        new_certs = list(certs_after - certs_before)
        new_standards = list(standards_after - standards_before)
        
        if not new_certs and not new_standards:
            return None
        
        return {
            'new_certifications': new_certs,
            'new_standards': new_standards
        }
    
    def _compare_twitter(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare Twitter metadata"""
        tweets_before = {t.get('id'): t for t in before.get('tweets', []) if t.get('id')}
        tweets_after = {t.get('id'): t for t in after.get('tweets', []) if t.get('id')}
        
        new_tweets = [t for tweet_id, t in tweets_after.items() if tweet_id not in tweets_before]
        
        if not new_tweets:
            return None
        
        return {
            'new_tweets': new_tweets
        }
    
    def _compare_news(self, before: Dict, after: Dict) -> Dict[str, Any]:
        """Compare News metadata"""
        articles_before = {a.get('url'): a for a in before.get('articles', []) if a.get('url')}
        articles_after = {a.get('url'): a for a in after.get('articles', []) if a.get('url')}

        new_articles = [a for url, a in articles_after.items() if url not in articles_before]

        if not new_articles:
            return None

        return {
            'new_articles': new_articles
        }
    
    def _calculate_change_percentage(self, text_before: str, text_after: str) -> float:
        """
        Calculate approximate percentage of content change
        
        Args:
            text_before: Previous text
            text_after: Current text
        
        Returns:
            Percentage of change (0-100)
        """
        if not text_before:
            return 100.0 if text_after else 0.0
        if not text_after:
            return 100.0
        
        # Use sequence matcher for similarity
        matcher = difflib.SequenceMatcher(None, text_before, text_after)
        similarity = matcher.ratio()
        change_percentage = (1.0 - similarity) * 100.0
        
        return round(change_percentage, 2)
    
    def is_significant_change(self, change_data: Dict[str, Any], threshold: float = 5.0) -> bool:
        """
        Determine if a change is significant enough to warrant an alert
        
        Args:
            change_data: Change data from compare_snapshots
            threshold: Minimum change percentage to consider significant
        
        Returns:
            True if change is significant, False otherwise
        """
        # If structured diff exists and has changes, it's significant
        if change_data.get('structured_diff'):
            return True
        
        # Check content change percentage
        change_percentage = change_data.get('content_change_percentage', 0.0)
        if change_percentage >= threshold:
            return True
        
        # Check if substantial lines were added/removed
        text_diff = change_data.get('text_diff', {})
        added = text_diff.get('added_count', 0)
        removed = text_diff.get('removed_count', 0)
        
        # If more than 10 lines changed, consider significant
        if (added + removed) > 10:
            return True
        
        return False

