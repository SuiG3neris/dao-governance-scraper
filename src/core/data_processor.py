"""
Core data processing module for DAO analysis.
Provides base classes and utilities for data processing and validation.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import json
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

# Custom exceptions for data processing
class DataProcessingError(Exception):
    """Base exception for data processing errors."""
    pass

class ValidationError(DataProcessingError):
    """Raised when data validation fails."""
    pass

class ProcessingError(DataProcessingError):
    """Raised when data processing fails."""
    pass

@dataclass
class ProcessingResult:
    """Container for processing results."""
    success: bool
    data: Optional[Union[pd.DataFrame, Dict, List]] = None
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    processing_time: float = 0.0

    def __post_init__(self):
        """Initialize lists if None."""
        self.errors = self.errors or []
        self.warnings = self.warnings or []
        self.metadata = self.metadata or {}

class DataProcessor(ABC):
    """Base class for data processors."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize data processor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set default configurations
        self.config.setdefault('validation', {
            'required_fields': [],
            'field_types': {},
            'value_ranges': {},
            'max_rows': None,
            'max_size': None
        })
        
    def process(self, data: Any) -> ProcessingResult:
        """
        Process data with validation and error handling.
        
        Args:
            data: Input data to process
            
        Returns:
            ProcessingResult object containing results and metadata
        """
        start_time = datetime.now()
        result = ProcessingResult(success=False)
        
        try:
            # Validate input data
            self.validate_data(data)
            
            # Clean data
            cleaned_data = self.clean_data(data)
            
            # Process data
            processed_data = self._process_data(cleaned_data)
            
            # Validate output
            self.validate_output(processed_data)
            
            result.success = True
            result.data = processed_data
            
        except ValidationError as e:
            self.logger.error(f"Validation error: {str(e)}")
            result.errors.append(f"Validation error: {str(e)}")
            
        except ProcessingError as e:
            self.logger.error(f"Processing error: {str(e)}")
            result.errors.append(f"Processing error: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            result.errors.append(f"Unexpected error: {str(e)}")
            
        finally:
            # Add metadata
            result.processing_time = (datetime.now() - start_time).total_seconds()
            result.metadata.update({
                'processor': self.__class__.__name__,
                'processed_at': datetime.now().isoformat(),
                'config': self.config
            })
            
            return result
    
    @abstractmethod
    def _process_data(self, data: Any) -> Any:
        """
        Process the data. Must be implemented by subclasses.
        
        Args:
            data: Cleaned input data
            
        Returns:
            Processed data
        """
        raise NotImplementedError
    
    def validate_data(self, data: Any) -> None:
        """
        Validate input data.
        
        Args:
            data: Input data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if data is None:
            raise ValidationError("Input data is None")
            
        # Convert to DataFrame if possible
        if isinstance(data, (dict, list)):
            try:
                data = pd.DataFrame(data)
            except Exception as e:
                raise ValidationError(f"Could not convert data to DataFrame: {e}")
        
        if isinstance(data, pd.DataFrame):
            self._validate_dataframe(data)
        else:
            self._validate_generic(data)
    
    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        Validate DataFrame.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Check required fields
        missing_fields = set(self.config['validation']['required_fields']) - set(df.columns)
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")
        
        # Check data types
        for field, expected_type in self.config['validation']['field_types'].items():
            if field in df.columns:
                if not pd.api.types.is_dtype_equal(df[field].dtype, expected_type):
                    try:
                        df[field] = df[field].astype(expected_type)
                    except Exception as e:
                        raise ValidationError(f"Invalid type for field {field}: {e}")
        
        # Check value ranges
        for field, (min_val, max_val) in self.config['validation']['value_ranges'].items():
            if field in df.columns:
                if df[field].min() < min_val or df[field].max() > max_val:
                    raise ValidationError(
                        f"Values out of range for field {field}. "
                        f"Expected [{min_val}, {max_val}]"
                    )
        
        # Check size limits
        if self.config['validation']['max_rows']:
            if len(df) > self.config['validation']['max_rows']:
                raise ValidationError(f"Too many rows: {len(df)}")
    
    def _validate_generic(self, data: Any) -> None:
        """
        Validate non-DataFrame data.
        
        Args:
            data: Data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Check size limit if specified
        if self.config['validation']['max_size']:
            try:
                size = len(data)
                if size > self.config['validation']['max_size']:
                    raise ValidationError(f"Data size {size} exceeds limit")
            except TypeError:
                pass  # Object doesn't support len()
    
    def validate_output(self, data: Any) -> None:
        """
        Validate processed output data.
        
        Args:
            data: Processed data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if data is None:
            raise ValidationError("Output data is None")
    
    def clean_data(self, data: Any) -> Any:
        """
        Clean input data.
        
        Args:
            data: Data to clean
            
        Returns:
            Cleaned data
        """
        if isinstance(data, pd.DataFrame):
            return self._clean_dataframe(data)
        return self._clean_generic(data)
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean DataFrame.
        
        Args:
            df: DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        # Create copy to avoid modifying original
        df = df.copy()
        
        # Remove duplicate rows
        df = df.drop_duplicates()
        
        # Handle missing values
        for column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                # Fill numeric missing values with median
                df[column] = df[column].fillna(df[column].median())
            else:
                # Fill categorical missing values with mode
                df[column] = df[column].fillna(df[column].mode()[0] if not df[column].mode().empty else None)
        
        # Remove whitespace from string columns
        string_columns = df.select_dtypes(include=['object']).columns
        for column in string_columns:
            df[column] = df[column].str.strip()
        
        return df
    
    def _clean_generic(self, data: Any) -> Any:
        """
        Clean non-DataFrame data.
        
        Args:
            data: Data to clean
            
        Returns:
            Cleaned data
        """
        if isinstance(data, dict):
            return {k: self._clean_value(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_value(v) for v in data]
        else:
            return self._clean_value(data)
    
    def _clean_value(self, value: Any) -> Any:
        """
        Clean individual value.
        
        Args:
            value: Value to clean
            
        Returns:
            Cleaned value
        """
        if isinstance(value, str):
            return value.strip()
        return value
    
    def save_results(self, result: ProcessingResult, output_path: Path) -> None:
        """
        Save processing results.
        
        Args:
            result: ProcessingResult to save
            output_path: Path to save results
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Determine format based on data type and file extension
            if isinstance(result.data, pd.DataFrame):
                if output_path.suffix == '.csv':
                    result.data.to_csv(output_path, index=False)
                else:
                    result.data.to_json(output_path)
            else:
                with open(output_path, 'w') as f:
                    json.dump({
                        'success': result.success,
                        'data': result.data,
                        'errors': result.errors,
                        'warnings': result.warnings,
                        'metadata': result.metadata
                    }, f, indent=2)
                    
            self.logger.info(f"Results saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            raise ProcessingError(f"Failed to save results: {e}")
    
    def load_data(self, input_path: Path) -> Any:
        """
        Load data from file.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Loaded data
        """
        try:
            input_path = Path(input_path)
            
            if not input_path.exists():
                raise ValidationError(f"Input file not found: {input_path}")
            
            # Determine format based on file extension
            if input_path.suffix == '.csv':
                return pd.read_csv(input_path)
            elif input_path.suffix == '.json':
                return pd.read_json(input_path)
            else:
                with open(input_path, 'r') as f:
                    return json.load(f)
                    
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise ProcessingError(f"Failed to load data: {e}")