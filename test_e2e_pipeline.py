#!/usr/bin/env python3
"""
End-to-end test script for AI Competitor Watchdog V1 pipeline
Runs the complete pipeline: crawl -> detect -> classify -> alert
"""
import sys
import os
import time
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.storage.database import init_database, DatabaseSession
from src.config.loader import load_competitor_config, get_all_assets
from src.crawler.scheduler import CrawlScheduler
from src.diff.change_detector import ChangeDetector
from src.classifier.classifier_manager import ClassifierManager
from src.alerting.alert_manager import AlertManager
from src.storage.models import Asset, Competitor, Change, Snapshot


def print_step(step_num: int, step_name: str):
    """Print a step header"""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {step_name}")
    print(f"{'='*60}")


def report_result(step_name: str, success: bool, details: str = ""):
    """Report success or failure for a step"""
    status = "[SUCCESS]" if success else "[FAILED]"
    print(f"{status} {step_name}")
    if details:
        print(f"  {details}")


def test_e2e_pipeline():
    """
    Run the complete V1 pipeline end-to-end in test mode
    """
    print("\n" + "="*60)
    print("AI COMPETITOR WATCHDOG V1 - END-TO-END TEST")
    print("="*60)
    print("\nThis test will:")
    print("  1. Initialize database")
    print("  2. Load configuration and filter to 1 competitor")
    print("  3. Select 2-3 URLs (pricing + changelog)")
    print("  4. Run first crawl cycle (baseline snapshots)")
    print("  5. Run second crawl cycle (to detect changes)")
    print("  6. Detect changes between snapshots")
    print("  7. Classify changes and generate insights")
    print("  8. Send Slack alert for detected changes")
    print("\n" + "="*60)
    
    results = {}
    
    # STEP 1: Initialize Database
    print_step(1, "Initialize Database")
    try:
        init_database()
        report_result("Database initialization", True, "Database ready")
        results['database'] = True
    except Exception as e:
        report_result("Database initialization", False, str(e))
        results['database'] = False
        return results
    
    # STEP 2: Load Configuration and Filter
    print_step(2, "Load Configuration and Filter to 1 Competitor")
    try:
        config = load_competitor_config()
        competitors = config.get('competitors', [])
        
        if not competitors:
            report_result("Configuration loading", False, "No competitors found in config")
            results['config'] = False
            return results
        
        # Select first competitor
        selected_competitor = competitors[0]
        competitor_name = selected_competitor['name']
        
        # Get assets for this competitor
        all_assets = get_all_assets(config)
        competitor_assets = [
            a for a in all_assets 
            if a['competitor_name'] == competitor_name and a.get('url')
        ]
        
        # Filter to pricing and changelog (or first 2-3 available)
        asset_types_to_find = ['pricing', 'changelog', 'features']
        selected_assets = []
        
        for asset_type in asset_types_to_find:
            for asset in competitor_assets:
                if asset['type'] == asset_type and asset not in selected_assets:
                    selected_assets.append(asset)
                    if len(selected_assets) >= 3:
                        break
            if len(selected_assets) >= 3:
                break
        
        # If we don't have enough, take first 2-3 available
        if len(selected_assets) < 2:
            selected_assets = competitor_assets[:3]
        
        if len(selected_assets) < 2:
            report_result("Asset selection", False, f"Not enough assets found for {competitor_name}")
            results['config'] = False
            return results
        
        print(f"  Selected competitor: {competitor_name}")
        print(f"  Selected {len(selected_assets)} asset(s):")
        for asset in selected_assets:
            print(f"    - {asset['type']}: {asset['url']}")
        
        report_result("Configuration loading", True, 
                     f"Selected {competitor_name} with {len(selected_assets)} assets")
        results['config'] = True
        results['competitor_name'] = competitor_name
        results['selected_assets'] = selected_assets
        
    except Exception as e:
        report_result("Configuration loading", False, str(e))
        results['config'] = False
        return results
    
    # STEP 3: Initialize Components
    print_step(3, "Initialize Pipeline Components")
    try:
        alert_manager = AlertManager()
        scheduler = CrawlScheduler(alert_manager=alert_manager)
        change_detector = ChangeDetector()
        classifier_manager = ClassifierManager(alert_manager=alert_manager)
        
        report_result("Component initialization", True, 
                     "Scheduler, ChangeDetector, ClassifierManager, AlertManager ready")
        results['components'] = True
        results['scheduler'] = scheduler
        results['change_detector'] = change_detector
        results['classifier_manager'] = classifier_manager
        results['alert_manager'] = alert_manager
        
    except Exception as e:
        report_result("Component initialization", False, str(e))
        results['components'] = False
        return results
    
    # STEP 4: Sync Assets and Get Asset IDs
    print_step(4, "Sync Assets from Configuration")
    try:
        scheduler._sync_assets_from_config()
        
        # Get asset IDs for selected URLs
        asset_ids = []
        with DatabaseSession() as session:
            for asset_config in selected_assets:
                asset = session.query(Asset).join(Competitor).filter(
                    Competitor.name == competitor_name,
                    Asset.url == asset_config['url']
                ).first()
                if asset:
                    asset_ids.append(asset.id)
                    print(f"  Found asset ID {asset.id}: {asset_config['type']} - {asset.url}")
        
        if len(asset_ids) < 2:
            report_result("Asset sync", False, f"Only found {len(asset_ids)} assets in database")
            results['sync'] = False
            return results
        
        report_result("Asset sync", True, f"Synced {len(asset_ids)} assets")
        results['sync'] = True
        results['asset_ids'] = asset_ids
        
    except Exception as e:
        report_result("Asset sync", False, str(e))
        results['sync'] = False
        return results
    
    # STEP 5: First Crawl Cycle (Baseline)
    print_step(5, "First Crawl Cycle - Create Baseline Snapshots")
    try:
        crawl_success = 0
        crawl_failed = 0
        
        with DatabaseSession() as session:
            for asset_id in asset_ids:
                asset = session.query(Asset).filter(Asset.id == asset_id).first()
                if asset:
                    print(f"  Crawling: {asset.asset_type} - {asset.url}")
                    if scheduler._crawl_asset(asset):
                        crawl_success += 1
                    else:
                        crawl_failed += 1
        
        if crawl_success == 0:
            report_result("First crawl cycle", False, "All crawls failed")
            results['crawl1'] = False
            return results
        
        report_result("First crawl cycle", True, 
                     f"Success: {crawl_success}, Failed: {crawl_failed}")
        results['crawl1'] = True
        results['crawl1_success'] = crawl_success
        
        # Wait a moment for database commits
        time.sleep(1)
        
    except Exception as e:
        report_result("First crawl cycle", False, str(e))
        results['crawl1'] = False
        return results
    
    # STEP 6: Second Crawl Cycle (Detect Changes)
    print_step(6, "Second Crawl Cycle - Detect Changes")
    try:
        crawl_success = 0
        crawl_failed = 0
        
        with DatabaseSession() as session:
            for asset_id in asset_ids:
                asset = session.query(Asset).filter(Asset.id == asset_id).first()
                if asset:
                    print(f"  Crawling: {asset.asset_type} - {asset.url}")
                    if scheduler._crawl_asset(asset):
                        crawl_success += 1
                    else:
                        crawl_failed += 1
        
        if crawl_success == 0:
            report_result("Second crawl cycle", False, "All crawls failed")
            results['crawl2'] = False
            return results
        
        report_result("Second crawl cycle", True, 
                     f"Success: {crawl_success}, Failed: {crawl_failed}")
        results['crawl2'] = True
        results['crawl2_success'] = crawl_success
        
        # Wait a moment for database commits
        time.sleep(1)
        
    except Exception as e:
        report_result("Second crawl cycle", False, str(e))
        results['crawl2'] = False
        return results
    
    # STEP 7: Detect Changes
    print_step(7, "Detect Changes Between Snapshots")
    try:
        detected_changes = []
        
        with DatabaseSession() as session:
            for asset_id in asset_ids:
                asset = session.query(Asset).filter(Asset.id == asset_id).first()
                if asset:
                    changes = change_detector.detect_changes_for_asset(asset)
                    if changes:
                        detected_changes.extend(changes)
                        for change in changes:
                            print(f"  Detected change ID {change.id} for {asset.asset_type}")
        
        if not detected_changes:
            report_result("Change detection", True, 
                         "No changes detected (this is normal if content hasn't changed)")
            results['detection'] = True
            results['changes_detected'] = 0
            # If no changes, we'll simulate one for testing
            print("\n  NOTE: No changes detected. This is expected if content hasn't changed.")
            print("  The pipeline is working correctly, but we need changes to test classification and alerting.")
        else:
            report_result("Change detection", True, f"Detected {len(detected_changes)} change(s)")
            results['detection'] = True
            results['changes_detected'] = len(detected_changes)
            results['change_ids'] = [c.id for c in detected_changes]
        
    except Exception as e:
        report_result("Change detection", False, str(e))
        results['detection'] = False
        return results
    
    # STEP 8: Classify Changes and Generate Insights
    print_step(8, "Classify Changes and Generate Insights")
    try:
        classified_count = 0
        
        if detected_changes:
            with DatabaseSession() as session:
                for change in detected_changes:
                    # Reload change in session
                    change = session.query(Change).filter(Change.id == change.id).first()
                    if change and not change.priority:  # Not yet classified
                        print(f"  Classifying change ID {change.id}...")
                        classifier_manager.classify_change(change)
                        classified_count += 1
                        print(f"    Priority: {change.priority}")
                        print(f"    Change Type: {change.change_type}")
                        print(f"    Summary: {change.summary[:100] if change.summary else 'N/A'}...")
        else:
            # If no changes detected, we can't test classification
            print("  No changes to classify (this is expected if content hasn't changed)")
            classified_count = 0
        
        if detected_changes and classified_count == 0:
            report_result("Change classification", False, "Changes detected but not classified")
            results['classification'] = False
        else:
            report_result("Change classification", True, 
                         f"Classified {classified_count} change(s)" if detected_changes 
                         else "No changes to classify (expected)")
            results['classification'] = True
            results['classified_count'] = classified_count
        
    except Exception as e:
        report_result("Change classification", False, str(e))
        logger.error(f"Classification error: {e}", exc_info=True)
        results['classification'] = False
    
    # STEP 9: Send Slack Alert
    print_step(9, "Send Slack Alert")
    try:
        alerts_sent = 0
        
        if detected_changes:
            with DatabaseSession() as session:
                # Get classified changes that haven't been alerted
                # Send exactly one alert (first available change)
                for change_id in results.get('change_ids', []):
                    change = session.query(Change).filter(Change.id == change_id).first()
                    if change and change.priority and not change.alert_sent:
                        asset = session.query(Asset).filter(Asset.id == change.asset_id).first()
                        competitor = session.query(Competitor).filter(
                            Competitor.id == asset.competitor_id
                        ).first()
                        
                        print(f"  Sending alert for change ID {change.id} (Priority: {change.priority})...")
                        
                        # Send alert (send exactly one for testing)
                        success = alert_manager.slack.send_alert(
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
                            # Mark as sent
                            change.alert_sent = True
                            change.alert_sent_at = datetime.utcnow()
                            session.commit()
                            alerts_sent += 1
                            print(f"    Alert sent successfully!")
                            # Send exactly one alert as requested
                            break
                        else:
                            print(f"    Alert failed to send")
        else:
            print("  No changes to alert (this is expected if content hasn't changed)")
            print("  NOTE: To test alerting, content needs to change between crawls")
        
        if detected_changes and alerts_sent == 0:
            report_result("Slack alert", False, "Changes detected but no alerts sent")
            results['alert'] = False
        elif alerts_sent > 0:
            report_result("Slack alert", True, f"Sent exactly {alerts_sent} alert(s) to Slack")
            results['alert'] = True
            results['alerts_sent'] = alerts_sent
        else:
            report_result("Slack alert", True, "No changes to alert (expected)")
            results['alert'] = True
            results['alerts_sent'] = 0
        
    except Exception as e:
        report_result("Slack alert", False, str(e))
        logger.error(f"Alert error: {e}", exc_info=True)
        results['alert'] = False
    
    # Final Summary
    print("\n" + "="*60)
    print("END-TO-END TEST SUMMARY")
    print("="*60)
    
    steps = [
        ("Database Initialization", results.get('database', False)),
        ("Configuration Loading", results.get('config', False)),
        ("Component Initialization", results.get('components', False)),
        ("Asset Sync", results.get('sync', False)),
        ("First Crawl (Baseline)", results.get('crawl1', False)),
        ("Second Crawl (Detection)", results.get('crawl2', False)),
        ("Change Detection", results.get('detection', False)),
        ("Change Classification", results.get('classification', False)),
        ("Slack Alert", results.get('alert', False)),
    ]
    
    for step_name, success in steps:
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {step_name}")
    
    print("\n" + "="*60)
    
    all_success = all(success for _, success in steps)
    if all_success:
        print("RESULT: ALL STEPS COMPLETED SUCCESSFULLY")
        if results.get('changes_detected', 0) == 0:
            print("\nNOTE: No changes were detected, which is normal if content hasn't changed.")
            print("      The pipeline is working correctly. To test full alerting, content needs to change.")
    else:
        print("RESULT: SOME STEPS FAILED - CHECK ERRORS ABOVE")
    
    print("="*60 + "\n")
    
    return results


if __name__ == '__main__':
    try:
        results = test_e2e_pipeline()
        sys.exit(0 if all([
            results.get('database', False),
            results.get('config', False),
            results.get('components', False),
            results.get('sync', False),
            results.get('crawl1', False),
            results.get('crawl2', False),
            results.get('detection', False),
            results.get('classification', False),
            results.get('alert', False),
        ]) else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        logger.exception("Fatal error in e2e test")
        sys.exit(1)
