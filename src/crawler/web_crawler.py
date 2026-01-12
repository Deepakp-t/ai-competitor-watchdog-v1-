"""
Basic web crawler with rate limiting, robots.txt respect, and content extraction
"""
import time
import hashlib
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import os
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()


class WebCrawler:
    """Web crawler with rate limiting and robots.txt respect"""
    
    def __init__(self, user_agent: str = None, rate_limit_delay: float = None, timeout: int = None):
        """
        Initialize web crawler
        
        Args:
            user_agent: User agent string (defaults to env var or default)
            rate_limit_delay: Seconds to wait between requests (defaults to env var or 2.0)
            timeout: Request timeout in seconds (defaults to env var or 30)
        """
        self.user_agent = user_agent or os.getenv('CRAWL_USER_AGENT', 'AI-Competitor-Watchdog/1.0')
        self.rate_limit_delay = float(rate_limit_delay or os.getenv('CRAWL_RATE_LIMIT_DELAY', '2.0'))
        self.timeout = int(timeout or os.getenv('CRAWL_TIMEOUT', '30'))
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Cache robots.txt parsers per domain
        self.robots_cache: Dict[str, RobotFileParser] = {}
        
        # Track last request time per domain for rate limiting
        self.last_request_time: Dict[str, float] = {}
    
    def _get_robots_parser(self, url: str) -> Optional[RobotFileParser]:
        """
        Get or create robots.txt parser for a domain
        
        Args:
            url: URL to check robots.txt for
        
        Returns:
            RobotFileParser instance or None if robots.txt is not accessible
        """
        parsed_url = urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if domain not in self.robots_cache:
            robots_url = urljoin(domain, '/robots.txt')
            rp = RobotFileParser()
            try:
                rp.set_url(robots_url)
                rp.read()
                self.robots_cache[domain] = rp
            except Exception as e:
                # If robots.txt is not accessible, allow crawling but log
                print(f"Warning: Could not fetch robots.txt for {domain}: {e}")
                return None
        
        return self.robots_cache.get(domain)
    
    def _can_fetch(self, url: str) -> bool:
        """
        Check if URL can be fetched according to robots.txt
        
        Args:
            url: URL to check
        
        Returns:
            True if allowed, False otherwise
        """
        robots_parser = self._get_robots_parser(url)
        if robots_parser is None:
            return True  # If no robots.txt, allow crawling
        
        return robots_parser.can_fetch(self.user_agent, url)
    
    def _rate_limit(self, url: str):
        """
        Apply rate limiting based on domain
        
        Args:
            url: URL being requested
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        if domain in self.last_request_time:
            time_since_last = time.time() - self.last_request_time[domain]
            if time_since_last < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last
                time.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()
    
    def fetch(self, url: str, max_retries: int = 3) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Fetch URL content with retry logic
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
        
        Returns:
            Tuple of (content_html, http_status, error_message)
            Returns (None, status_code, error_message) on failure
        """
        # Check robots.txt
        if not self._can_fetch(url):
            return None, None, f"Blocked by robots.txt: {url}"
        
        # Apply rate limiting
        self._rate_limit(url)
        
        # Fetch with retries
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
                return response.text, response.status_code, None
            except requests.exceptions.Timeout:
                error_msg = f"Timeout fetching {url} (attempt {attempt + 1}/{max_retries})"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None, None, error_msg
            except requests.exceptions.RequestException as e:
                error_msg = f"Error fetching {url}: {e} (attempt {attempt + 1}/{max_retries})"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, None, error_msg
        
        return None, None, f"Failed to fetch {url} after {max_retries} attempts"
    
    def extract_content(self, html: str) -> Tuple[str, str]:
        """
        Extract clean text and normalized HTML from raw HTML
        
        Args:
            html: Raw HTML content
        
        Returns:
            Tuple of (clean_text, normalized_html)
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        # Remove common dynamic/ad elements (can be extended)
        for element in soup.find_all(['iframe', 'embed', 'object']):
            element.decompose()
        
        # Try to extract main content (common patterns)
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.content', '#content', 'body']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if main_content:
            content_soup = main_content
        else:
            content_soup = soup
        
        # Get text
        text = content_soup.get_text(separator=' ', strip=True)
        
        # Normalize whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        clean_text = '\n'.join(lines)
        
        # Get normalized HTML (for structured extraction)
        normalized_html = str(content_soup)
        
        return clean_text, normalized_html
    
    def compute_content_hash(self, content: str) -> str:
        """
        Compute SHA256 hash of content
        
        Args:
            content: Content string to hash
        
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def crawl(self, url: str) -> Dict:
        """
        Complete crawl operation: fetch, extract, hash
        
        Args:
            url: URL to crawl
        
        Returns:
            Dictionary with:
                - content_html: Raw HTML (or None on error)
                - content_text: Clean extracted text (or None on error)
                - content_hash: SHA256 hash of content (or None on error)
                - http_status: HTTP status code (or None on error)
                - error: Error message (or None on success)
        """
        html, status_code, error = self.fetch(url)
        
        if error:
            return {
                'content_html': None,
                'content_text': None,
                'content_hash': None,
                'http_status': status_code,
                'error': error
            }
        
        clean_text, normalized_html = self.extract_content(html)
        content_hash = self.compute_content_hash(clean_text)
        
        return {
            'content_html': html,
            'content_text': clean_text,
            'content_hash': content_hash,
            'http_status': status_code,
            'error': None
        }

