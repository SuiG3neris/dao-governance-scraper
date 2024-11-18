# src/document_processing/__init__.py
"""
DAO Analyzer document processing module.
Provides infrastructure for extracting and processing content from various document types.
"""

from .document_processor import (
    DocumentProcessor,
    ProcessingResult,
    DocumentType,
    ProcessingError,
    ValidationError,
    ExtractionError
)

from .processors import (
    PDFProcessor,
    CSVProcessor,
    ExcelProcessor,
    TextProcessor,
    ImageProcessor
)

from .extractors import (
    TextExtractor,
    TableExtractor,
    MetadataExtractor,
    ContentStructureDetector
)

from .models import (
    Document,
    ExtractedContent,
    TableData,
    DocumentMetadata,
    ProcessingOptions
)

from .utils import (
    FileValidator,
    FormatConverter,
    OCRHelper,
    DocumentCleaner
)

__all__ = [
    # Core processor
    'DocumentProcessor',
    'ProcessingResult',
    'DocumentType',
    'ProcessingError',
    'ValidationError',
    'ExtractionError',
    
    # Specialized processors
    'PDFProcessor',
    'CSVProcessor',
    'ExcelProcessor',
    'TextProcessor',
    'ImageProcessor',
    
    # Extractors
    'TextExtractor',
    'TableExtractor',
    'MetadataExtractor',
    'ContentStructureDetector',
    
    # Models
    'Document',
    'ExtractedContent', 
    'TableData',
    'DocumentMetadata',
    'ProcessingOptions',
    
    # Utilities
    'FileValidator',
    'FormatConverter',
    'OCRHelper',
    'DocumentCleaner'
]