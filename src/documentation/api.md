# Data Merger API Reference

## Classes

### DataMerger

Main class for performing data merge operations.

#### Methods

##### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize a new DataMerger instance.

**Parameters:**
- `config`: Optional configuration dictionary for the merger

##### `merge(source_a: Union[pd.DataFrame, Dict], source_b: Union[pd.DataFrame, Dict], merge_config: MergeConfig) -> MergeResult`
Merge two data sources based on configuration.

**Parameters:**
- `source_a`: First data source (DataFrame or Dictionary)
- `source_b`: Second data source (DataFrame or Dictionary)
- `merge_config`: Configuration for merge operation

**Returns:**
- `MergeResult`: Object containing merge results and statistics

**Raises:**
- `ValidationError`: If merge configuration or data is invalid
- `ProcessingError`: If merge operation fails

### MergeConfig

Configuration class for merge operations.

#### Fields

- `key_fields: List[str]`
  - Fields used to identify matching records
  - Required
  - Example: `['id', 'address']`

- `conflict_strategy: ConflictResolutionStrategy`
  - Strategy for resolving conflicts
  - Default: `KEEP_NEWEST`
  - Type: `ConflictResolutionStrategy` enum

- `timestamp_field: Optional[str]`
  - Field containing record timestamps
  - Required for time-based resolution strategies
  - Example: `'created_at'`

- `custom_resolver: Optional[Callable]`
  - Custom conflict resolution function
  - Signature: `(record_a: pd.Series, record_b: pd.Series, conflicts: Dict) -> pd.Series`

- `case_sensitive: bool`
  - Whether to treat string keys as case sensitive
  - Default: `False`

- `merge_similar: bool`
  - Whether to merge records with similar keys
  - Default: `True`

- `similarity_threshold: float`
  - Threshold for key similarity (0-1)
  - Default: `0.9`

- `source_priority: Optional[List[str]]`
  - Priority order of data sources
  - Example: `['chain_data', 'snapshot_data']`

- `field_mappings: Dict[str, str]`
  - Map fields between sources
  - Example: `{'voter': 'voter_address'}`

- `ignored_fields: List[str]`
  - Fields to exclude from merge
  - Example: `['temp_id', 'internal_ref']`

### MergeResult

Container for merge operation results.

#### Fields

- `success: bool`
  - Whether merge completed successfully
  - Default: `True`

- `merged_data: Optional[Union[pd.DataFrame, Dict]]`
  - Merged data if successful
  - `None` if merge failed

- `conflicts: List[Dict]`
  - Details of conflicts and resolutions
  - Format:
    ```python
    {
        'key_values': Dict,  # Values of key fields
        'fields': Dict,      # Conflicting fields and values
        'resolution': Dict   # How conflicts were resolved
    }
    ```

- `stats: Dict[str, int]`
  - Merge operation statistics
  - Keys:
    - `total_records`: Total records in result
    - `matches_found`: Number of matching records
    - `conflicts_resolved`: Number of conflicts resolved
    - `source_a_only`: Records only in source A
    - `source_b_only`: Records only in source B

- `errors: List[str]`
  - Error messages if merge failed
  - Empty if successful

- `warnings: List[str]`
  - Warning messages from merge operation

### ConflictResolutionStrategy

Enum defining conflict resolution strategies.

#### Values

- `KEEP_NEWEST`
  - Keep most recent value based on timestamp
  - Requires `timestamp_field` in config

- `KEEP_OLDEST`
  - Keep oldest value based on timestamp
  - Requires `timestamp_field` in config

- `KEEP_SOURCE_A`
  - Always keep value from source A
  - Useful when one source is authoritative

- `KEEP_SOURCE_B`
  - Always keep value from source B
  - Useful when one source is authoritative

- `KEEP_MOST_COMPLETE`
  - Keep record with most non-null fields
  - Good for combining partial records

- `COMBINE`
  - Combine values where possible
  - Works with lists, sets, and concatenable values

- `CUSTOM`
  - Use custom resolution function
  - Requires `custom_resolver` in config

## Custom Resolution Functions

When using `ConflictResolutionStrategy.CUSTOM`, provide a resolver function:

```python
def custom_resolver(
    record_a: pd.Series,
    record_b: pd.Series,
    conflicts: Dict[str, tuple]
) -> pd.Series:
    """
    Args:
        record_a: Record from source A
        record_b: Record from source B
        conflicts: Dictionary of field names to (value_a, value_b) tuples
        
    Returns:
        Resolved record as pandas Series
    """
    resolved = record_a.copy()
    # Custom resolution logic here
    return resolved
```

## Error Types

### ValidationError
Raised when:
- Required fields are missing
- Invalid configuration
- Data validation fails

### ProcessingError 
Raised when:
- Merge operation fails
- Data transformation fails
- Resolution strategy fails

## Advanced Usage

### Field Mappings

Use field mappings to handle different field names:

```python
config = MergeConfig(
    key_fields=['id'],
    field_mappings={
        'source_a_field': 'standard_name',
        'source_b_field': 'standard_name'
    }
)
```

### Source Priority

Set source priority for multi-source merges:

```python
config = MergeConfig(
    key_fields=['id'],
    source_priority=['chain_data', 'snapshot_data', 'forum_data']
)
```

### Custom Key Comparison

For complex key matching, use a custom resolver:

```python
def address_matcher(val_a, val_b):
    """Custom address comparison logic"""
    return val_a.lower() == val_b.lower()

config = MergeConfig(
    key_fields=['address'],
    custom_resolver=address_matcher
)
```