"""
Crawl scheduler for automated crawling based on frequency
"""
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from src.storage.database import DatabaseSession
from src.storage.models import Asset, Snapshot, Competitor
from src.config.loader import get_all_assets, load_competitor_config
from src.crawler.web_crawler import WebCrawler
from src.crawler.content_extractor import get_extractor
from src.diff.change_detector import ChangeDetector
from src.classifier.classifier_manager import ClassifierManager
from src.alerting.alert_manager import AlertManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CrawlScheduler:
    """Manages scheduled crawling of competitor assets"""
    
    def __init__(self, alert_manager: AlertManager = None):
        """
        Initialize scheduler with crawler
        
        Args:
            alert_manager: Optional alert manager for sending alerts
        """
        self.crawler = WebCrawler()
        self.config = load_competitor_config()
        self.change_detector = ChangeDetector()
        
        # Initialize alert manager if not provided
        if alert_manager is None:
            try:
                alert_manager = AlertManager()
            except Exception as e:
                logger.warning(f"Alert manager not available: {e}")
                alert_manager = None
        
        self.alert_manager = alert_manager
        self.classifier_manager = ClassifierManager(alert_manager=alert_manager)
    
    def _get_last_snapshot(self, asset_id: int, session=None) -> Optional[Snapshot]:
        """
        Get the most recent snapshot for an asset
        
        Args:
            asset_id: Asset ID
            session: Database session (optional, creates new if not provided)
        
        Returns:
            Most recent Snapshot or None
        """
        if session is None:
            with DatabaseSession() as session:
                snapshot = session.query(Snapshot)\
                    .filter(Snapshot.asset_id == asset_id)\
                    .order_by(Snapshot.crawl_timestamp.desc())\
                    .first()
                return snapshot
        else:
            snapshot = session.query(Snapshot)\
                .filter(Snapshot.asset_id == asset_id)\
                .order_by(Snapshot.crawl_timestamp.desc())\
                .first()
            return snapshot
    
    def _is_crawl_due(self, asset: Asset, session=None) -> bool:
        """
        Check if asset is due for crawling based on frequency
        
        Args:
            asset: Asset to check
            session: Database session (optional)
        
        Returns:
            True if crawl is due, False otherwise
        """
        last_snapshot = self._get_last_snapshot(asset.id, session)
        
        if not last_snapshot:
            # No previous snapshot, crawl is due
            return True
        
        # Calculate time since last crawl
        time_since_last = datetime.utcnow() - last_snapshot.crawl_timestamp
        
        # Check frequency
        if asset.crawl_frequency == 'daily':
            return time_since_last >= timedelta(days=1)
        elif asset.crawl_frequency == 'weekly':
            return time_since_last >= timedelta(weeks=1)
        else:
            # Unknown frequency, default to daily
            logger.warning(f"Unknown crawl frequency '{asset.crawl_frequency}' for asset {asset.id}, defaulting to daily")
            return time_since_last >= timedelta(days=1)
    
    def _get_or_create_competitor(self, session, competitor_name: str, base_url: str) -> Competitor:
        """
        Get existing competitor or create new one
        
        Args:
            session: Database session
            competitor_name: Competitor name
            base_url: Competitor base URL
        
        Returns:
            Competitor instance
        """
        competitor = session.query(Competitor).filter(Competitor.name == competitor_name).first()
        if not competitor:
            competitor = Competitor(name=competitor_name, base_url=base_url)
            session.add(competitor)
            session.commit()
            session.refresh(competitor)
        return competitor
    
    def _get_or_create_asset(self, session, competitor: Competitor, asset_config: Dict[str, Any]) -> Optional[Asset]:
        """
        Get existing asset or create new one
        
        Args:
            session: Database session
            competitor: Competitor instance
            asset_config: Asset configuration dictionary
        
        Returns:
            Asset instance or None if URL is missing
        """
        # Skip assets with null or missing URLs
        if not asset_config.get('url'):
            logger.warning(f"Skipping asset {asset_config.get('type')} for {competitor.name} - no URL provided")
            return None
        
        asset = session.query(Asset).filter(
            Asset.competitor_id == competitor.id,
            Asset.url == asset_config['url']
        ).first()
        
        if not asset:
            asset = Asset(
                competitor_id=competitor.id,
                asset_type=asset_config['type'],
                url=asset_config['url'],
                crawl_frequency=asset_config['crawl_frequency'],
                priority_threshold=asset_config.get('priority_threshold')
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
        else:
            # Update asset configuration if it changed
            asset.asset_type = asset_config['type']
            asset.crawl_frequency = asset_config['crawl_frequency']
            asset.priority_threshold = asset_config.get('priority_threshold')
            session.commit()
        
        return asset
    
    def _sync_assets_from_config(self):
        """
        Sync assets from configuration file to database
        Creates competitors and assets if they don't exist
        """
        with DatabaseSession() as session:
            all_assets_config = get_all_assets(self.config)
            
            for asset_config in all_assets_config:
                competitor_name = asset_config['competitor_name']
                base_url = asset_config['competitor_base_url']
                
                # Get or create competitor
                competitor = self._get_or_create_competitor(session, competitor_name, base_url)
                
                # Get or create asset (skip if None returned)
                asset = self._get_or_create_asset(session, competitor, asset_config)
                if asset is None:
                    continue
            
            logger.info(f"Synced {len(all_assets_config)} assets from configuration")
    
    def _crawl_asset(self, asset: Asset) -> bool:
        """
        Crawl a single asset and store snapshot
        
        Args:
            asset: Asset to crawl
        
        Returns:
            True if crawl was successful, False otherwise
        """
        # Get asset details before session closes
        asset_id = asset.id
        asset_url = asset.url
        asset_type = asset.asset_type
        competitor_name = asset.competitor.name if asset.competitor else "Unknown"
        
        logger.info(f"Crawling {competitor_name} - {asset_type}: {asset_url}")
        
        try:
            # Handle Twitter and News separately (uses API, not web crawling)
            if asset_type == 'twitter':
                # Get asset config
                asset_config = next(
                    (a for a in get_all_assets(self.config) 
                     if a['url'] == asset_url),
                    {}
                )
                
                # Extract using Twitter API
                from src.crawler.twitter_extractor import TwitterExtractor
                try:
                    twitter_extractor = TwitterExtractor()
                    query = asset_config.get('query')
                    if not query:
                        # Build query from competitor name if not provided
                        query_competitor_name = competitor_name.lower().replace(' ', '')
                        query = f'from:{query_competitor_name} OR @{query_competitor_name} OR "{competitor_name}" -is:retweet lang:en'
                    
                    metadata = twitter_extractor.extract('', asset_url, query)
                    
                    # Create content text from tweets for hashing
                    tweets_text = '\n'.join([t.get('text', '') for t in metadata.get('tweets', [])])
                    content_hash = self.crawler.compute_content_hash(tweets_text)
                    
                    # Store snapshot
                    with DatabaseSession() as session:
                        asset = session.query(Asset).filter(Asset.id == asset_id).first()
                        snapshot = Snapshot(
                            asset_id=asset_id,
                            content_hash=content_hash,
                            content_text=tweets_text,
                            content_html=None,  # No HTML for Twitter
                            metadata_json=metadata,
                            crawl_timestamp=datetime.utcnow(),
                            http_status=200
                        )
                        session.add(snapshot)
                        session.commit()
                    
                    logger.info(f"Successfully crawled and stored Twitter snapshot for {asset_url}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error with Twitter API for {asset_url}: {e}")
                    return False
            
            # Handle News API separately
            elif asset_type == 'news':
                # Get asset config
                asset_config = next(
                    (a for a in get_all_assets(self.config) 
                     if a['url'] == asset_url),
                    {}
                )
                
                # Extract using News API
                from src.crawler.news_extractor import NewsExtractor
                try:
                    news_extractor = NewsExtractor()
                    query = asset_config.get('query')
                    if not query:
                        # Use competitor name as query if not provided
                        query = competitor_name
                    
                    metadata = news_extractor.extract('', asset_url, query=query, competitor_name=competitor_name)
                    
                    # Create content text from articles for hashing
                    articles_text = '\n'.join([
                        f"{a.get('title', '')} {a.get('description', '')}" 
                        for a in metadata.get('articles', [])
                    ])
                    content_hash = self.crawler.compute_content_hash(articles_text)
                    
                    # Store snapshot
                    with DatabaseSession() as session:
                        snapshot = Snapshot(
                            asset_id=asset_id,
                            content_hash=content_hash,
                            content_text=articles_text,
                            content_html=None,  # No HTML for News API
                            metadata_json=metadata,
                            crawl_timestamp=datetime.utcnow(),
                            http_status=200
                        )
                        session.add(snapshot)
                        session.commit()
                    
                    logger.info(f"Successfully crawled and stored News snapshot for {asset_url}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error with News API for {asset_url}: {e}")
                    return False
            
            # For non-API assets, use web crawler
            crawl_result = self.crawler.crawl(asset_url)
            
            if crawl_result['error']:
                logger.error(f"Error crawling {asset_url}: {crawl_result['error']}")
                # Store snapshot with error for tracking
                with DatabaseSession() as session:
                    snapshot = Snapshot(
                        asset_id=asset_id,
                        content_hash='',  # No hash for errors
                        content_text=None,
                        content_html=None,
                        metadata_json=None,
                        crawl_timestamp=datetime.utcnow(),
                        http_status=crawl_result.get('http_status')
                    )
                    session.add(snapshot)
                    session.commit()
                return False
            
            # Extract structured metadata
            extractor = get_extractor(asset_type)
            metadata = None
            
            if crawl_result['content_html']:
                # Pass filters/options for specific extractors
                asset_config = next(
                    (a for a in get_all_assets(self.config) 
                     if a['url'] == asset_url),
                    {}
                )
                
                if asset_type == 'blog':
                    # Get filters from config
                    filters = asset_config.get('filters', [])
                    metadata = extractor.extract(crawl_result['content_html'], asset_url, filters)
                else:
                    metadata = extractor.extract(crawl_result['content_html'], asset_url)
            
            # Store snapshot
            with DatabaseSession() as session:
                snapshot = Snapshot(
                    asset_id=asset_id,
                    content_hash=crawl_result['content_hash'],
                    content_text=crawl_result['content_text'],
                    content_html=crawl_result['content_html'],
                    metadata_json=metadata,
                    crawl_timestamp=datetime.utcnow(),
                    http_status=crawl_result['http_status']
                )
                session.add(snapshot)
                session.commit()
            
            logger.info(f"Successfully crawled and stored snapshot for {asset_url}")
            
            # Detect changes after successful crawl (need to reload asset in new session)
            try:
                with DatabaseSession() as session:
                    asset = session.query(Asset).filter(Asset.id == asset_id).first()
                    if asset:
                        changes = self.change_detector.detect_changes_for_asset(asset)
                        if changes:
                            logger.info(f"Detected {len(changes)} change(s) for {asset_url}")
                            # Classify changes
                            for change in changes:
                                try:
                                    self.classifier_manager.classify_change(change)
                                except Exception as e:
                                    logger.error(f"Error classifying change {change.id}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error detecting changes for {asset_url}: {e}", exc_info=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Exception while crawling {asset_url}: {e}", exc_info=True)
            return False
    
    def crawl_due_assets(self) -> Dict[str, int]:
        """
        Crawl all assets that are due for crawling
        
        Returns:
            Dictionary with counts: {'total': X, 'due': Y, 'success': Z, 'failed': W}
        """
        # Sync assets from config first
        self._sync_assets_from_config()
        
        with DatabaseSession() as session:
            all_assets = session.query(Asset).join(Competitor).all()
            asset_ids = [asset.id for asset in all_assets]
        
        stats = {
            'total': len(asset_ids),
            'due': 0,
            'success': 0,
            'failed': 0
        }
        
        # Process each asset in its own session context
        for asset_id in asset_ids:
            with DatabaseSession() as session:
                asset = session.query(Asset).filter(Asset.id == asset_id).first()
                if not asset:
                    continue
                
                if self._is_crawl_due(asset, session):
                    stats['due'] += 1
                    if self._crawl_asset(asset):
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
        
        logger.info(f"Crawl cycle complete: {stats}")
        
        # After crawling, detect changes for all assets
        # (This catches any changes that might have been missed during individual crawls)
        try:
            all_changes = self.change_detector.detect_changes_for_all_assets()
            if all_changes:
                logger.info(f"Detected {len(all_changes)} total changes after crawl cycle")
                # Classify all detected changes
                for change in all_changes:
                    try:
                        self.classifier_manager.classify_change(change)
                    except Exception as e:
                        logger.error(f"Error classifying change {change.id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error in post-crawl change detection: {e}", exc_info=True)
        
        return stats
    
    def start_scheduler(self, run_immediately: bool = True):
        """
        Start the scheduler
        
        Args:
            run_immediately: If True, run crawl immediately, then schedule
        """
        # Sync assets on startup
        self._sync_assets_from_config()
        
        # Schedule periodic crawls
        # Run every hour to check for due assets
        schedule.every().hour.do(self.crawl_due_assets)
        
        # Also run daily at 2 AM for consistency
        schedule.every().day.at("02:00").do(self.crawl_due_assets)
        
        logger.info("Scheduler started. Checking for due assets every hour.")
        
        if run_immediately:
            logger.info("Running initial crawl...")
            self.crawl_due_assets()
        
        # Run scheduler loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
    
    def run_once(self):
        """
        Run a single crawl cycle (useful for testing or manual runs)
        """
        return self.crawl_due_assets()

