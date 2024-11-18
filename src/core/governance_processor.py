"""
Specialized processor for DAO governance data.
Handles proposal and voting data processing, metrics calculation,
and format standardization.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import logging
from dataclasses import dataclass
import pandas as pd
import numpy as np
from enum import Enum

from .data_processor import DataProcessor, ProcessingResult, ValidationError, ProcessingError

class ProposalState(Enum):
    """Standard states for governance proposals."""
    ACTIVE = "active"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    CANCELED = "canceled"
    QUEUED = "queued"
    EXECUTED = "executed"

@dataclass
class GovernanceMetrics:
    """Container for governance metrics."""
    total_proposals: int = 0
    total_votes: int = 0
    participation_rate: float = 0.0
    avg_voting_power: float = 0.0
    proposal_success_rate: float = 0.0
    unique_voters: int = 0
    avg_duration: float = 0.0
    votes_by_state: Dict[str, int] = None
    votes_by_month: Dict[str, int] = None
    top_voters: List[Tuple[str, int]] = None

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            'total_proposals': self.total_proposals,
            'total_votes': self.total_votes,
            'participation_rate': self.participation_rate,
            'avg_voting_power': self.avg_voting_power,
            'proposal_success_rate': self.proposal_success_rate,
            'unique_voters': self.unique_voters,
            'avg_duration': self.avg_duration,
            'votes_by_state': self.votes_by_state,
            'votes_by_month': self.votes_by_month,
            'top_voters': self.top_voters
        }

class GovernanceProcessor(DataProcessor):
    """Process and analyze DAO governance data."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize governance processor with configuration."""
        super().__init__(config)
        
        # Set governance-specific validation rules
        self.config['validation'].update({
            'required_fields': {
                'proposals': ['id', 'title', 'state', 'start', 'end'],
                'votes': ['id', 'proposal_id', 'voter', 'choice', 'voting_power']
            },
            'field_types': {
                'voting_power': float,
                'choice': int,
                'start': 'datetime64[ns]',
                'end': 'datetime64[ns]'
            }
        })
        
    def _process_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Process governance data.
        
        Args:
            data: Dictionary containing 'proposals' and 'votes' DataFrames
            
        Returns:
            Dictionary containing processed data and metrics
        """
        try:
            # Standardize data formats
            proposals_df = self._standardize_proposals(data['proposals'])
            votes_df = self._standardize_votes(data['votes'])
            
            # Calculate metrics
            metrics = self._calculate_metrics(proposals_df, votes_df)
            
            # Prepare processed data
            processed_data = {
                'proposals': proposals_df,
                'votes': votes_df,
                'metrics': metrics.to_dict(),
                'summary': self._generate_summary(metrics)
            }
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing governance data: {e}")
            raise ProcessingError(f"Failed to process governance data: {e}")
    
    def _standardize_proposals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize proposal data format.
        
        Args:
            df: Proposals DataFrame
            
        Returns:
            Standardized DataFrame
        """
        df = df.copy()
        
        try:
            # Convert timestamps to datetime
            for col in ['start', 'end']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], utc=True)
            
            # Standardize state values
            df['state'] = df['state'].str.lower()
            df['state'] = df['state'].map(lambda x: next(
                (s.value for s in ProposalState if s.value in x),
                'unknown'
            ))
            
            # Calculate duration
            if 'start' in df.columns and 'end' in df.columns:
                df['duration'] = (df['end'] - df['start']).dt.total_seconds() / 3600  # hours
            
            # Clean text fields
            for col in ['title', 'description', 'body']:
                if col in df.columns:
                    df[col] = df[col].fillna('').str.strip()
            
            return df
            
        except Exception as e:
            raise ProcessingError(f"Error standardizing proposals: {e}")
    
    def _standardize_votes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize voting data format.
        
        Args:
            df: Votes DataFrame
            
        Returns:
            Standardized DataFrame
        """
        df = df.copy()
        
        try:
            # Convert voting power to float
            df['voting_power'] = pd.to_numeric(df['voting_power'], errors='coerce')
            
            # Convert choice to int
            df['choice'] = pd.to_numeric(df['choice'], errors='coerce').fillna(0).astype(int)
            
            # Convert timestamp if present
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
            # Clean voter addresses
            df['voter'] = df['voter'].str.strip().str.lower()
            
            # Add month column if timestamp exists
            if 'timestamp' in df.columns:
                df['month'] = df['timestamp'].dt.strftime('%Y-%m')
            
            return df
            
        except Exception as e:
            raise ProcessingError(f"Error standardizing votes: {e}")
    
    def _calculate_metrics(
        self,
        proposals_df: pd.DataFrame,
        votes_df: pd.DataFrame
    ) -> GovernanceMetrics:
        """
        Calculate governance metrics.
        
        Args:
            proposals_df: Proposals DataFrame
            votes_df: Votes DataFrame
            
        Returns:
            GovernanceMetrics object
        """
        try:
            metrics = GovernanceMetrics()
            
            # Basic counts
            metrics.total_proposals = len(proposals_df)
            metrics.total_votes = len(votes_df)
            metrics.unique_voters = votes_df['voter'].nunique()
            
            # Success rate
            if len(proposals_df) > 0:
                succeeded = proposals_df['state'].isin(['succeeded', 'executed']).sum()
                metrics.proposal_success_rate = succeeded / len(proposals_df) * 100
            
            # Voting power metrics
            if len(votes_df) > 0:
                metrics.avg_voting_power = votes_df['voting_power'].mean()
            
            # Participation rate (votes per proposal)
            if metrics.total_proposals > 0:
                metrics.participation_rate = metrics.total_votes / metrics.total_proposals
            
            # Average proposal duration
            if 'duration' in proposals_df.columns:
                metrics.avg_duration = proposals_df['duration'].mean()
            
            # Votes by state
            metrics.votes_by_state = votes_df.groupby('proposal_id')\
                .size()\
                .reset_index(name='vote_count')\
                .merge(proposals_df[['id', 'state']], left_on='proposal_id', right_on='id')\
                .groupby('state')['vote_count']\
                .sum()\
                .to_dict()
            
            # Votes by month
            if 'month' in votes_df.columns:
                metrics.votes_by_month = votes_df.groupby('month')\
                    .size()\
                    .sort_index()\
                    .to_dict()
            
            # Top voters
            metrics.top_voters = votes_df.groupby('voter')\
                .size()\
                .sort_values(ascending=False)\
                .head(10)\
                .items()
            
            return metrics
            
        except Exception as e:
            raise ProcessingError(f"Error calculating metrics: {e}")
    
    def _generate_summary(self, metrics: GovernanceMetrics) -> str:
        """
        Generate human-readable summary of metrics.
        
        Args:
            metrics: GovernanceMetrics object
            
        Returns:
            Formatted summary string
        """
        try:
            summary = [
                f"Governance Activity Summary",
                f"------------------------",
                f"Total Proposals: {metrics.total_proposals}",
                f"Total Votes Cast: {metrics.total_votes}",
                f"Unique Voters: {metrics.unique_voters}",
                f"Average Votes per Proposal: {metrics.participation_rate:.2f}",
                f"Proposal Success Rate: {metrics.proposal_success_rate:.1f}%",
                f"Average Voting Power: {metrics.avg_voting_power:.2f}",
                f"Average Proposal Duration: {metrics.avg_duration:.1f} hours",
                "",
                f"Top 5 Most Active Voters:",
            ]
            
            # Add top voters
            for voter, count in list(metrics.top_voters)[:5]:
                summary.append(f"- {voter[:10]}... : {count} votes")
            
            return "\n".join(summary)
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return "Error generating summary"
    
    def process_snapshot(self, data: Dict[str, Any]) -> ProcessingResult:
        """
        Process Snapshot.org format data.
        
        Args:
            data: Dictionary containing Snapshot data
            
        Returns:
            ProcessingResult object
        """
        try:
            # Convert Snapshot format to standard format
            proposals_df = pd.DataFrame(data.get('proposals', []))
            votes_df = pd.DataFrame(data.get('votes', []))
            
            # Map fields to standard format
            if not proposals_df.empty:
                proposals_df = proposals_df.rename(columns={
                    'title': 'title',
                    'body': 'description',
                    'choices': 'options',
                    'start': 'start',
                    'end': 'end',
                    'state': 'state',
                    'author': 'creator'
                })
            
            if not votes_df.empty:
                votes_df = votes_df.rename(columns={
                    'voter': 'voter',
                    'choice': 'choice',
                    'vp': 'voting_power',
                    'created': 'timestamp'
                })
            
            # Process converted data
            return self.process({
                'proposals': proposals_df,
                'votes': votes_df
            })
            
        except Exception as e:
            self.logger.error(f"Error processing Snapshot data: {e}")
            raise ProcessingError(f"Failed to process Snapshot data: {e}")
    
    def validate_data(self, data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate governance data structure.
        
        Args:
            data: Dictionary containing 'proposals' and 'votes' DataFrames
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError("Input must be a dictionary containing 'proposals' and 'votes'")
        
        required_keys = {'proposals', 'votes'}
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            raise ValidationError(f"Missing required keys: {missing_keys}")
        
        # Validate each DataFrame
        for key, df in data.items():
            if not isinstance(df, pd.DataFrame):
                raise ValidationError(f"{key} must be a DataFrame")
            
            # Check required fields
            required_fields = self.config['validation']['required_fields'].get(key, [])
            missing_fields = set(required_fields) - set(df.columns)
            if missing_fields:
                raise ValidationError(f"Missing required fields in {key}: {missing_fields}")