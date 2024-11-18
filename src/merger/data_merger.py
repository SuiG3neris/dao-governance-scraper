"""
Flexible data merging system for DAO analyzer.
Handles combining, deduplicating, and relating data from different sources.
"""

from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from enum import Enum
import pandas as pd
import numpy as np
from pathlib import Path

from .core.data_processor import DataProcessor, ProcessingResult, ValidationError

class ConflictResolutionStrategy(Enum):
    """Strategies for resolving data conflicts."""
    KEEP_NEWEST = "newest"  # Keep most recent value based on timestamp
    KEEP_OLDEST = "oldest"  # Keep oldest value based on timestamp
    KEEP_SOURCE_A = "source_a"  # Always keep value from source A
    KEEP_SOURCE_B = "source_b"  # Always keep value from source B
    KEEP_MOST_COMPLETE = "most_complete"  # Keep record with most non-null fields
    COMBINE = "combine"  # Combine values (e.g., for lists/sets)
    CUSTOM = "custom"  # Use custom resolution function

@dataclass
class MergeConfig:
    """Configuration for data merging operations."""
    key_fields: List[str]  # Fields used to identify matching records
    conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.KEEP_NEWEST
    timestamp_field: Optional[str] = None  # Field containing record timestamps
    custom_resolver: Optional[Callable] = None  # Custom conflict resolution function
    case_sensitive: bool = False  # Whether to treat string keys as case sensitive
    merge_similar: bool = True  # Whether to merge records with similar but not exact keys
    similarity_threshold: float = 0.9  # Threshold for key similarity (0-1)
    source_priority: Optional[List[str]] = None  # Priority order of data sources
    field_mappings: Dict[str, str] = field(default_factory=dict)  # Map fields between sources
    ignored_fields: List[str] = field(default_factory=list)  # Fields to exclude from merge

