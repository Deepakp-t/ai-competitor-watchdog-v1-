"""
Main entry point for AI Competitor Watchdog
"""
import sys
import os
import argparse

# Add project root to path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from src.storage.database import init_database
from src.config.loader import load_competitor_config
from src.crawler.scheduler import CrawlScheduler
from src.alerting.alert_manager import AlertManager


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI Competitor Watchdog V1')
    parser.add_argument('--init-db', action='store_true', help='Initialize database only')
    parser.add_argument('--crawl-once', action='store_true', help='Run a single crawl cycle and exit')
    parser.add_argument('--start-scheduler', action='store_true', help='Start the scheduler (default)')
    parser.add_argument('--start-alert-scheduler', action='store_true', help='Start only the alert scheduler')
    
    args = parser.parse_args()
    
    print("AI Competitor Watchdog V1")
    print("=" * 50)
    
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
        for comp in competitors:
            print(f"      - {comp['name']}: {len(comp.get('assets', []))} asset(s)")
    except Exception as e:
        print(f"   [ERROR] Configuration loading failed: {e}")
        return 1
    
    # If just initializing database, exit
    if args.init_db:
        print("\n" + "=" * 50)
        print("Database initialized. Exiting.")
        return 0
    
    # Initialize alert manager
    print("\n3. Initializing alert manager...")
    try:
        alert_manager = AlertManager()
        print("   [OK] Alert manager ready")
    except Exception as e:
        print(f"   [WARNING] Alert manager not available: {e}")
        alert_manager = None
    
    # If just starting alert scheduler, do that and exit
    if args.start_alert_scheduler:
        if alert_manager:
            print("\n" + "=" * 50)
            print("Starting alert scheduler...")
            print("Press Ctrl+C to stop")
            print("=" * 50)
            alert_manager.start_scheduler()
        else:
            print("   [ERROR] Cannot start alert scheduler without Slack configuration")
            return 1
        return 0
    
    # Initialize scheduler
    print("\n4. Initializing crawler scheduler...")
    scheduler = CrawlScheduler(alert_manager=alert_manager)
    print("   [OK] Scheduler ready")
    
    print("\n" + "=" * 50)
    
    # Run based on arguments
    if args.crawl_once:
        print("Running single crawl cycle...")
        stats = scheduler.run_once()
        print(f"\nCrawl complete:")
        print(f"  Total assets: {stats['total']}")
        print(f"  Due for crawl: {stats['due']}")
        print(f"  Successful: {stats['success']}")
        print(f"  Failed: {stats['failed']}")
        return 0
    else:
        # Default: start scheduler
        print("Starting scheduler...")
        if alert_manager:
            print("Alert scheduler will run in background")
        print("Press Ctrl+C to stop")
        print("=" * 50)
        
        # Start alert scheduler in background thread if available
        if alert_manager:
            import threading
            alert_thread = threading.Thread(target=alert_manager.start_scheduler, daemon=True)
            alert_thread.start()
        
        scheduler.start_scheduler(run_immediately=True)
        return 0


if __name__ == '__main__':
    sys.exit(main())

