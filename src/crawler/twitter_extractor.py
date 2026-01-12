"""
Twitter/X extractor using Twitter API v2 search endpoint
"""
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Try to import tweepy for Twitter API
try:
    import tweepy
    HAS_TWEEPY = True
except ImportError:
    HAS_TWEEPY = False

from src.crawler.content_extractor import ContentExtractor


class TwitterExtractor(ContentExtractor):
    """Extract tweets using Twitter API v2 search endpoint"""
    
    def __init__(self):
        """Initialize Twitter extractor"""
        if not HAS_TWEEPY:
            raise ImportError("tweepy is required for Twitter monitoring. Install with: pip install tweepy")
        
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        if not self.bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN not found in environment variables")
        
        # Initialize Twitter API v2 client
        self.client = tweepy.Client(bearer_token=self.bearer_token)
    
    def extract(self, html: str, url: str, query: str = None) -> Dict[str, Any]:
        """
        Extract tweets using Twitter API v2 search endpoint
        
        Args:
            html: HTML content (not used for API, kept for interface compatibility)
            url: Not used for API search, kept for interface compatibility
            query: Search query (e.g., "from:competitor OR @competitor")
        
        Returns:
            Dictionary with:
                - tweets: List of tweets with text, date, url, author
        """
        if not query:
            raise ValueError("Twitter search query is required")
        
        metadata = {
            'tweets': []
        }
        
        try:
            tweets = self._search_recent_tweets(query)
            metadata['tweets'] = tweets
        except Exception as e:
            print(f"Twitter API error: {e}")
            # Return empty list on error
            metadata['tweets'] = []
        
        return metadata
    
    def _search_recent_tweets(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for recent tweets using Twitter API v2
        
        Args:
            query: Search query (supports Twitter search operators)
            max_results: Maximum number of tweets to return (10-100)
        
        Returns:
            List of tweet dictionaries
        """
        tweets = []
        
        try:
            # Use the search_recent_tweets endpoint
            # This corresponds to GET /2/tweets/search/recent
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),  # API limit is 100
                tweet_fields=['created_at', 'public_metrics', 'author_id', 'text'],
                expansions=['author_id'],
                user_fields=['username', 'name']
            )
            
            if not response.data:
                return tweets
            
            # Create user lookup dictionary
            users = {}
            if response.includes and 'users' in response.includes:
                for user in response.includes['users']:
                    users[user.id] = user
            
            # Process tweets
            for tweet in response.data:
                author = users.get(tweet.author_id) if tweet.author_id else None
                username = author.username if author else 'unknown'
                
                tweets.append({
                    'text': tweet.text,
                    'date': tweet.created_at.isoformat() if tweet.created_at else None,
                    'url': f"https://twitter.com/{username}/status/{tweet.id}",
                    'id': str(tweet.id),
                    'author': username,
                    'author_name': author.name if author else None,
                    'metrics': tweet.public_metrics if hasattr(tweet, 'public_metrics') else {}
                })
        
        except tweepy.TooManyRequests:
            print("Twitter API rate limit exceeded. Please wait before retrying.")
        except tweepy.Unauthorized:
            print("Twitter API authentication failed. Check your bearer token.")
        except Exception as e:
            print(f"Twitter API error: {e}")
        
        return tweets
    
    def search_competitor_tweets(self, competitor_name: str, 
                                additional_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search for tweets related to a competitor
        
        Args:
            competitor_name: Name of the competitor
            additional_keywords: Additional keywords to include in search
        
        Returns:
            List of tweet dictionaries
        """
        # Build search query
        # Search for tweets from the competitor's account or mentioning them
        query_parts = [
            f'from:{competitor_name}',
            f'@{competitor_name}',
            f'"{competitor_name}"'
        ]
        
        if additional_keywords:
            for keyword in additional_keywords:
                query_parts.append(f'"{keyword}"')
        
        # Combine with OR operator
        query = ' OR '.join(query_parts)
        
        # Add filters to reduce noise
        query += ' -is:retweet lang:en'  # Exclude retweets, English only
        
        return self._search_recent_tweets(query, max_results=20)
