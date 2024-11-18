"""
Background thread implementation for scraping operations.
"""

from typing import Dict, List, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal
import time
import logging
from queue import Queue

from src.scraper.snapshot_scraper import SnapshotScraper
from src.scraper.chain_scraper import ChainScraper
from src.database.database import DatabaseManager
from .data_manager import DataManager

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

class ScraperThread(QThread):
    """Worker thread for running scraping operations."""
    
    # Progress signals
    progress = pyqtSignal(str, int)  # (source, progress percentage)
    status = pyqtSignal(str)  # Status message
    error = pyqtSignal(str)  # Error message
    rate_limit = pyqtSignal(str, dict)  # (source, rate limit info)
    data_ready = pyqtSignal(str, list)  # (data_type, data items)
    finished = pyqtSignal()
    
    def __init__(
        self,
        data_manager: DataManager,
        db_manager: DatabaseManager,
        sources: List[str],
        config: Dict[str, Any]
    ):
        super().__init__()
        self.data_manager = data_manager
        self.db_manager = db_manager
        self.sources = sources
        self.config = config
        self._is_running = True
        
        # Initialize rate limiters
        self.rate_limiters = {
            'snapshot': RateLimiter(
                max_requests=config['scraping']['rate_limit']['requests_per_minute'],
                time_window=60
            ),
            'etherscan': RateLimiter(
                max_requests=config['blockchain']['etherscan']['rate_limit']['calls_per_second'],
                time_window=1
            )
        }
        
        # Create work queue
        self.queue = Queue()
        
    def stop(self):
        """Stop the scraping operation."""
        self._is_running = False
        
    def run(self):
        """Execute the scraping operation."""
        try:
            for source in self.sources:
                if source == "snapshot":
                    self.scrape_snapshot()
                elif source == "etherscan":
                    self.scrape_etherscan()
                    
                if not self._is_running:
                    break
                    
            if self._is_running:
                self.finished.emit()
                
        except Exception as e:
            logging.error(f"Scraping error: {e}", exc_info=True)
            self.error.emit(str(e))
            
    def scrape_snapshot(self):
        """Scrape data from Snapshot.org."""
        try:
            scraper = SnapshotScraper(self.config)
            self.status.emit("Initializing Snapshot.org scraper")
            
            # Get spaces
            self.status.emit("Fetching Snapshot spaces")
            spaces = []
            for space in scraper.get_spaces():
                if not self._is_running:
                    return
                    
                spaces.append(space)
                self.rate_limiters['snapshot'].wait()
                
            self.data_manager.add_data('spaces', spaces)
            self.data_ready.emit('spaces', spaces)
            self.progress.emit('snapshot', 25)
            
            # Get proposals for each space
            total_proposals = []
            for i, space in enumerate(spaces):
                if not self._is_running:
                    return
                    
                self.status.emit(f"Fetching proposals for space: {space.name}")
                proposals = list(scraper.get_proposals(space.id))
                total_proposals.extend(proposals)
                
                progress = 25 + int((i + 1) / len(spaces) * 25)
                self.progress.emit('snapshot', progress)
                self.rate_limiters['snapshot'].wait()
                
            self.data_manager.add_data('proposals', total_proposals)
            self.data_ready.emit('proposals', total_proposals)
            self.progress.emit('snapshot', 50)
            
            # Get votes for each proposal
            total_votes = []
            for i, proposal in enumerate(total_proposals):
                if not self._is_running:
                    return
                    
                self.status.emit(f"Fetching votes for proposal: {proposal.title[:30]}...")
                votes = list(scraper.get_votes(proposal.id))
                total_votes.extend(votes)
                
                progress = 50 + int((i + 1) / len(total_proposals) * 50)
                self.progress.emit('snapshot', progress)
                self.rate_limiters['snapshot'].wait()
                
            self.data_manager.add_data('votes', total_votes)
            self.data_ready.emit('votes', total_votes)
            self.progress.emit('snapshot', 100)
            
        except Exception as e:
            self.error.emit(f"Snapshot scraping error: {str(e)}")
            raise
            
    def scrape_etherscan(self):
        """Scrape data from Etherscan."""
        try:
            scraper = ChainScraper(self.config)
            self.status.emit("Initializing Etherscan scraper")
            
            # Get token holders
            self.status.emit("Fetching token holders")
            holders = list(scraper.get_token_holders(
                self.config['blockchain']['token_address']
            ))
            self.data_manager.add_data('holders', holders)
            self.data_ready.emit('holders', holders)
            self.progress.emit('etherscan', 50)
            
            # Get token transfers
            self.status.emit("Fetching token transfers")
            transfers = list(scraper.get_token_transfers(
                self.config['blockchain']['token_address']
            ))
            self.data_manager.add_data('transfers', transfers)
            self.data_ready.emit('transfers', transfers)
            self.progress.emit('etherscan', 100)
            
        except Exception as e:
            self.error.emit(f"Etherscan scraping error: {str(e)}")
            raise