@dataclass
class MergeResult:
    """Results of a merge operation."""
    success: bool = True
    merged_data: Optional[Union[pd.DataFrame, Dict]] = None
    conflicts: List[Dict] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class DataMerger(DataProcessor):
    """
    Flexible system for merging data from multiple sources.
    Handles conflict resolution, relationship creation, and data integrity.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize data merger with configuration."""
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def merge(
        self,
        source_a: Union[pd.DataFrame, Dict],
        source_b: Union[pd.DataFrame, Dict],
        merge_config: MergeConfig
    ) -> MergeResult:
        """
        Merge two data sources based on configuration.
        
        Args:
            source_a: First data source
            source_b: Second data source
            merge_config: Configuration for merge operation
            
        Returns:
            MergeResult containing merged data and operation details
        """
        result = MergeResult()
        
        try:
            # Convert inputs to DataFrames if needed
            df_a = self._to_dataframe(source_a)
            df_b = self._to_dataframe(source_b)
            
            # Apply field mappings
            df_a = self._apply_field_mappings(df_a, merge_config.field_mappings)
            df_b = self._apply_field_mappings(df_b, merge_config.field_mappings)
            
            # Validate merge keys exist
            self._validate_merge_keys(df_a, df_b, merge_config)
            
            # Prepare keys for merging
            df_a, df_b = self._prepare_merge_keys(df_a, df_b, merge_config)
            
            # Identify matching records
            matches = self._find_matches(df_a, df_b, merge_config)
            
            # Handle conflicts
            resolved_data = self._resolve_conflicts(
                df_a, df_b, matches, merge_config, result
            )
            
            # Handle unmatched records
            final_data = self._handle_unmatched(
                resolved_data, df_a, df_b, matches, merge_config
            )
            
            # Clean up merged data
            final_data = self._cleanup_merged_data(
                final_data, merge_config.ignored_fields
            )
            
            # Add merge statistics
            result.stats = {
                'total_records': len(final_data),
                'matches_found': len(matches),
                'conflicts_resolved': len(result.conflicts),
                'source_a_only': len(df_a) - len(matches),
                'source_b_only': len(df_b) - len(matches)
            }
            
            result.merged_data = final_data
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self.logger.error(f"Merge failed: {e}")
            
        return result
    
    def _to_dataframe(self, data: Union[pd.DataFrame, Dict]) -> pd.DataFrame:
        """Convert input data to DataFrame if needed."""
        if isinstance(data, pd.DataFrame):
            return data.copy()
        elif isinstance(data, dict):
            return pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
            
    def _apply_field_mappings(
        self,
        df: pd.DataFrame,
        mappings: Dict[str, str]
    ) -> pd.DataFrame:
        """Apply field name mappings to DataFrame."""
        return df.rename(columns=mappings)
    
    def _validate_merge_keys(
        self,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        config: MergeConfig
    ) -> None:
        """Validate that merge keys exist in both DataFrames."""
        for key in config.key_fields:
            if key not in df_a.columns:
                raise ValidationError(f"Merge key '{key}' not found in source A")
            if key not in df_b.columns:
                raise ValidationError(f"Merge key '{key}' not found in source B")
    
    def _prepare_merge_keys(
        self,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        config: MergeConfig
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Prepare key fields for merging."""
        # Handle case sensitivity
        if not config.case_sensitive:
            for key in config.key_fields:
                if df_a[key].dtype == object:
                    df_a[key] = df_a[key].str.lower()
                if df_b[key].dtype == object:
                    df_b[key] = df_b[key].str.lower()
        
        return df_a, df_b
    
    def _find_matches(
        self,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        config: MergeConfig
    ) -> pd.DataFrame:
        """Find matching records between DataFrames."""
        if config.merge_similar:
            return self._find_similar_matches(df_a, df_b, config)
        else:
            return pd.merge(
                df_a, df_b,
                on=config.key_fields,
                how='inner',
                suffixes=('_a', '_b'),
                indicator=True
            )
    
    def _find_similar_matches(
        self,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        config: MergeConfig
    ) -> pd.DataFrame:
        """Find records with similar but not exact key matches."""
        from rapidfuzz import fuzz
        
        matches = []
        for idx_a, row_a in df_a.iterrows():
            for idx_b, row_b in df_b.iterrows():
                # Calculate similarity score for each key field
                scores = []
                for key in config.key_fields:
                    if pd.api.types.is_string_dtype(df_a[key].dtype):
                        score = fuzz.ratio(str(row_a[key]), str(row_b[key])) / 100
                    else:
                        score = 1.0 if row_a[key] == row_b[key] else 0.0
                    scores.append(score)
                
                # Average similarity across all key fields
                avg_score = sum(scores) / len(scores)
                if avg_score >= config.similarity_threshold:
                    matches.append({
                        'idx_a': idx_a,
                        'idx_b': idx_b,
                        'similarity': avg_score
                    })
        
        return pd.DataFrame(matches)
    
    def _resolve_conflicts(
        self,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        matches: pd.DataFrame,
        config: MergeConfig,
        result: MergeResult
    ) -> pd.DataFrame:
        """Resolve conflicts between matching records."""
        resolved_data = []
        
        for _, match in matches.iterrows():
            record_a = df_a.iloc[match['idx_a']]
            record_b = df_b.iloc[match['idx_b']]
            
            # Find conflicting fields
            conflicts = self._find_conflicts(record_a, record_b)
            
            if conflicts:
                resolved = self._apply_resolution_strategy(
                    record_a, record_b, conflicts, config
                )
                result.conflicts.append({
                    'key_values': {k: record_a[k] for k in config.key_fields},
                    'fields': conflicts,
                    'resolution': resolved
                })
            else:
                resolved = record_a.combine_first(record_b)
            
            resolved_data.append(resolved)
            
        return pd.DataFrame(resolved_data)
    
    def _find_conflicts(
        self,
        record_a: pd.Series,
        record_b: pd.Series
    ) -> Dict[str, tuple]:
        """Identify conflicting fields between records."""
        conflicts = {}
        for field in record_a.index:
            if field in record_b.index:
                val_a = record_a[field]
                val_b = record_b[field]
                if not pd.isna(val_a) and not pd.isna(val_b) and val_a != val_b:
                    conflicts[field] = (val_a, val_b)
        return conflicts
    
    def _apply_resolution_strategy(
        self,
        record_a: pd.Series,
        record_b: pd.Series,
        conflicts: Dict[str, tuple],
        config: MergeConfig
    ) -> pd.Series:
        """Apply configured conflict resolution strategy."""
        resolved = record_a.copy()
        
        if config.conflict_strategy == ConflictResolutionStrategy.KEEP_NEWEST:
            if config.timestamp_field:
                if record_b[config.timestamp_field] > record_a[config.timestamp_field]:
                    resolved.update(record_b)
                    
        elif config.conflict_strategy == ConflictResolutionStrategy.KEEP_OLDEST:
            if config.timestamp_field:
                if record_b[config.timestamp_field] < record_a[config.timestamp_field]:
                    resolved.update(record_b)
                    
        elif config.conflict_strategy == ConflictResolutionStrategy.KEEP_SOURCE_A:
            pass  # Keep record_a values
            
        elif config.conflict_strategy == ConflictResolutionStrategy.KEEP_SOURCE_B:
            resolved.update(record_b)
            
        elif config.conflict_strategy == ConflictResolutionStrategy.KEEP_MOST_COMPLETE:
            null_count_a = record_a.isna().sum()
            null_count_b = record_b.isna().sum()
            if null_count_b < null_count_a:
                resolved.update(record_b)
                
        elif config.conflict_strategy == ConflictResolutionStrategy.COMBINE:
            for field, (val_a, val_b) in conflicts.items():
                if isinstance(val_a, (list, set)) and isinstance(val_b, (list, set)):
                    resolved[field] = list(set(val_a) | set(val_b))
                elif isinstance(val_a, str) and isinstance(val_b, str):
                    resolved[field] = f"{val_a} | {val_b}"
                    
        elif config.conflict_strategy == ConflictResolutionStrategy.CUSTOM:
            if config.custom_resolver:
                resolved = config.custom_resolver(record_a, record_b, conflicts)
                
        return resolved
    
    def _handle_unmatched(
        self,
        matched_data: pd.DataFrame,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        matches: pd.DataFrame,
        config: MergeConfig
    ) -> pd.DataFrame:
        """Handle records that didn't match between sources."""
        matched_idx_a = set(matches['idx_a'])
        matched_idx_b = set(matches['idx_b'])
        
        unmatched_a = df_a[~df_a.index.isin(matched_idx_a)]
        unmatched_b = df_b[~df_b.index.isin(matched_idx_b)]
        
        # Combine all data
        all_data = pd.concat([matched_data, unmatched_a, unmatched_b])
        
        return all_data
    
    def _cleanup_merged_data(
        self,
        df: pd.DataFrame,
        ignored_fields: List[str]
    ) -> pd.DataFrame:
        """Clean up merged DataFrame."""
        # Remove ignored fields
        for field in ignored_fields:
            if field in df.columns:
                df = df.drop(columns=[field])
        
        # Remove duplicate suffix columns
        suffix_cols = [col for col in df.columns if col.endswith('_a') or col.endswith('_b')]
        df = df.drop(columns=suffix_cols)
        
        # Reset index
        df = df.reset_index(drop=True)
        
        return df