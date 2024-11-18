# src/gui/forum_scraper.py

import logging
import requests
from typing import Dict, List, Optional, Generator
from datetime import datetime
from bs4 import BeautifulSoup

class BaseScraper:
    """Base class for forum scrapers."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (DAO Governance Scraper)'
        })

    def _make_request(self, url: str) -> requests.Response:
        """Make HTTP request with error handling."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"Request failed: {e}")
            raise

class CommonwealthScraper(BaseScraper):
    """Scraper for Commonwealth forum."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_url = "https://commonwealth.im"
        
    def get_discussions(self, community: str) -> Generator[Dict, None, None]:
        """
        Get discussions for a community.
        
        Args:
            community: Community identifier
            
        Yields:
            Discussion data dictionaries
        """
        page = 1
        while True:
            url = f"{self.base_url}/api/v0/communities/{community}/discussions"
            params = {
                'page': page,
                'limit': 20,
                'sort': 'newest'
            }
            
            try:
                response = self._make_request(f"{url}?{'&'.join(f'{k}={v}' for k,v in params.items())}")
                data = response.json()
                
                if not data['result']:
                    break
                    
                for discussion in data['result']:
                    yield {
                        'id': discussion['id'],
                        'title': discussion['title'],
                        'author': discussion['author'],
                        'created_at': discussion['created_at'],
                        'updated_at': discussion['updated_at'],
                        'comments_count': discussion['comments_count'],
                        'url': f"{self.base_url}/{community}/discussion/{discussion['id']}"
                    }
                    
                page += 1
                
            except Exception as e:
                logging.error(f"Error fetching discussions: {e}")
                break
                
    def get_comments(self, community: str, discussion_id: str) -> Generator[Dict, None, None]:
        """
        Get comments for a discussion.
        
        Args:
            community: Community identifier
            discussion_id: Discussion identifier
            
        Yields:
            Comment data dictionaries
        """
        url = f"{self.base_url}/api/v0/communities/{community}/discussions/{discussion_id}/comments"
        
        try:
            response = self._make_request(url)
            data = response.json()
            
            for comment in data['result']:
                yield {
                    'id': comment['id'],
                    'text': comment['text'],
                    'author': comment['author'],
                    'created_at': comment['created_at'],
                    'parent_id': comment.get('parent_id'),
                    'discussion_id': discussion_id
                }
                
        except Exception as e:
            logging.error(f"Error fetching comments: {e}")

class DiscourseScraper(BaseScraper):
    """Scraper for Discourse forums."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.api_key = config.get('discourse', {}).get('api_key')
        self.username = config.get('discourse', {}).get('username')
        
    def configure(self, base_url: str, api_key: Optional[str] = None, username: Optional[str] = None):
        """
        Configure the scraper.
        
        Args:
            base_url: Forum base URL
            api_key: Optional API key
            username: Optional username
        """
        self.base_url = base_url.rstrip('/')
        if api_key:
            self.api_key = api_key
        if username:
            self.username = username
            
        # Update session headers if using API
        if self.api_key and self.username:
            self.session.headers.update({
                'Api-Key': self.api_key,
                'Api-Username': self.username
            })
            
    def get_topics(self, category_id: Optional[int] = None) -> Generator[Dict, None, None]:
        """
        Get topics from a category.
        
        Args:
            category_id: Optional category ID to filter by
            
        Yields:
            Topic data dictionaries
        """
        page = 0
        while True:
            url = f"{self.base_url}/latest.json"
            params = {'page': page}
            
            if category_id:
                params['category'] = category_id
                
            try:
                response = self._make_request(f"{url}?{'&'.join(f'{k}={v}' for k,v in params.items())}")
                data = response.json()
                
                if not data['topic_list']['topics']:
                    break
                    
                for topic in data['topic_list']['topics']:
                    yield {
                        'id': topic['id'],
                        'title': topic['title'],
                        'created_at': topic['created_at'],
                        'views': topic['views'],
                        'posts_count': topic['posts_count'],
                        'author': topic.get('posters', [{}])[0].get('user_id'),
                        'url': f"{self.base_url}/t/{topic['id']}"
                    }
                    
                page += 1
                
            except Exception as e:
                logging.error(f"Error fetching topics: {e}")
                break
                
    def get_posts(self, topic_id: int) -> Generator[Dict, None, None]:
        """
        Get posts from a topic.
        
        Args:
            topic_id: Topic identifier
            
        Yields:
            Post data dictionaries
        """
        try:
            url = f"{self.base_url}/t/{topic_id}.json"
            response = self._make_request(url)
            data = response.json()
            
            for post in data['post_stream']['posts']:
                yield {
                    'id': post['id'],
                    'topic_id': topic_id,
                    'author': post['username'],
                    'content': post['cooked'],  # HTML content
                    'created_at': post['created_at'],
                    'updated_at': post.get('updated_at'),
                    'reply_to_post_number': post.get('reply_to_post_number'),
                    'quote_count': post.get('quote_count', 0),
                    'incoming_link_count': post.get('incoming_link_count', 0)
                }
                
        except Exception as e:
            logging.error(f"Error fetching posts: {e}")
            
    def get_categories(self) -> List[Dict]:
        """
        Get list of categories.
        
        Returns:
            List of category data dictionaries
        """
        try:
            url = f"{self.base_url}/categories.json"
            response = self._make_request(url)
            data = response.json()
            
            categories = []
            for category in data['category_list']['categories']:
                categories.append({
                    'id': category['id'],
                    'name': category['name'],
                    'slug': category['slug'],
                    'topics_count': category['topics_count'],
                    'description': category.get('description'),
                    'parent_category_id': category.get('parent_category_id')
                })
            return categories
            
        except Exception as e:
            logging.error(f"Error fetching categories: {e}")
            return []