"""
Database utility functions for backup, maintenance, and monitoring.
"""

import os
import time
import shutil
import sqlite3
import logging
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine

class DatabaseUtils:
    """Utility functions for database maintenance and monitoring."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize database utilities with configuration."""
        self.config = config['database']
        self.db_path = Path(self.config['path'])
        self.backup_path = Path(self.config['backup']['path'])
        
        # Ensure backup directory exists
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, compress: bool = True) -> Path:
        """
        Create a backup of the database.
        
        Args:
            compress: Whether to compress the backup using gzip
            
        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.db"
        backup_file = self.backup_path / backup_name
        
        logging.info(f"Creating backup: {backup_file}")
        
        try:
            # Create backup
            shutil.copy2(self.db_path, backup_file)
            
            if compress:
                # Compress backup
                with open(backup_file, 'rb') as f_in:
                    compressed_file = backup_file.with_suffix('.db.gz')
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                # Remove uncompressed backup
                backup_file.unlink()
                backup_file = compressed_file
            
            logging.info(f"Backup created successfully: {backup_file}")
            return backup_file
            
        except Exception as e:
            logging.error(f"Backup creation failed: {e}")
            raise
    
    def restore_backup(self, backup_file: Path) -> None:
        """
        Restore database from backup.
        
        Args:
            backup_file: Path to backup file
        """
        logging.info(f"Restoring from backup: {backup_file}")
        
        try:
            if backup_file.suffix == '.gz':
                # Decompress backup
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(self.db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Copy backup directly
                shutil.copy2(backup_file, self.db_path)
                
            logging.info("Database restored successfully")
            
        except Exception as e:
            logging.error(f"Restore failed: {e}")
            raise
    
    def cleanup_old_backups(self, keep_days: int = 7) -> None:
        """
        Remove backups older than specified days.
        
        Args:
            keep_days: Number of days to keep backups
        """
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        for backup_file in self.backup_path.glob("backup_*.db*"):
            # Extract date from filename
            try:
                date_str = backup_file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    backup_file.unlink()
                    logging.info(f"Removed old backup: {backup_file}")
            except (IndexError, ValueError):
                logging.warning(f"Could not parse date from backup filename: {backup_file}")
    
    def export_to_csv(self, table_name: str, output_dir: Path) -> Path:
        """
        Export table data to CSV file.
        
        Args:
            table_name: Name of table to export
            output_dir: Directory to save CSV
            
        Returns:
            Path to CSV file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{table_name}_{datetime.now():%Y%m%d}.csv"
        
        engine = create_engine(f"sqlite:///{self.db_path}")
        query = f"SELECT * FROM {table_name}"
        
        try:
            df = pd.read_sql_query(query, engine)
            df.to_csv(output_file, index=False)
            logging.info(f"Exported {table_name} to {output_file}")
            return output_file
        except Exception as e:
            logging.error(f"Export failed: {e}")
            raise
        finally:
            engine.dispose()
    
    def check_database_health(self) -> Dict[str, Any]:
        """
        Perform basic database health checks.
        
        Returns:
            Dictionary containing health check results
        """
        results = {
            'integrity_check': False,
            'size_mb': 0,
            'table_sizes': {},
            'indexes': [],
            'fragmentation': 0
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check integrity
            integrity = cursor.execute("PRAGMA integrity_check").fetchone()[0]
            results['integrity_check'] = integrity == 'ok'
            
            # Get database size
            results['size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
            
            # Get table sizes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for (table_name,) in cursor.fetchall():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                results['table_sizes'][table_name] = count
            
            # Get index information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            results['indexes'] = [row[0] for row in cursor.fetchall()]
            
            # Check fragmentation (free pages)
            cursor.execute("PRAGMA freelist_count")
            freelist_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            if page_count > 0:
                results['fragmentation'] = (freelist_count / page_count) * 100
            
            return results
            
        except Exception as e:
            logging.error(f"Health check failed: {e}")
            raise
        finally:
            conn.close()
    
    def optimize_database(self) -> None:
        """Optimize database by cleaning up fragmentation and analyzing statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Vacuum to clean up fragmentation
            cursor.execute("VACUUM")
            
            # Analyze to update statistics
            cursor.execute("ANALYZE")
            
            logging.info("Database optimization completed")
            
        except Exception as e:
            logging.error(f"Optimization failed: {e}")
            raise
        finally:
            conn.close()
    
    def get_query_performance_stats(self, query: str) -> Dict[str, Any]:
        """
        Get execution statistics for a query.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Dictionary containing query performance statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enable stats
            cursor.execute("PRAGMA stats = ON")
            
            # Execute EXPLAIN QUERY PLAN
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            query_plan = cursor.fetchall()
            
            # Execute query and measure time
            start_time = time.time()
            cursor.execute(query)
            results = cursor.fetchall()
            execution_time = time.time() - start_time
            
            stats = {
                'query_plan': query_plan,
                'execution_time': execution_time,
                'rows_returned': len(results),
                'uses_index': any('USING INDEX' in str(p) for p in query_plan)
            }
            
            return stats
            
        except Exception as e:
            logging.error(f"Performance analysis failed: {e}")
            raise
        finally:
            conn.close()