"""
Forum scraping implementation with support for multiple platforms.
"""

import logging
from typing import Dict, List, Any, Generator, Optional
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin
import time

@dataclass
class ForumPost:
    """Represents a forum post."""
    id: str
    title: str
    author: str
    content: str
    timestamp: datetime
    url: str
    category: str
    replies: int
    views: int
    platform: str
    raw_data: Dict[str, Any]

@dataclass
class ForumComment:
    """Represents a comment on a forum post."""
    id: str
    post_id: str
    author: str
    content: str
    timestamp: datetime
    parent_id: Optional[str]
    platform: str
    raw_data: Dict[str, Any]

class ForumScraper:
    """Base class for forum scraping."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize forum scraper.
        
        Args:
            config: Scraper configuration
        """
        self.config = config
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(
            max_requests=config['scraping']['forum']['rate_limit']['requests_per_minute'],
            time_window=60
        )
        
    def make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        Make an HTTP request with rate limiting.
        
        Args:
            url: Request URL
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response object
        """
        self.rate_limiter.wait()
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

class CommonwealthScraper(ForumScraper):
    """Scraper for Commonwealth forums."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config['scraping']['forum']['commonwealth']['url']
        self.community = config['scraping']['forum']['commonwealth']['community']
        
    def get_posts(self, category: Optional[str] = None) -> Generator[ForumPost, None, None]:
        """Get forum posts."""
        page = 1
        while True:
            url = f"{self.base_url}/api/communities/{self.community}/threads"
            params = {'page': page}
            if category:
                params['category'] = category
                
            response = self.make_request(url, params=params)
            data = response.json()
            
            if not data['threads']:
                break
                
            for thread in data['threads']:
                yield ForumPost(
                    id=thread['id'],
                    title=thread['title'],
                    author=thread['author']['address'],
                    content=thread['body'],
                    timestamp=datetime.fromisoformat(thread['created_at']),
                    url=f"{self.base_url}/{self.community}/discussion/{thread['id']}",
                    category=thread.get('category', ''),
                    replies=thread['comment_count'],
                    views=thread.get('view_count', 0),
                    platform='commonwealth',
                    raw_data=thread
                )
                
            page += 1
            
    def get_comments(self, post_id: str) -> Generator[ForumComment, None, None]:
        """Get comments for a post."""
        url = f"{self.base_url}/api/threads/{post_id}/comments"
        response = self.make_request(url)
        data = response.json()
        
        for comment in data['comments']:
            yield ForumComment(
                id=comment['id'],
                post_id=post_id,
                author=comment['author']['address'],
                content=comment['text'],
                timestamp=datetime.fromisoformat(comment['created_at']),
                parent_id=comment.get('parent_id'),
                platform='commonwealth',
                raw_data=comment
            )

class DiscourseScraper(ForumScraper):
    """Scraper for Discourse forums."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config['scraping']['forum']['discourse']['url']
        self.api_key = config['scraping']['forum']['discourse']['api_key']
        self.api_username = config['scraping']['forum']['discourse']['api_username']
        
    def get_posts(self, category: Optional[str] = None) -> Generator[ForumPost, None, None]:
        """Get forum posts."""
        page = 0
        while True:
            url = f"{self.base_url}/latest.json"
            params = {
                'page': page,
                'api_key': self.api_key,
                'api_username': self.api_username
            }
            if category:
                params['category'] = category
                
            response = self.make_request(url, params=params)
            data = response.json()
            
            if not data['topic_list']['topics']:
                break
                
            for topic in data['topic_list']['topics']:
                yield ForumPost(
                    id=str(topic['id']),
                    title=topic['title'],
                    author=topic['creator']['username'],
                    content=self._get_topic_content(topic['id']),
                    timestamp=datetime.fromisoformat(topic['created_at']),
                    url=urljoin(self.base_url, f"/t/{topic['slug']}/{topic['id']}"),
                    category=topic.get('category_name', ''),
                    replies=topic['reply_count'],
                    views=topic['views'],
                    platform='discourse',
                    raw_data=topic
                )
                
            page += 1
            
    def get_comments(self, post_id: str) -> Generator[ForumComment, None, None]:
        """Get comments for a post."""
        url = f"{self.base_url}/t/{post_id}.json"
        params = {
            'api_key': self.api_key,
            'api_username': self.api_username
        }
        
        response = self.make_request(url, params=params)
        data = response.json()
        
        for post in data['post_stream']['posts'][1:]:  # Skip first post (topic content)
            yield ForumComment(
                id=str(post['id']),
                post_id=post_id,
                author=post['username'],
                content=post['cooked'],  # HTML content
                timestamp=datetime.fromisoformat(post['created_at']),
                parent_id=str(post.get('reply_to_post_number', '')),
                platform='discourse',
                raw_data=post
            )
            
    def _get_topic_content(self, topic_id: str) -> str:
        """Get the content of a topic's first post."""
        url = f"{self.base_url}/t/{topic_id}.json"
        params = {
            'api_key': self.api_key,
            'api_username': self.api_username
        }
        
        response = self.make_request(url, params=params)
        data = response.json()
        
        if data['post_stream']['posts']:
            return data['post_stream']['posts'][0]['cooked']  # HTML content
        return ""

class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        
    def wait(self):
        """Wait if necessary to respect rate limits."""
        now = time.time()
        
        # Remove old requests
        self.requests = [t for t in self.requests if now - t < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            if sleep_time > 0:
                time.sleep(sleep_time)
                
        self.requests.append(now)