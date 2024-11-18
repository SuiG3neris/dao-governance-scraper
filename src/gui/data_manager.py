"""
Data manager for handling DAO data and Claude integration.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pandas as pd

@dataclass
class ClaudeExportFormat:
    """Structure for Claude-optimized data format."""
    context: Dict[str, Any]
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class DataManager:
    """Manages data processing and Claude integration."""
    
def __init__(self):
    """Initialize the data manager."""
    self.raw_data: Dict[str, List[Dict[str, Any]]] = {
        'spaces': [],
        'proposals': [],
        'votes': [],
        'holders': [],
        'transfers': [],
        'forum_posts': [],
        'forum_comments': []
    }
        
    def add_data(self, data_type: str, items: List[Dict[str, Any]]) -> None:
        """
        Add new data items to the manager.
        
        Args:
            data_type: Type of data ('spaces', 'proposals', etc.)
            items: List of data items to add
        """
        if data_type not in self.raw_data:
            raise ValueError(f"Unknown data type: {data_type}")
            
        self.raw_data[data_type].extend(items)
        
        # Convert to DataFrame for processing
        if items:
            df = pd.DataFrame(items)
            if data_type in self.processed_data:
                self.processed_data[data_type] = pd.concat(
                    [self.processed_data[data_type], df],
                    ignore_index=True
                )
            else:
                self.processed_data[data_type] = df
                
    def get_data_preview(self, data_type: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get a preview of the data for display.
        
        Args:
            data_type: Type of data to preview
            limit: Maximum number of items to return
            
        Returns:
            List of data items for preview
        """
        if data_type not in self.processed_data:
            return []
            
        df = self.processed_data[data_type]
        return df.head(limit).to_dict('records')
        
    def get_statistics(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about the collected data.
        
        Returns:
            Dictionary of statistics for each data type
        """
        stats = {}
        for data_type, items in self.raw_data.items():
            stats[data_type] = {
                'total_items': len(items),
                'unique_items': len(set(item.get('id') for item in items if 'id' in item))
            }
            
        return stats
        
    def prepare_for_claude(self, data_types: List[str]) -> ClaudeExportFormat:
        """
        Prepare data for Claude analysis.
        
        Args:
            data_types: List of data types to include
            
        Returns:
            Formatted data structure for Claude
        """
        # Build context information
        context = {
            'data_types': data_types,
            'statistics': self.get_statistics(),
            'schema': self._get_data_schema(data_types)
        }
        
        # Prepare selected data
        data = {}
        for data_type in data_types:
            if data_type in self.processed_data:
                df = self.processed_data[data_type]
                data[data_type] = df.to_dict('records')
                
        # Add metadata
        metadata = {
            'version': '1.0',
            'format': 'claude_optimized',
            'encoding': 'utf-8'
        }
        
        return ClaudeExportFormat(
            context=context,
            data=data,
            metadata=metadata
        )
        
    def export_for_claude(self, 
                         data_types: List[str],
                         format: str = 'json',
                         filepath: Optional[Path] = None) -> Path:
        """
        Export data in Claude-friendly format.
        
        Args:
            data_types: List of data types to export
            format: Export format ('json' or 'yaml')
            filepath: Optional specific export path
            
        Returns:
            Path to exported file
        """
        # Prepare data
        export_data = self.prepare_for_claude(data_types)
        
        # Generate filepath if not provided
        if filepath is None:
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            filepath = self.export_path / f'claude_export_{timestamp}.{format}'
            
        # Export based on format
        if format == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(export_data), f, indent=2)
        elif format == 'yaml':
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(asdict(export_data), f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
            
        return filepath
        
    def _get_data_schema(self, data_types: List[str]) -> Dict[str, List[str]]:
        """Get schema information for selected data types."""
        schema = {}
        for data_type in data_types:
            if data_type in self.processed_data:
                df = self.processed_data[data_type]
                schema[data_type] = list(df.columns)
        return schema
        
    def clear_data(self) -> None:
        """Clear all stored data."""
        self.raw_data = {key: [] for key in self.raw_data}
        self.processed_data = {}
        
    def validate_data(self, data_type: str) -> List[str]:
        """
        Validate data for consistency and completeness.
        
        Args:
            data_type: Type of data to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        if data_type not in self.processed_data:
            return [f"No data available for type: {data_type}"]
            
        df = self.processed_data[data_type]
        
        # Check for missing required fields
        required_fields = {
            'spaces': ['id', 'name'],
            'proposals': ['id', 'title', 'space_id'],
            'votes': ['id', 'proposal_id', 'voter'],
            'holders': ['address', 'balance'],
            'transfers': ['from_address', 'to_address', 'amount']
        }
        
        if data_type in required_fields:
            for field in required_fields[data_type]:
                if field not in df.columns:
                    errors.append(f"Missing required field: {field}")
                elif df[field].isna().any():
                    errors.append(f"Found null values in required field: {field}")
                    
        # Check data consistency
        if data_type == 'proposals':
            # Check if all space_ids exist
            if 'spaces' in self.processed_data:
                space_ids = set(self.processed_data['spaces']['id'])
                invalid_spaces = df[~df['space_id'].isin(space_ids)]['space_id'].unique()
                if len(invalid_spaces) > 0:
                    errors.append(f"Found proposals with invalid space_ids: {invalid_spaces}")
                    
        elif data_type == 'votes':
            # Check if all proposal_ids exist
            if 'proposals' in self.processed_data:
                proposal_ids = set(self.processed_data['proposals']['id'])
                invalid_proposals = df[~df['proposal_id'].isin(proposal_ids)]['proposal_id'].unique()
                if len(invalid_proposals) > 0:
                    errors.append(f"Found votes with invalid proposal_ids: {invalid_proposals}")
        
        return errors
    
    def prepare_forum_data_for_claude(self) -> Dict[str, Any]:

    if 'forum_posts' not in self.processed_data:
        return {}
        
    posts_df = self.processed_data['forum_posts']
    comments_df = self.processed_data.get('forum_comments', pd.DataFrame())
    
    # Group discussions by category
    discussions_by_category = {}
    for category in posts_df['category'].unique():
        category_posts = posts_df[posts_df['category'] == category]
        discussions_by_category[category] = {
            'post_count': len(category_posts),
            'unique_authors': len(category_posts['author'].unique()),
            'avg_replies': category_posts['replies'].mean(),
            'avg_views': category_posts['views'].mean(),
            'top_posts': category_posts.nlargest(5, 'replies')[
                ['title', 'author', 'replies', 'views', 'url']
            ].to_dict('records')
        }
    
    # Analyze engagement patterns
    engagement_analysis = {
        'total_posts': len(posts_df),
        'total_comments': len(comments_df),
        'unique_authors': len(pd.concat([
            posts_df['author'],
            comments_df['author'] if not comments_df.empty else pd.Series()
        ]).unique()),
        'most_active_categories': [
            {
                'category': category,
                'post_count': count
            }
            for category, count in posts_df['category'].value_counts().head().items()
        ],
        'most_engaged_authors': [
            {
                'author': author,
                'contribution_count': count
            }
            for author, count in pd.concat([
                posts_df['author'],
                comments_df['author'] if not comments_df.empty else pd.Series()
            ]).value_counts().head().items()
        ]
    }
    
    # Prepare discussion threads
    discussion_threads = []
    for _, post in posts_df.iterrows():
        if not comments_df.empty:
            thread_comments = comments_df[comments_df['post_id'] == post['id']]
            comment_thread = thread_comments.sort_values('timestamp').to_dict('records')
        else:
            comment_thread = []
            
        discussion_threads.append({
            'post': post.to_dict(),
            'comments': comment_thread,
            'metrics': {
                'reply_count': len(comment_thread),
                'unique_participants': len(set(c['author'] for c in comment_thread) | {post['author']}),
                'duration': (
                    max(c['timestamp'] for c in comment_thread) - post['timestamp']
                ).total_seconds() if comment_thread else 0
            }
        })
    
    return {
        'categories': discussions_by_category,
        'engagement': engagement_analysis,
        'discussions': discussion_threads,
        'metadata': {
            'platforms': posts_df['platform'].unique().tolist(),
            'date_range': {
                'start': posts_df['timestamp'].min().isoformat(),
                'end': posts_df['timestamp'].max().isoformat()
            },
            'export_timestamp': datetime.now().isoformat()
        }
    }