class DataProcessThread(QThread):
    """Worker thread for data processing operations."""
    
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, data_manager: DataManager, operation: str, **kwargs):
        super().__init__()
        self.data_manager = data_manager
        self.operation = operation
        self.kwargs = kwargs
        self._is_running = True
        
    def stop(self):
        """Stop the processing operation."""
        self._is_running = False
        
    def run(self):
        """Execute the processing operation."""
        try:
            if self.operation == "validate":
                self.validate_data()
            elif self.operation == "export":
                self.export_data()
                
            if self._is_running:
                self.finished.emit()
                
        except Exception as e:
            logging.error(f"Processing error: {e}", exc_info=True)
            self.error.emit(str(e))
            
    def validate_data(self):
        """Validate the collected data."""
        data_types = self.kwargs.get('data_types', [])
        total = len(data_types)
        
        for i, data_type in enumerate(data_types):
            if not self._is_running:
                return
                
            self.status.emit(f"Validating {data_type} data...")
            errors = self.data_manager.validate_data(data_type)
            
            if errors:
                self.error.emit(f"Validation errors in {data_type}: {', '.join(errors)}")
                
            progress = int((i + 1) / total * 100)
            self.progress.emit(progress)
            
    def export_data(self):
        """Export data in Claude-friendly format."""
        try:
            data_types = self.kwargs.get('data_types', [])
            format = self.kwargs.get('format', 'json')
            filepath = self.kwargs.get('filepath')
            
            self.status.emit("Preparing data for export...")
            self.progress.emit(25)
            
            if not self._is_running:
                return
                
            self.status.emit("Validating data...")
            self.progress.emit(50)
            
            for data_type in data_types:
                errors = self.data_manager.validate_data(data_type)
                if errors:
                    raise ValueError(f"Validation errors in {data_type}: {', '.join(errors)}")
                    
            if not self._is_running:
                return
                
            self.status.emit("Exporting data...")
            self.progress.emit(75)
            
            output_path = self.data_manager.export_for_claude(
                data_types,
                format=format,
                filepath=filepath
            )
            
            self.status.emit(f"Data exported to: {output_path}")
            self.progress.emit(100)
            
        except Exception as e:
            self.error.emit(f"Export error: {str(e)}")
            raise

        def scrape_forum(self, platform: str, config: Dict[str, Any]):
        """Scrape data from a forum platform."""
        try:
            self.status.emit(f"Initializing {platform} scraper")
            
            # Initialize appropriate scraper
            if platform == "commonwealth":
                scraper = CommonwealthScraper(config)
            elif platform == "discourse":
                scraper = DiscourseScraper(config)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
                
            # Get posts
            self.status.emit("Fetching forum posts")
            posts = []
            for post in scraper.get_posts():
                if not self._is_running:
                    return
                    
                posts.append(post)
                self.rate_limit.emit(platform, {'current': len(posts)})
                self.progress.emit(platform, int(len(posts) / 100 * 50))  # Assume max 100 posts
                
            self.data_manager.add_data('forum_posts', posts)
            self.data_ready.emit('forum_posts', posts)
            
            # Get comments for each post
            total_comments = []
            for i, post in enumerate(posts):
                if not self._is_running:
                    return
                    
                self.status.emit(f"Fetching comments for post: {post.title[:30]}...")
                comments = list(scraper.get_comments(post.id))
                total_comments.extend(comments)
                
                progress = 50 + int((i + 1) / len(posts) * 50)
                self.progress.emit(platform, progress)
                
            self.data_manager.add_data('forum_comments', total_comments)
            self.data_ready.emit('forum_comments', total_comments)
            
            self.progress.emit(platform, 100)
            
        except Exception as e:
            self.error.emit(f"Forum scraping error: {str(e)}")
            raise