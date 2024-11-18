"""
Data processing pipeline for Claude-optimized exports.
Handles data cleaning, structuring, and analysis preparation.
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from src.database.models import Space, Proposal, Vote
from src.utils.helpers import clean_text


class ClaudeProcessor:
    """Processes DAO governance data for Claude analysis."""
    
    def __init__(self, db_session: Session):
        """Initialize processor with database session."""
        self.db = db_session
        self.date_format = "%Y-%m-%d %H:%M:%S"
        
    def clean_proposal_data(self, proposals: List[Proposal]) -> pd.DataFrame:
        """
        Clean and standardize proposal data.
        
        Args:
            proposals: List of Proposal objects
            
        Returns:
            DataFrame with cleaned proposal data
        """
        cleaned_data = []
        
        for proposal in proposals:
            cleaned = {
                'id': proposal.id,
                'title': clean_text(proposal.title),
                'body': clean_text(proposal.body),
                'start_date': proposal.start.strftime(self.date_format),
                'end_date': proposal.end.strftime(self.date_format),
                'state': proposal.state.lower(),
                'choices': proposal.choices,
                'votes_count': proposal.votes,
                'scores_total': float(proposal.scores_total),
                'author': proposal.author.lower(),
                'space_id': proposal.space_id
            }
            cleaned_data.append(cleaned)
            
        df = pd.DataFrame(cleaned_data)
        
        # Handle missing values
        df['body'] = df['body'].fillna('')
        df['scores_total'] = df['scores_total'].fillna(0.0)
        
        return df
    
    def clean_vote_data(self, votes: List[Vote]) -> pd.DataFrame:
        """
        Clean and standardize vote data.
        
        Args:
            votes: List of Vote objects
            
        Returns:
            DataFrame with cleaned vote data
        """
        cleaned_data = []
        
        for vote in votes:
            cleaned = {
                'id': vote.id,
                'proposal_id': vote.proposal_id,
                'voter': vote.voter.lower(),
                'choice': vote.choice,
                'voting_power': float(vote.voting_power),
                'timestamp': vote.timestamp.strftime(self.date_format)
            }
            cleaned_data.append(cleaned)
            
        df = pd.DataFrame(cleaned_data)
        
        # Handle missing values
        df['voting_power'] = df['voting_power'].fillna(0.0)
        
        return df
    
    def combine_proposal_votes(
        self,
        proposals_df: pd.DataFrame,
        votes_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Combine proposal and vote data with relationships.
        
        Args:
            proposals_df: Cleaned proposals DataFrame
            votes_df: Cleaned votes DataFrame
            
        Returns:
            Combined DataFrame with proposal and vote data
        """
        # Add vote statistics to proposals
        vote_stats = votes_df.groupby('proposal_id').agg({
            'voting_power': ['sum', 'mean', 'count'],
            'voter': 'nunique'
        }).reset_index()
        
        vote_stats.columns = [
            'id', 'total_voting_power', 'mean_voting_power',
            'vote_count', 'unique_voters'
        ]
        
        return proposals_df.merge(vote_stats, on='id', how='left')
    
    def generate_context_summary(self, space_id: str) -> Dict[str, Any]:
        """
        Generate context summary for a space.
        
        Args:
            space_id: Space ID to summarize
            
        Returns:
            Dictionary containing context summary
        """
        space = self.db.query(Space).filter_by(id=space_id).first()
        proposals = self.db.query(Proposal).filter_by(space_id=space_id).all()
        votes = self.db.query(Vote).join(Proposal).filter(Proposal.space_id == space_id).all()
        
        # Clean and process data
        proposals_df = self.clean_proposal_data(proposals)
        votes_df = self.clean_vote_data(votes)
        combined_df = self.combine_proposal_votes(proposals_df, votes_df)
        
        # Generate summary statistics
        summary = {
            'space_name': space.name,
            'space_id': space.id,
            'total_proposals': len(proposals),
            'total_votes': len(votes),
            'unique_voters': votes_df['voter'].nunique(),
            'active_period': {
                'start': proposals_df['start_date'].min(),
                'end': proposals_df['end_date'].max()
            },
            'proposal_stats': {
                'avg_votes_per_proposal': combined_df['vote_count'].mean(),
                'avg_voting_power': combined_df['total_voting_power'].mean(),
                'success_rate': (
                    combined_df['state'].value_counts(normalize=True).get('active', 0)
                )
            },
            'top_authors': proposals_df['author'].value_counts().head(5).to_dict(),
            'top_voters': votes_df['voter'].value_counts().head(5).to_dict()
        }
        
        return summary
    
    def extract_key_patterns(
        self,
        proposals_df: pd.DataFrame,
        votes_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Extract key patterns from proposal and vote data.
        
        Args:
            proposals_df: Cleaned proposals DataFrame
            votes_df: Cleaned votes DataFrame
            
        Returns:
            Dictionary containing identified patterns
        """
        patterns = {
            'temporal_patterns': {
                'proposal_creation': self._analyze_temporal_patterns(
                    proposals_df['start_date']
                ),
                'voting_activity': self._analyze_temporal_patterns(
                    votes_df['timestamp']
                )
            },
            'voter_behavior': {
                'participation_distribution': self._analyze_voter_distribution(
                    votes_df
                ),
                'power_distribution': self._analyze_voting_power_distribution(
                    votes_df
                )
            },
            'proposal_patterns': {
                'success_factors': self._analyze_success_factors(
                    proposals_df
                ),
                'topic_clusters': self._extract_topic_clusters(
                    proposals_df
                )
            }
        }
        
        return patterns
    
    def _analyze_temporal_patterns(self, timestamps: pd.Series) -> Dict[str, Any]:
        """Analyze temporal patterns in timestamps."""
        ts = pd.to_datetime(timestamps)
        return {
            'daily_distribution': ts.dt.hour.value_counts().to_dict(),
            'weekly_distribution': ts.dt.dayofweek.value_counts().to_dict(),
            'monthly_distribution': ts.dt.month.value_counts().to_dict()
        }
    
    def _analyze_voter_distribution(self, votes_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze voter participation patterns."""
        voter_stats = votes_df.groupby('voter').agg({
            'proposal_id': 'count',
            'voting_power': ['mean', 'sum']
        })
        
        return {
            'participation_levels': {
                'active': len(voter_stats[voter_stats['proposal_id']['count'] > 5]),
                'moderate': len(voter_stats[
                    (voter_stats['proposal_id']['count'] > 2) &
                    (voter_stats['proposal_id']['count'] <= 5)
                ]),
                'casual': len(voter_stats[voter_stats['proposal_id']['count'] <= 2])
            },
            'power_concentration': {
                'top_10_power': voter_stats['voting_power']['sum'].nlargest(10).sum() /
                               voter_stats['voting_power']['sum'].sum()
            }
        }
    
    def _analyze_voting_power_distribution(
        self,
        votes_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Analyze voting power distribution patterns."""
        power_stats = votes_df['voting_power'].describe()
        
        return {
            'distribution_stats': {
                'mean': power_stats['mean'],
                'median': power_stats['50%'],
                'std': power_stats['std']
            },
            'concentration_index': self._calculate_gini(
                votes_df.groupby('voter')['voting_power'].sum()
            )
        }
    
    def _analyze_success_factors(self, proposals_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze factors correlated with proposal success."""
        success_corr = proposals_df.corr()['state'].sort_values(ascending=False)
        
        return {
            'correlations': success_corr.to_dict(),
            'timing_impact': self._analyze_timing_impact(proposals_df),
            'participation_threshold': self._find_participation_threshold(proposals_df)
        }
    
    def _extract_topic_clusters(self, proposals_df: pd.DataFrame) -> Dict[str, Any]:
        """Extract topic clusters from proposal titles and bodies."""
        # Basic keyword extraction for demonstration
        # In practice, you might want to use more sophisticated NLP
        keywords = []
        for text in proposals_df['title'] + ' ' + proposals_df['body']:
            words = re.findall(r'\b\w+\b', text.lower())
            keywords.extend(words)
            
        keyword_freq = pd.Series(keywords).value_counts()
        
        return {
            'common_topics': keyword_freq.head(20).to_dict(),
            'topic_correlations': self._analyze_topic_correlations(
                proposals_df, keyword_freq.head(20).index
            )
        }
    
    @staticmethod
    def _calculate_gini(values: pd.Series) -> float:
        """Calculate Gini coefficient for distribution analysis."""
        sorted_values = values.sort_values()
        cumulative = sorted_values.cumsum()
        return (
            (np.arange(1, len(cumulative) + 1) / len(cumulative) - 
             cumulative / cumulative.sum())
        ).sum() / len(cumulative)
    
    def prepare_claude_export(
        self,
        space_id: str,
        export_type: str = 'full'
    ) -> Dict[str, Any]:
        """
        Prepare data export optimized for Claude analysis.
        
        Args:
            space_id: Space ID to export
            export_type: Type of export (full, summary, analysis)
            
        Returns:
            Dictionary containing formatted data for Claude
        """
        # Get base data
        space = self.db.query(Space).filter_by(id=space_id).first()
        proposals = self.db.query(Proposal).filter_by(space_id=space_id).all()
        votes = self.db.query(Vote).join(Proposal).filter(
            Proposal.space_id == space_id
        ).all()
        
        # Clean and process data
        proposals_df = self.clean_proposal_data(proposals)
        votes_df = self.clean_vote_data(votes)
        combined_df = self.combine_proposal_votes(proposals_df, votes_df)
        
        # Generate context and patterns
        context = self.generate_context_summary(space_id)
        patterns = self.extract_key_patterns(proposals_df, votes_df)
        
        export_data = {
            'metadata': {
                'space_id': space_id,
                'space_name': space.name,
                'export_type': export_type,
                'export_date': datetime.now().strftime(self.date_format),
                'data_period': {
                    'start': context['active_period']['start'],
                    'end': context['active_period']['end']
                }
            },
            'context': context,
            'patterns': patterns
        }
        
        if export_type == 'full':
            export_data.update({
                'proposals': combined_df.to_dict(orient='records'),
                'votes': votes_df.to_dict(orient='records')
            })
        elif export_type == 'analysis':
            export_data.update({
                'analysis_ready_data': self._prepare_analysis_data(
                    combined_df, votes_df
                )
            })
        
        return export_data
    
    def _prepare_analysis_data(
        self,
        proposals_df: pd.DataFrame,
        votes_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Prepare data specifically for analysis."""
        return {
            'proposal_metrics': {
                'success_rate_over_time': self._calculate_success_rate_over_time(
                    proposals_df
                ),
                'participation_trends': self._calculate_participation_trends(
                    proposals_df
                ),
                'voting_power_distribution': self._calculate_power_distribution(
                    votes_df
                )
            },
            'voter_metrics': {
                'engagement_levels': self._calculate_engagement_levels(votes_df),
                'voting_patterns': self._analyze_voting_patterns(votes_df)
            }
        }