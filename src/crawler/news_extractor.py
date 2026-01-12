"""
News extractor using NewsAPI.org API
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

load_dotenv()
logger = logging.getLogger(__name__)


class NewsExtractor:
    """Extract news articles using NewsAPI.org API"""
    
    def __init__(self):
        """Initialize News extractor"""
        self.api_key = os.getenv('NEWS_API_KEY')
        if not self.api_key:
            logger.warning("NEWS_API_KEY not found in .env. News API will not be used.")
            self.api_key = None
        else:
            logger.info("NewsAPI.org client initialized.")
        
        self.base_url = "https://newsapi.org/v2"
    
    def extract(self, html: str, url: str, query: str = None, competitor_name: str = None) -> Dict[str, Any]:
        """
        Extract news articles using NewsAPI.org API
        
        Args:
            html: Not used for API, kept for interface compatibility
            url: Not used for API, kept for interface compatibility
            query: Search query (e.g., "DocuSign OR docusign")
            competitor_name: Name of competitor (used if query not provided)
        
        Returns:
            Dictionary with:
                - articles: List of news articles
        """
        if not self.api_key:
            logger.error("News API key not initialized. Cannot extract news.")
            return {'articles': []}
        
        if not query and not competitor_name:
            logger.warning("No search query or competitor name provided. Cannot extract news.")
            return {'articles': []}
        
        # Build query if not provided
        if not query:
            query = competitor_name
        
        metadata = {'articles': []}
        
        try:
            # Use the everything endpoint for comprehensive search
            # Note: Free tier has limitations (100 requests/day, 1 month back)
            articles = self._search_articles(query)
            metadata['articles'] = articles
            logger.info(f"Extracted {len(articles)} news articles for query: {query}")
        
        except Exception as e:
            logger.error(f"News API error for query '{query}': {e}")
        
        return metadata
    
    def _search_articles(self, query: str, max_results: int = 20, 
                        sort_by: str = 'publishedAt', 
                        language: str = 'en') -> List[Dict[str, Any]]:
        """
        Search for news articles using NewsAPI.org
        
        Args:
            query: Search query (keywords, phrases, etc.)
            max_results: Maximum number of articles to return
            sort_by: Sort order ('relevancy', 'popularity', 'publishedAt')
            language: Language code (default: 'en')
        
        Returns:
            List of article dictionaries
        """
        articles = []
        
        try:
            # Calculate date range (last 7 days for free tier, or use from/to parameters)
            # Free tier allows up to 1 month back
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)  # Last 7 days
            
            url = f"{self.base_url}/everything"
            params = {
                'q': query,
                'apiKey': self.api_key,
                'sortBy': sort_by,
                'language': language,
                'pageSize': min(max_results, 100),  # API limit is 100 per page
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d')
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'ok' and data.get('articles'):
                for article in data['articles']:
                    # Filter out articles without content
                    if article.get('title') and article.get('url'):
                        articles.append({
                            'title': article.get('title', ''),
                            'description': article.get('description', ''),
                            'url': article.get('url', ''),
                            'published_at': article.get('publishedAt', ''),
                            'source': article.get('source', {}).get('name', 'Unknown'),
                            'author': article.get('author', ''),
                            'content': article.get('content', '')[:500] if article.get('content') else '',  # Truncate content
                            'url_to_image': article.get('urlToImage', '')
                        })
            
            elif data.get('status') == 'error':
                error_message = data.get('message', 'Unknown error')
                logger.error(f"NewsAPI error: {error_message}")
                # Handle rate limiting
                if 'rate limit' in error_message.lower():
                    logger.warning("NewsAPI rate limit reached. Please wait before retrying.")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"NewsAPI request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during news extraction: {e}")
        
        return articles
    
    def search_competitor_news(self, competitor_name: str, 
                              additional_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search for news articles related to a competitor
        
        Args:
            competitor_name: Name of the competitor
            additional_keywords: Additional keywords to include in search
        
        Returns:
            List of article dictionaries
        """
        # Build search query
        query_parts = [f'"{competitor_name}"']
        
        if additional_keywords:
            for keyword in additional_keywords:
                query_parts.append(f'"{keyword}"')
        
        # Combine with OR operator
        query = ' OR '.join(query_parts)
        
        return self._search_articles(query, max_results=20)
