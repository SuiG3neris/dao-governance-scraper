"""
Worker threads for handling long-running operations in the GUI.
"""

from typing import Dict, Any, Optional, List
from PyQt6.QtCore import QThread, pyqtSignal

from src.scraper.snapshot_scraper import SnapshotScraper
from src.scraper.chain_scraper import ChainScraper
from src.database.database import DatabaseManager

class ScraperWorker(QThread):
    """Worker thread for running scraper operations."""
    
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    rate_limit = pyqtSignal(dict)  # Emits current rate limit status
    data_ready = pyqtSignal(str, list)  # Emits (data_type, data)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(
        self,
        scraper: SnapshotScraper,
        db: DatabaseManager,
        space_id: str,
        data_types: List[str]
    ):
        super().__init__()
        self.scraper = scraper
        self.db = db
        self.space_id = space_id
        self.data_types = data_types
        self._is_running = True
        
    def run(self):
        """Execute the scraping operation."""
        try:
            self.status.emit(f"Starting scrape for space: {self.space_id}")
            
            if "proposals" in self.data_types:
                # Fetch proposals
                proposals = list(self.scraper.get_proposals(self.space_id))
                self.status.emit(f"Found {len(proposals)} proposals")
                self.progress.emit(33)
                
                # Save to database and emit for display
                for proposal in proposals:
                    if not self._is_running:
                        return
                    self.db.save_proposal(proposal)
                self.data_ready.emit("proposals", proposals)
                
            if not self._is_running:
                return
                
            if "votes" in self.data_types:
                # Fetch votes for each proposal
                total_votes = []
                for i, proposal in enumerate(proposals):
                    if not self._is_running:
                        return
                        
                    votes = list(self.scraper.get_votes(proposal.id))
                    total_votes.extend(votes)
                    
                    # Save to database
                    self.db.save_votes(votes)
                    
                    # Update progress
                    progress = 33 + int((i + 1) / len(proposals) * 33)
                    self.progress.emit(progress)
                    self.status.emit(f"Processed votes for proposal {i+1}/{len(proposals)}")
                    
                self.data_ready.emit("votes", total_votes)
                self.status.emit(f"Found {len(total_votes)} total votes")
                
            self.progress.emit(100)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            
    def stop(self):
        """Stop the worker."""
        self._is_running = False

class ChainScraperWorker(QThread):
    """Worker thread for blockchain data scraping."""
    
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    rate_limit = pyqtSignal(dict)
    data_ready = pyqtSignal(str, list)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(
        self,
        scraper: ChainScraper,
        db: DatabaseManager,
        contract_address: str,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None
    ):
        super().__init__()
        self.scraper = scraper
        self.db = db
        self.contract_address = contract_address
        self.start_block = start_block
        self.end_block = end_block
        self._is_running = True
        
    def run(self):
        """Execute the chain scraping operation."""
        try:
            self.status.emit(f"Starting chain scrape for contract: {self.contract_address}")
            
            # Get token holders
            holders = list(self.scraper.get_token_holders(
                self.contract_address,
                start_block=self.start_block,
                end_block=self.end_block
            ))
            self.status.emit(f"Found {len(holders)} token holders")
            self.progress.emit(33)
            self.data_ready.emit("holders", holders)
            
            if not self._is_running:
                return
                
            # Get token transfers
            transfers = list(self.scraper.get_token_transfers(
                self.contract_address,
                start_block=self.start_block,
                end_block=self.end_block
            ))
            self.status.emit(f"Found {len(transfers)} transfers")
            self.progress.emit(66)
            self.data_ready.emit("transfers", transfers)
            
            if not self._is_running:
                return
                
            # Get governance events
            events = list(self.scraper.get_governance_events(
                self.contract_address,
                start_block=self.start_block,
                end_block=self.end_block
            ))
            self.status.emit(f"Found {len(events)} governance events")
            self.progress.emit(100)
            self.data_ready.emit("events", events)
            
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            
    def stop(self):
        """Stop the worker."""
        self._is_running = False

class DatabaseWorker(QThread):
    """Worker thread for database operations."""
    
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    data_ready = pyqtSignal(str, list)  # Emits (table_name, data)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, db: DatabaseManager, operation: str, **kwargs):
        super().__init__()
        self.db = db
        self.operation = operation
        self.kwargs = kwargs
        self._is_running = True
        
    def run(self):
        """Execute the database operation."""
        try:
            if self.operation == "export":
                table_name = self.kwargs.get("table_name")
                output_path = self.kwargs.get("output_path")
                
                self.status.emit(f"Exporting {table_name} to {output_path}")
                # Implementation depends on your DatabaseManager's export functionality
                
            elif self.operation == "backup":
                backup_path = self.kwargs.get("backup_path")
                self.status.emit(f"Creating database backup at {backup_path}")
                # Implementation depends on your DatabaseManager's backup functionality
                
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            
    def stop(self):
        """Stop the worker."""
        self._is_running = False