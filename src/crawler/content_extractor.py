"""
Content extractors for different asset types
"""
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import re
from datetime import datetime


class ContentExtractor:
    """Base class for content extractors"""
    
    def extract(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract structured data from HTML
        
        Args:
            html: HTML content
            url: Source URL
        
        Returns:
            Dictionary with extracted metadata
        """
        raise NotImplementedError


class PricingExtractor(ContentExtractor):
    """Extract pricing information from pricing pages"""
    
    def extract(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract pricing tiers, prices, and feature inclusions
        
        Returns:
            Dictionary with:
                - tiers: List of pricing tiers with name, price, features
                - has_free_tier: Boolean
                - free_tier_details: Dict with free tier info
        """
        soup = BeautifulSoup(html, 'lxml')
        metadata = {
            'tiers': [],
            'has_free_tier': False,
            'free_tier_details': None
        }
        
        # Common pricing table/container selectors
        pricing_selectors = [
            '.pricing-table', '.pricing', '.plans', '.pricing-plans',
            '[class*="pricing"]', '[class*="plan"]', '[id*="pricing"]'
        ]
        
        pricing_container = None
        for selector in pricing_selectors:
            pricing_container = soup.select_one(selector)
            if pricing_container:
                break
        
        if not pricing_container:
            # Try to find any table that might contain pricing
            tables = soup.find_all('table')
            for table in tables:
                if any(keyword in table.get_text().lower() for keyword in ['price', 'plan', 'tier', '$']):
                    pricing_container = table
                    break
        
        if pricing_container:
            # Extract pricing tiers
            tiers = self._extract_tiers(pricing_container)
            metadata['tiers'] = tiers
            
            # Check for free tier
            for tier in tiers:
                if tier.get('price', '').lower() in ['free', '$0', '0', 'free forever']:
                    metadata['has_free_tier'] = True
                    metadata['free_tier_details'] = tier
                    break
        
        return metadata
    
    def _extract_tiers(self, container) -> List[Dict[str, Any]]:
        """Extract pricing tiers from container"""
        tiers = []
        
        # Look for tier/plan cards
        tier_cards = container.find_all(['div', 'section', 'article'], 
                                        class_=re.compile(r'(tier|plan|package)', re.I))
        
        if not tier_cards:
            # Try table rows
            rows = container.find_all('tr')
            if len(rows) > 1:  # Header row + data rows
                headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                    if len(cells) >= 2:
                        tier = {
                            'name': cells[0] if cells else 'Unknown',
                            'price': cells[1] if len(cells) > 1 else '',
                            'features': cells[2:] if len(cells) > 2 else []
                        }
                        tiers.append(tier)
        else:
            for card in tier_cards:
                tier = {
                    'name': self._extract_text(card, ['h2', 'h3', '.plan-name', '.tier-name']),
                    'price': self._extract_text(card, ['.price', '.cost', '[class*="price"]']),
                    'features': self._extract_features(card)
                }
                if tier['name'] or tier['price']:
                    tiers.append(tier)
        
        return tiers
    
    def _extract_text(self, container, selectors: List[str]) -> str:
        """Extract text using multiple selector attempts"""
        for selector in selectors:
            element = container.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return ''
    
    def _extract_features(self, container) -> List[str]:
        """Extract feature list from container"""
        features = []
        
        # Look for lists
        lists = container.find_all(['ul', 'ol'])
        for ul in lists:
            items = ul.find_all('li', recursive=False)
            for item in items:
                text = item.get_text(strip=True)
                if text:
                    features.append(text)
        
        return features


class FeatureExtractor(ContentExtractor):
    """Extract feature lists from feature/solution pages"""
    
    def extract(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract feature lists and capabilities
        
        Returns:
            Dictionary with:
                - features: List of feature names/descriptions
                - categories: Dict of features by category
        """
        soup = BeautifulSoup(html, 'lxml')
        metadata = {
            'features': [],
            'categories': {}
        }
        
        # Find feature lists
        feature_containers = soup.find_all(['ul', 'ol', 'section'], 
                                          class_=re.compile(r'(feature|capability)', re.I))
        
        if not feature_containers:
            # Try to find any lists that might contain features
            all_lists = soup.find_all(['ul', 'ol'])
            for ul in all_lists:
                items = ul.find_all('li')
                if len(items) >= 3:  # Likely a feature list
                    feature_containers.append(ul)
        
        for container in feature_containers:
            items = container.find_all('li', recursive=False)
            for item in items:
                text = item.get_text(strip=True)
                if text and len(text) > 5:  # Filter out very short items
                    metadata['features'].append(text)
        
        # Try to categorize features by headings
        sections = soup.find_all(['section', 'div'], class_=re.compile(r'(feature|section)', re.I))
        for section in sections:
            heading = section.find(['h2', 'h3', 'h4'])
            if heading:
                category = heading.get_text(strip=True)
                items = section.find_all('li')
                if items:
                    metadata['categories'][category] = [li.get_text(strip=True) for li in items]
        
        return metadata


class ChangelogExtractor(ContentExtractor):
    """Extract changelog entries with dates"""
    
    def extract(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract changelog entries with dates
        
        Returns:
            Dictionary with:
                - entries: List of entries with date and content
        """
        soup = BeautifulSoup(html, 'lxml')
        metadata = {
            'entries': []
        }
        
        # Look for changelog entries (common patterns)
        entries = soup.find_all(['article', 'div', 'li'], 
                               class_=re.compile(r'(changelog|update|release|entry)', re.I))
        
        if not entries:
            # Try to find date + content patterns
            all_elements = soup.find_all(['div', 'article', 'section'])
            for elem in all_elements:
                date_elem = elem.find(['time', 'span', 'div'], 
                                     class_=re.compile(r'(date|time|published)', re.I))
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    content = elem.get_text(strip=True)
                    if date_text and content:
                        metadata['entries'].append({
                            'date': date_text,
                            'content': content
                        })
        else:
            for entry in entries:
                date_elem = entry.find(['time', 'span', 'div'], 
                                      class_=re.compile(r'(date|time)', re.I))
                date_text = date_elem.get_text(strip=True) if date_elem else ''
                content = entry.get_text(strip=True)
                if content:
                    metadata['entries'].append({
                        'date': date_text,
                        'content': content
                    })
        
        return metadata


class SitemapExtractor(ContentExtractor):
    """Extract URLs from XML sitemap"""
    
    def extract(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract URLs from XML sitemap
        
        Returns:
            Dictionary with:
                - urls: List of URLs found in sitemap
        """
        soup = BeautifulSoup(html, 'xml')
        metadata = {
            'urls': []
        }
        
        # Extract URLs from sitemap
        url_tags = soup.find_all('url')
        for url_tag in url_tags:
            loc = url_tag.find('loc')
            if loc:
                url_text = loc.get_text(strip=True)
                if url_text:
                    metadata['urls'].append(url_text)
        
        # Also check for sitemapindex
        sitemap_tags = soup.find_all('sitemap')
        for sitemap_tag in sitemap_tags:
            loc = sitemap_tag.find('loc')
            if loc:
                url_text = loc.get_text(strip=True)
                if url_text:
                    metadata['urls'].append(url_text)
        
        return metadata


class BlogExtractor(ContentExtractor):
    """Extract blog posts filtered by topic"""
    
    def extract(self, html: str, url: str, filters: List[str] = None) -> Dict[str, Any]:
        """
        Extract blog posts filtered by topic keywords
        
        Args:
            html: HTML content
            url: Source URL
            filters: List of keywords to filter by (product, pricing, AI, compliance)
        
        Returns:
            Dictionary with:
                - posts: List of posts with title, date, tags, url
        """
        soup = BeautifulSoup(html, 'lxml')
        metadata = {
            'posts': []
        }
        
        filters = filters or []
        filter_keywords = [kw.lower() for kw in filters]
        
        # Find blog post containers
        posts = soup.find_all(['article', 'div'], 
                            class_=re.compile(r'(post|article|blog)', re.I))
        
        if not posts:
            # Try alternative selectors
            posts = soup.find_all(['div', 'section'], 
                                class_=re.compile(r'(entry|item)', re.I))
        
        for post in posts:
            title_elem = post.find(['h2', 'h3', 'h4', 'a'], 
                                 class_=re.compile(r'(title|heading)', re.I))
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            date_elem = post.find(['time', 'span', 'div'], 
                                class_=re.compile(r'(date|time|published)', re.I))
            date_text = date_elem.get_text(strip=True) if date_elem else ''
            
            # Extract tags/categories
            tags = []
            tag_elems = post.find_all(['a', 'span'], 
                                    class_=re.compile(r'(tag|category|topic)', re.I))
            for tag_elem in tag_elems:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)
            
            # Extract link
            link_elem = post.find('a', href=True)
            post_url = urljoin(url, link_elem['href']) if link_elem else url
            
            # Filter by keywords if filters provided
            if filters:
                post_text = post.get_text().lower()
                title_lower = title.lower()
                tags_lower = ' '.join([t.lower() for t in tags])
                
                matches_filter = any(
                    keyword in post_text or keyword in title_lower or keyword in tags_lower
                    for keyword in filter_keywords
                )
                
                if not matches_filter:
                    continue
            
            if title:  # Only include posts with titles
                metadata['posts'].append({
                    'title': title,
                    'date': date_text,
                    'tags': tags,
                    'url': post_url
                })
        
        return metadata


class ComplianceExtractor(ContentExtractor):
    """Extract compliance certifications and standards"""
    
    def extract(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract compliance certifications and standards
        
        Returns:
            Dictionary with:
                - certifications: List of certification names
                - standards: List of compliance standards
        """
        soup = BeautifulSoup(html, 'lxml')
        metadata = {
            'certifications': [],
            'standards': []
        }
        
        # Common compliance keywords
        compliance_keywords = [
            'SOC 2', 'SOC 1', 'ISO 27001', 'GDPR', 'HIPAA', 'PCI DSS',
            'FedRAMP', 'CCPA', 'SOC 2 Type II', 'ISO', 'certified', 'compliance'
        ]
        
        # Find compliance sections
        text = soup.get_text()
        
        for keyword in compliance_keywords:
            if keyword.lower() in text.lower():
                # Try to find the context around the keyword
                pattern = re.compile(f'.{{0,50}}{re.escape(keyword)}.{{0,50}}', re.IGNORECASE)
                matches = pattern.findall(text)
                for match in matches:
                    if 'certification' in match.lower() or 'certified' in match.lower():
                        if keyword not in metadata['certifications']:
                            metadata['certifications'].append(keyword)
                    elif 'standard' in match.lower() or 'compliance' in match.lower():
                        if keyword not in metadata['standards']:
                            metadata['standards'].append(keyword)
        
        # Also look for badges/logos that might indicate certifications
        images = soup.find_all('img', alt=re.compile(r'(cert|compliance|iso|soc)', re.I))
        for img in images:
            alt_text = img.get('alt', '')
            if alt_text:
                metadata['certifications'].append(alt_text)
        
        return metadata


def get_extractor(asset_type: str) -> ContentExtractor:
    """
    Get appropriate extractor for asset type
    
    Args:
        asset_type: Type of asset (pricing, features, changelog, etc.)
    
    Returns:
        ContentExtractor instance
    """
    extractors = {
        'pricing': PricingExtractor(),
        'features': FeatureExtractor(),
        'changelog': ChangelogExtractor(),
        'sitemap': SitemapExtractor(),
        'blog': BlogExtractor(),
        'compliance': ComplianceExtractor(),
        'news': FeatureExtractor(),  # News pages can use feature extractor
        'twitter': None,  # Will be instantiated with query parameter
    }
    
    return extractors.get(asset_type, ContentExtractor())

