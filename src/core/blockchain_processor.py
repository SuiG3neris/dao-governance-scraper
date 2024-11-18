"""
Blockchain data processor for DAO analyzer.
Handles transaction data, smart contract events, wallet activities,
and standardizes chain data across different formats.
"""

from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
from web3 import Web3
from eth_utils import to_checksum_address

from .data_processor import DataProcessor, ProcessingResult, ValidationError, ProcessingError

class ChainType(Enum):
    """Supported blockchain types."""
    ETHEREUM = auto()
    POLYGON = auto()
    ARBITRUM = auto()
    OPTIMISM = auto()
    BSC = auto()

@dataclass
class BlockchainMetrics:
    """Container for blockchain metrics and analytics."""
    total_transactions: int = 0
    unique_addresses: int = 0
    total_volume: float = 0.0
    avg_gas_price: float = 0.0
    contract_interactions: Dict[str, int] = None
    daily_activity: Dict[str, int] = None
    top_interactors: List[tuple] = None
    event_counts: Dict[str, int] = None
    token_transfers: Dict[str, float] = None
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary format."""
        return {
            'total_transactions': self.total_transactions,
            'unique_addresses': self.unique_addresses,
            'total_volume': self.total_volume,
            'avg_gas_price': self.avg_gas_price,
            'contract_interactions': self.contract_interactions,
            'daily_activity': self.daily_activity,
            'top_interactors': self.top_interactors,
            'event_counts': self.event_counts,
            'token_transfers': self.token_transfers
        }

class BlockchainProcessor(DataProcessor):
    """Process and analyze blockchain data."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize blockchain processor with configuration."""
        super().__init__(config)
        
        # Set blockchain-specific validation rules
        self.config['validation'].update({
            'required_fields': {
                'transactions': ['hash', 'from', 'to', 'value', 'blockNumber'],
                'events': ['address', 'event', 'blockNumber', 'transactionHash'],
                'tokens': ['contract', 'from', 'to', 'value', 'tokenType']
            },
            'field_types': {
                'value': float,
                'blockNumber': int,
                'gasPrice': float,
                'nonce': int
            }
        })
        
        self.web3 = Web3()
    
    def _process_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Process blockchain data.
        
        Args:
            data: Dictionary containing DataFrames for transactions, events, etc.
            
        Returns:
            Dictionary containing processed data and metrics
        """
        try:
            # Standardize data formats
            transactions_df = self._standardize_transactions(data.get('transactions', pd.DataFrame()))
            events_df = self._standardize_events(data.get('events', pd.DataFrame()))
            tokens_df = self._standardize_tokens(data.get('tokens', pd.DataFrame()))
            
            # Calculate metrics
            metrics = self._calculate_metrics(transactions_df, events_df, tokens_df)
            
            # Prepare processed data
            processed_data = {
                'transactions': transactions_df,
                'events': events_df,
                'tokens': tokens_df,
                'metrics': metrics.to_dict(),
                'summary': self._generate_summary(metrics),
                'network_stats': self._get_network_stats(transactions_df)
            }
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing blockchain data: {e}")
            raise ProcessingError(f"Failed to process blockchain data: {e}")
    
    def _standardize_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize transaction data format.
        
        Args:
            df: Transactions DataFrame
            
        Returns:
            Standardized DataFrame
        """
        if df.empty:
            return df
            
        df = df.copy()
        
        try:
            # Convert addresses to checksum format
            for col in ['from', 'to']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: 
                        to_checksum_address(x) if pd.notnull(x) else None
                    )
            
            # Convert Wei to Ether for value field
            if 'value' in df.columns:
                df['value'] = df['value'].apply(
                    lambda x: float(Web3.from_wei(int(x), 'ether')) if pd.notnull(x) else 0.0
                )
            
            # Add timestamp if blockNumber exists
            if 'blockNumber' in df.columns and 'timestamp' not in df.columns:
                # This would require block timestamp lookup - simplified for example
                df['timestamp'] = pd.Timestamp.now(tz=timezone.utc)
            
            # Calculate gas cost if needed fields exist
            if all(field in df.columns for field in ['gasPrice', 'gasUsed']):
                df['gasCost'] = df['gasPrice'] * df['gasUsed']
                df['gasCost'] = df['gasCost'].apply(
                    lambda x: float(Web3.from_wei(int(x), 'ether')) if pd.notnull(x) else 0.0
                )
            
            return df
            
        except Exception as e:
            raise ProcessingError(f"Error standardizing transactions: {e}")
    
    def _standardize_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize event data format.
        
        Args:
            df: Events DataFrame
            
        Returns:
            Standardized DataFrame
        """
        if df.empty:
            return df
            
        df = df.copy()
        
        try:
            # Convert addresses to checksum format
            df['address'] = df['address'].apply(to_checksum_address)
            
            # Parse event parameters if stored as string
            if 'args' in df.columns and df['args'].dtype == 'object':
                df['args'] = df['args'].apply(self._parse_event_args)
            
            # Standardize event names
            df['event'] = df['event'].str.upper()
            
            # Add timestamp if not present
            if 'timestamp' not in df.columns:
                df['timestamp'] = pd.Timestamp.now(tz=timezone.utc)
            
            return df
            
        except Exception as e:
            raise ProcessingError(f"Error standardizing events: {e}")
    
    def _standardize_tokens(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize token transfer data format.
        
        Args:
            df: Token transfers DataFrame
            
        Returns:
            Standardized DataFrame
        """
        if df.empty:
            return df
            
        df = df.copy()
        
        try:
            # Convert addresses to checksum format
            for col in ['contract', 'from', 'to']:
                if col in df.columns:
                    df[col] = df[col].apply(to_checksum_address)
            
            # Standardize token values based on decimals
            if 'value' in df.columns and 'decimals' in df.columns:
                df['value'] = df.apply(
                    lambda row: float(row['value']) / (10 ** row['decimals'])
                    if pd.notnull(row['decimals']) else row['value'],
                    axis=1
                )
            
            # Standardize token types
            if 'tokenType' in df.columns:
                df['tokenType'] = df['tokenType'].str.upper()
            
            return df
            
        except Exception as e:
            raise ProcessingError(f"Error standardizing tokens: {e}")
    
    def _parse_event_args(self, args: str) -> Dict:
        """Parse event arguments from string format."""
        if pd.isna(args):
            return {}
        try:
            if isinstance(args, str):
                return eval(args)  # Note: Use proper JSON parsing in production
            return args
        except Exception:
            return {}
    
    def _calculate_metrics(
        self,
        transactions_df: pd.DataFrame,
        events_df: pd.DataFrame,
        tokens_df: pd.DataFrame
    ) -> BlockchainMetrics:
        """
        Calculate blockchain metrics.
        
        Args:
            transactions_df: Transactions DataFrame
            events_df: Events DataFrame
            tokens_df: Token transfers DataFrame
            
        Returns:
            BlockchainMetrics object
        """
        metrics = BlockchainMetrics()
        
        try:
            # Transaction metrics
            if not transactions_df.empty:
                metrics.total_transactions = len(transactions_df)
                metrics.unique_addresses = pd.concat([
                    transactions_df['from'], transactions_df['to']
                ]).nunique()
                metrics.total_volume = transactions_df['value'].sum()
                metrics.avg_gas_price = transactions_df.get('gasPrice', pd.Series()).mean()
                
                # Daily activity
                if 'timestamp' in transactions_df.columns:
                    metrics.daily_activity = transactions_df.groupby(
                        transactions_df['timestamp'].dt.date
                    ).size().to_dict()
                
                # Contract interactions
                contract_mask = transactions_df['to'].apply(
                    lambda x: len(x) == 42 if pd.notnull(x) else False
                )
                metrics.contract_interactions = transactions_df[contract_mask].groupby('to').size().to_dict()
            
            # Event metrics
            if not events_df.empty:
                metrics.event_counts = events_df.groupby('event').size().to_dict()
            
            # Token metrics
            if not tokens_df.empty:
                metrics.token_transfers = tokens_df.groupby('contract')['value'].sum().to_dict()
                
                # Top token interactors
                metrics.top_interactors = tokens_df.groupby('from').size().nlargest(10).items()
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {e}")
            return metrics
    
    def _get_network_stats(self, transactions_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate network statistics from transaction data."""
        stats = {
            'avg_block_time': None,
            'avg_transaction_fee': None,
            'active_addresses': 0,
            'contract_creation_count': 0
        }
        
        if transactions_df.empty:
            return stats
            
        try:
            # Calculate average block time if timestamps available
            if 'timestamp' in transactions_df.columns:
                block_times = transactions_df.groupby('blockNumber')['timestamp'].first()
                stats['avg_block_time'] = block_times.diff().mean().total_seconds()
            
            # Calculate average transaction fee
            if 'gasCost' in transactions_df.columns:
                stats['avg_transaction_fee'] = transactions_df['gasCost'].mean()
            
            # Count active addresses
            stats['active_addresses'] = pd.concat([
                transactions_df['from'], transactions_df['to']
            ]).nunique()
            
            # Count contract creations (transactions with empty 'to' field)
            stats['contract_creation_count'] = transactions_df['to'].isna().sum()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating network stats: {e}")
            return stats
    
    def _generate_summary(self, metrics: BlockchainMetrics) -> str:
        """Generate human-readable summary of blockchain metrics."""
        try:
            summary = [
                f"Blockchain Activity Summary",
                f"--------------------------",
                f"Total Transactions: {metrics.total_transactions:,}",
                f"Unique Addresses: {metrics.unique_addresses:,}",
                f"Total Volume: {metrics.total_volume:.2f} ETH",
                f"Average Gas Price: {metrics.avg_gas_price:.2f} Gwei",
                "",
                f"Top 5 Contract Interactions:",
            ]
            
            # Add top contracts
            if metrics.contract_interactions:
                top_contracts = sorted(
                    metrics.contract_interactions.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                for contract, count in top_contracts:
                    summary.append(f"- {contract[:10]}... : {count:,} transactions")
            
            # Add event summary
            if metrics.event_counts:
                summary.extend([
                    "",
                    "Event Distribution:",
                    *[f"- {event}: {count:,}" 
                      for event, count in sorted(
                          metrics.event_counts.items(),
                          key=lambda x: x[1],
                          reverse=True
                      )[:5]
                    ]
                ])
            
            return "\n".join(summary)
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return "Error generating blockchain summary"
    
    def process_web3_format(self, transactions: List[Dict]) -> ProcessingResult:
        """
        Process Web3.py format transaction data.
        
        Args:
            transactions: List of Web3.py transaction dictionaries
            
        Returns:
            ProcessingResult with standardized data
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(transactions)
            
            # Rename fields to match standard format
            df = df.rename(columns={
                'blockHash': 'blockHash',
                'blockNumber': 'blockNumber',
                'from': 'from',
                'gas': 'gasLimit',
                'gasPrice': 'gasPrice',
                'hash': 'hash',
                'input': 'input',
                'nonce': 'nonce',
                'to': 'to',
                'transactionIndex': 'transactionIndex',
                'value': 'value',
                'type': 'type'
            })
            
            # Process using standard pipeline
            return self.process({'transactions': df})
            
        except Exception as e:
            self.logger.error(f"Error processing Web3 format: {e}")
            raise ProcessingError(f"Failed to process Web3 format: {e}")