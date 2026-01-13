#!/usr/bin/env python3
"""
Run script for AI Competitor Watchdog V1
Supports test mode with limits and dry-run options
"""
import sys
import os
import argparse

# Add project root to path
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

from src.storage.database import init_database, DatabaseSession
from src.config.loader import load_competitor_config
from src.crawler.scheduler import CrawlScheduler
from src.storage.models import Asset, Competitor
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mode(limit: int, dry_run: bool):
    """
    Run in test mode: crawl limited number of assets
    
    Args:
        limit: Maximum number of assets to process
        dry_run: If True, only simulate (don't actually crawl)
    """
    print("=" * 60)
    print("AI Competitor Watchdog V1 - TEST MODE")
    print("=" * 60)
    print(f"Limit: {limit} asset(s)")
    print(f"Dry-run: {dry_run}")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    try:
        init_database()
        print("   [OK] Database initialized")
    except Exception as e:
        print(f"   [ERROR] Database initialization failed: {e}")
        return 1
    
    # Load configuration
    print("\n2. Loading configuration...")
    try:
        config = load_competitor_config()
        competitors = config.get('competitors', [])
        print(f"   [OK] Loaded {len(competitors)} competitor(s)")
    except Exception as e:
        print(f"   [ERROR] Configuration loading failed: {e}")
        return 1
    
    # Initialize scheduler to sync assets
    print("\n3. Syncing assets from configuration...")
    try:
        scheduler = CrawlScheduler(alert_manager=None)  # No alerts in test mode
        scheduler._sync_assets_from_config()
        print("   [OK] Assets synced")
    except Exception as e:
        print(f"   [ERROR] Asset sync failed: {e}")
        return 1
    
    # Get assets (limit to N)
    print(f"\n4. Getting assets (limit: {limit})...")
    asset_list = []
    with DatabaseSession() as session:
        all_assets = session.query(Asset).join(Competitor).order_by(Asset.id).limit(limit).all()
        
        if not all_assets:
            print("   [WARNING] No assets found in database")
            return 0
        
        # Extract asset info while in session
        for asset in all_assets:
            competitor_name = asset.competitor.name if asset.competitor else "Unknown"
            asset_list.append({
                'id': asset.id,
                'competitor_name': competitor_name,
                'asset_type': asset.asset_type,
                'url': asset.url
            })
        
        print(f"   [OK] Found {len(asset_list)} asset(s) to process")
        for asset_info in asset_list:
            print(f"      - {asset_info['competitor_name']}: {asset_info['asset_type']} - {asset_info['url']}")
    
    if dry_run:
        print("\n" + "=" * 60)
        print("DRY-RUN MODE: No actual crawling will be performed")
        print("=" * 60)
        print(f"\nWould crawl {len(asset_list)} asset(s):")
        for asset_info in asset_list:
            print(f"  - {asset_info['competitor_name']} | {asset_info['asset_type']} | {asset_info['url']}")
        print("\n[DRY-RUN] Test complete. No changes made.")
        return 0
    
    # Actually crawl the assets
    print("\n5. Crawling assets...")
    print("=" * 60)
    
    stats = {
        'total': len(asset_list),
        'success': 0,
        'failed': 0
    }
    
    for i, asset_info in enumerate(asset_list, 1):
        print(f"\n[{i}/{len(asset_list)}] Crawling: {asset_info['competitor_name']} - {asset_info['asset_type']}")
        print(f"URL: {asset_info['url']}")
        
        try:
            # Get asset from database in new session
            with DatabaseSession() as session:
                asset = session.query(Asset).filter(Asset.id == asset_info['id']).first()
                if not asset:
                    stats['failed'] += 1
                    print(f"   [ERROR] Asset not found in database")
                    continue
                
                # Use scheduler's crawl method
                success = scheduler._crawl_asset(asset)
                if success:
                    stats['success'] += 1
                    print(f"   [OK] Crawl successful")
                else:
                    stats['failed'] += 1
                    print(f"   [FAILED] Crawl failed")
        except Exception as e:
            stats['failed'] += 1
            print(f"   [ERROR] Exception: {e}")
            logger.error(f"Error crawling {asset_info['url']}: {e}", exc_info=True)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST MODE COMPLETE")
    print("=" * 60)
    print(f"Total assets: {stats['total']}")
    print(f"Successful: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print("=" * 60)
    
    return 0 if stats['failed'] == 0 else 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI Competitor Watchdog V1 - Run Script')
    parser.add_argument('--mode', choices=['test', 'normal'], default='normal',
                       help='Run mode: test (limited crawl) or normal (full system)')
    parser.add_argument('--limit', type=int, default=10,
                       help='Limit number of assets to process in test mode (default: 10)')
    parser.add_argument('--dry-run', type=str, choices=['true', 'false'], default='false',
                       help='Dry-run mode: true (simulate only) or false (actually crawl)')
    
    args = parser.parse_args()
    
    # Convert dry-run string to boolean
    dry_run = args.dry_run.lower() == 'true'
    
    if args.mode == 'test':
        return test_mode(limit=args.limit, dry_run=dry_run)
    else:
        # Normal mode - use existing main.py logic
        print("Normal mode - use 'python -m src.main' instead")
        print("Or use --mode test for test mode")
        return 1


if __name__ == '__main__':
    sys.exit(main())
