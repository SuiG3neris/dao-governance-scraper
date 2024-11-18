# Data Merger Module

The Data Merger module provides robust functionality for combining and reconciling data from different sources in the DAO analyzer system. It handles conflict resolution, relationship creation, and maintains data integrity throughout the merging process.

## Key Features

- Flexible configuration system for merge operations
- Multiple conflict resolution strategies
- Support for exact and fuzzy key matching
- Handles different data formats (DataFrame, Dictionary)
- Detailed merge results with statistics and conflict tracking
- Custom field mapping support
- Case-sensitive and case-insensitive key matching
- Built-in data validation

## Installation

The merger module is part of the DAO analyzer package. No additional installation is required.

## Quick Start

```python
from src.merger import DataMerger, MergeConfig, ConflictResolutionStrategy

# Initialize merger
merger = DataMerger()

# Configure merge operation
config = MergeConfig(
    key_fields=['proposal_id', 'voter_address'],
    conflict_strategy=ConflictResolutionStrategy.KEEP_NEWEST,
    timestamp_field='created_at'
)

# Merge data sources
result = merger.merge(source_a, source_b, config)

if result.success:
    merged_data = result.merged_data
    print(f"Successfully merged {result.stats['total_records']} records")
else:
    print(f"Merge failed: {result.errors}")
```

## Configuration Options

### MergeConfig Fields

- `key_fields`: List of fields used to identify matching records
- `conflict_strategy`: Strategy for resolving conflicts between sources
- `timestamp_field`: Field containing record timestamps (for time-based resolution)
- `custom_resolver`: Custom function for conflict resolution
- `case_sensitive`: Whether to treat string keys as case sensitive
- `merge_similar`: Enable fuzzy matching for similar keys
- `similarity_threshold`: Threshold for fuzzy matching (0-1)
- `source_priority`: Priority order of data sources
- `field_mappings`: Map fields between sources
- `ignored_fields`: Fields to exclude from merge

### Available Conflict Resolution Strategies

- `KEEP_NEWEST`: Keep most recent value based on timestamp
- `KEEP_OLDEST`: Keep oldest value based on timestamp
- `KEEP_SOURCE_A`: Always keep value from source A
- `KEEP_SOURCE_B`: Always keep value from source B
- `KEEP_MOST_COMPLETE`: Keep record with most non-null fields
- `COMBINE`: Combine values (for lists/sets)
- `CUSTOM`: Use custom resolution function

## Common Usage Examples

### Basic Merge with Newest Values

```python
config = MergeConfig(
    key_fields=['id'],
    conflict_strategy=ConflictResolutionStrategy.KEEP_NEWEST,
    timestamp_field='updated_at'
)

result = merger.merge(data_source_1, data_source_2, config)
```

### Merge with Field Mapping

```python
config = MergeConfig(
    key_fields=['proposal_id'],
    field_mappings={
        'voter': 'voter_address',
        'vote_power': 'voting_power'
    }
)

result = merger.merge(snapshot_data, chain_data, config)
```

### Fuzzy Matching

```python
config = MergeConfig(
    key_fields=['name', 'address'],
    merge_similar=True,
    similarity_threshold=0.9
)

result = merger.merge(source_a, source_b, config)
```

### Custom Conflict Resolution

```python
def custom_resolver(record_a, record_b, conflicts):
    resolved = record_a.copy()
    for field, (val_a, val_b) in conflicts.items():
        resolved[field] = max(val_a, val_b)  # Keep maximum value
    return resolved

config = MergeConfig(
    key_fields=['id'],
    conflict_strategy=ConflictResolutionStrategy.CUSTOM,
    custom_resolver=custom_resolver
)

result = merger.merge(source_a, source_b, config)
```

## Working with Results

### Accessing Merge Results

```python
if result.success:
    # Access merged data
    merged_df = result.merged_data
    
    # Get merge statistics
    print(f"Total records: {result.stats['total_records']}")
    print(f"Matches found: {result.stats['matches_found']}")
    print(f"Conflicts resolved: {result.stats['conflicts_resolved']}")
    
    # Review conflicts
    for conflict in result.conflicts:
        print(f"Conflict in record: {conflict['key_values']}")
        print(f"Conflicting fields: {conflict['fields']}")
        print(f"Resolution: {conflict['resolution']}")
```

## Best Practices

1. Always validate input data before merging
2. Use appropriate conflict resolution strategies based on data type
3. Monitor merge statistics and conflicts for unexpected results
4. Back up data before performing large merges
5. Use case-insensitive matching for string keys unless case is significant
6. Set appropriate similarity thresholds for fuzzy matching

## Error Handling

The merger provides detailed error information:

```python
try:
    result = merger.merge(source_a, source_b, config)
    if not result.success:
        for error in result.errors:
            print(f"Error: {error}")
except Exception as e:
    print(f"Merge operation failed: {str(e)}")
```

## Contributing

When contributing to the merger module:

1. Add tests for new functionality
2. Update documentation for API changes
3. Follow the existing code style
4. Run the test suite before submitting changes