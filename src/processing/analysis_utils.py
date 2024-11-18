"""
Analysis utilities for DAO governance data.
Provides visualization generators, statistical analysis, and pattern detection.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from src.database.models import Space, Proposal, Vote


class AnalysisUtils:
    """Utilities for analyzing DAO governance data."""
    
    def __init__(self, db_session: Session):
        """Initialize analysis utilities with database session."""
        self.db = db_session
        self.date_format = "%Y-%m-%d %H:%M:%S"

    def generate_participation_metrics(
        self,
        space_id: str,
        time_window: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate participation metrics for a space.
        
        Args:
            space_id: Space ID to analyze
            time_window: Optional time window in days
            
        Returns:
            Dictionary of participation metrics
        """
        # Query data
        query = self.db.query(Vote).join(Proposal).filter(
            Proposal.space_id == space_id
        )
        
        if time_window:
            cutoff = datetime.now() - timedelta(days=time_window)
            query = query.filter(Vote.timestamp >= cutoff)
            
        votes_df = pd.read_sql(query.statement, self.db.bind)
        
        if votes_df.empty:
            return {}
            
        # Calculate metrics
        metrics = {
            'total_votes': len(votes_df),
            'unique_voters': votes_df['voter'].nunique(),
            'avg_voting_power': votes_df['voting_power'].mean(),
            'voting_power_distribution': {
                'min': votes_df['voting_power'].min(),
                'max': votes_df['voting_power'].max(),
                'median': votes_df['voting_power'].median(),
                'std': votes_df['voting_power'].std()
            },
            'participation_quartiles': {
                'q25': votes_df.groupby('voter')['proposal_id'].count().quantile(0.25),
                'q50': votes_df.groupby('voter')['proposal_id'].count().quantile(0.50),
                'q75': votes_df.groupby('voter')['proposal_id'].count().quantile(0.75)
            }
        }
        
        # Add time-based metrics
        if 'timestamp' in votes_df.columns:
            votes_df['date'] = pd.to_datetime(votes_df['timestamp'])
            metrics.update({
                'temporal_patterns': {
                    'daily': votes_df['date'].dt.hour.value_counts().to_dict(),
                    'weekly': votes_df['date'].dt.dayofweek.value_counts().to_dict(),
                    'monthly': votes_df['date'].dt.month.value_counts().to_dict()
                }
            })
            
        return metrics

    def analyze_proposal_outcomes(
        self,
        space_id: str,
        min_votes: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze proposal outcomes and success patterns.
        
        Args:
            space_id: Space ID to analyze
            min_votes: Minimum number of votes for inclusion
            
        Returns:
            Dictionary of proposal outcome analysis
        """
        # Query proposals and votes
        proposals = self.db.query(Proposal).filter_by(space_id=space_id).all()
        proposal_df = pd.DataFrame([p.__dict__ for p in proposals])
        
        if proposal_df.empty:
            return {}
            
        # Add vote counts
        vote_counts = pd.read_sql(
            self.db.query(Vote.proposal_id, Vote.id)
            .group_by(Vote.proposal_id)
            .statement,
            self.db.bind
        ).groupby('proposal_id').count()
        
        proposal_df = proposal_df.join(vote_counts, on='id')
        
        # Filter by minimum votes
        proposal_df = proposal_df[proposal_df['id'] >= min_votes]
        
        # Calculate success metrics
        analysis = {
            'success_rate': (
                proposal_df['state'].value_counts(normalize=True).get('active', 0)
            ),
            'vote_distribution': {
                'mean': proposal_df['id'].mean(),
                'median': proposal_df['id'].median(),
                'std': proposal_df['id'].std()
            },
            'duration_stats': {
                'avg_duration': (
                    proposal_df['end'] - proposal_df['start']
                ).mean().total_seconds() / 3600,  # in hours
                'duration_correlation': proposal_df['id'].corr(
                    (proposal_df['end'] - proposal_df['start'])
                    .dt.total_seconds()
                )
            }
        }
        
        # Add timing analysis
        proposal_df['hour_created'] = proposal_df['start'].dt.hour
        proposal_df['day_created'] = proposal_df['start'].dt.dayofweek
        
        analysis['timing_patterns'] = {
            'hour_success_rate': self._calculate_success_by_factor(
                proposal_df, 'hour_created'
            ),
            'day_success_rate': self._calculate_success_by_factor(
                proposal_df, 'day_created'
            )
        }
        
        return analysis

    def identify_voter_clusters(
        self,
        space_id: str,
        n_clusters: int = 4
    ) -> Dict[str, Any]:
        """
        Identify voter clusters based on behavior.
        
        Args:
            space_id: Space ID to analyze
            n_clusters: Number of clusters to identify
            
        Returns:
            Dictionary of voter cluster analysis
        """
        # Get voter activity data
        votes_df = pd.read_sql(
            self.db.query(Vote).join(Proposal)
            .filter(Proposal.space_id == space_id)
            .statement,
            self.db.bind
        )
        
        if votes_df.empty:
            return {}
            
        # Create voter features
        voter_features = votes_df.groupby('voter').agg({
            'id': 'count',  # vote count
            'voting_power': ['mean', 'std'],
            'proposal_id': 'nunique'  # unique proposals
        }).fillna(0)
        
        # Normalize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(voter_features)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(features_scaled)
        
        # Analyze clusters
        voter_features['cluster'] = clusters
        cluster_analysis = {
            'cluster_sizes': voter_features['cluster'].value_counts().to_dict(),
            'cluster_centers': {
                f'cluster_{i}': {
                    feature: value
                    for feature, value in zip(voter_features.columns, center)
                }
                for i, center in enumerate(kmeans.cluster_centers_)
            },
            'cluster_stats': {
                f'cluster_{i}': voter_features[voter_features['cluster'] == i]
                .mean()
                .to_dict()
                for i in range(n_clusters)
            }
        }
        
        return cluster_analysis

    def detect_relationship_patterns(
        self,
        space_id: str
    ) -> Dict[str, Any]:
        """
        Detect patterns in voter-proposal relationships.
        
        Args:
            space_id: Space ID to analyze
            
        Returns:
            Dictionary of relationship patterns
        """
        # Get voting relationships
        votes_df = pd.read_sql(
            self.db.query(Vote).join(Proposal)
            .filter(Proposal.space_id == space_id)
            .statement,
            self.db.bind
        )
        
        if votes_df.empty:
            return {}
            
        # Analyze voter-proposal networks
        voter_connections = votes_df.merge(
            votes_df,
            on='proposal_id',
            suffixes=('_1', '_2')
        )
        
        # Find voter similarities
        voter_similarities = {}
        for voter in votes_df['voter'].unique():
            voter_votes = set(
                votes_df[votes_df['voter'] == voter]['proposal_id']
            )
            similarities = []
            
            for other_voter in votes_df['voter'].unique():
                if voter != other_voter:
                    other_votes = set(
                        votes_df[votes_df['voter'] == other_voter]['proposal_id']
                    )
                    similarity = len(voter_votes & other_votes) / len(
                        voter_votes | other_votes
                    )
                    similarities.append((other_voter, similarity))
            
            voter_similarities[voter] = sorted(
                similarities,
                key=lambda x: x[1],
                reverse=True
            )[:5]  # Top 5 similar voters
            
        # Analyze voting blocks
        vote_correlations = votes_df.pivot(
            index='voter',
            columns='proposal_id',
            values='choice'
        ).corr()
        
        return {
            'voter_similarities': voter_similarities,
            'voting_blocks': self._identify_voting_blocks(vote_correlations),
            'proposal_relationships': self._analyze_proposal_relationships(votes_df)
        }

    def generate_trend_analysis(
        self,
        space_id: str,
        window: str = '7D'
    ) -> Dict[str, Any]:
        """
        Generate trend analysis over time.
        
        Args:
            space_id: Space ID to analyze
            window: Time window for rolling calculations
            
        Returns:
            Dictionary of trend analysis
        """
        # Get time series data
        votes_df = pd.read_sql(
            self.db.query(Vote).join(Proposal)
            .filter(Proposal.space_id == space_id)
            .statement,
            self.db.bind
        )
        
        if votes_df.empty:
            return {}
            
        votes_df['date'] = pd.to_datetime(votes_df['timestamp'])
        daily_stats = votes_df.set_index('date').resample('D').agg({
            'id': 'count',
            'voting_power': ['sum', 'mean'],
            'voter': 'nunique'
        })
        
        # Calculate trends
        trends = {
            'participation_trend': self._calculate_trend(
                daily_stats['voter']['nunique'].rolling(window).mean()
            ),
            'voting_power_trend': self._calculate_trend(
                daily_stats['voting_power']['sum'].rolling(window).mean()
            ),
            'activity_trend': self._calculate_trend(
                daily_stats['id']['count'].rolling(window).mean()
            )
        }
        
        # Add seasonality analysis
        if len(daily_stats) > 14:  # Need enough data for seasonal analysis
            trends['seasonality'] = {
                'weekly': self._analyze_seasonality(
                    daily_stats['id']['count'], 7
                ),
                'biweekly': self._analyze_seasonality(
                    daily_stats['id']['count'], 14
                )
            }
            
        return trends

    @staticmethod
    def _calculate_success_by_factor(df: pd.DataFrame, factor: str) -> Dict[str, float]:
        """Calculate success rates by a given factor."""
        return df.groupby(factor)['state'].apply(
            lambda x: (x == 'active').mean()
        ).to_dict()

    @staticmethod
    def _identify_voting_blocks(corr_matrix: pd.DataFrame, threshold: float = 0.7) -> List[List[str]]:
        """Identify voting blocks from correlation matrix."""
        blocks = []
        voters = list(corr_matrix.index)
        
        while voters:
            voter = voters[0]
            block = [voter]
            
            for other_voter in voters[1:]:
                if all(corr_matrix.loc[v, other_voter] > threshold for v in block):
                    block.append(other_voter)
                    
            if len(block) > 1:
                blocks.append(block)
            voters = [v for v in voters if v not in block]
            
        return blocks

    @staticmethod
    def _analyze_proposal_relationships(
        votes_df: pd.DataFrame
    ) -> Dict[str, List[Tuple[str, float]]]:
        """Analyze relationships between proposals based on voting patterns."""
        proposal_votes = votes_df.pivot(
            index='voter',
            columns='proposal_id',
            values='choice'
        )
        
        relationships = {}
        for proposal in proposal_votes.columns:
            correlations = proposal_votes[proposal].corr(
                proposal_votes.drop(proposal, axis=1)
            )
            relationships[proposal] = [
                (col, corr) for col, corr in correlations.nlargest(5).items()
            ]
            
        return relationships

    @staticmethod
    def _calculate_trend(series: pd.Series) -> Dict[str, float]:
        """Calculate trend statistics for a time series."""
        if series.empty:
            return {}
            
        x = np.arange(len(series))
        y = series.values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        return {
            'slope': slope,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'std_error': std_err
        }

    @staticmethod
    def _analyze_seasonality(
        series: pd.Series,
        period: int
    ) -> Dict[str, float]:
        """Analyze seasonality in a time series."""
        seasonal_means = []
        for i in range(period):
            seasonal_means.append(series[i::period].mean())
            
        return {
            'seasonal_strength': np.std(seasonal_means) / series.std(),
            'peak_period': np.argmax(seasonal_means),
            'trough_period': np.argmin(seasonal_means)
        }