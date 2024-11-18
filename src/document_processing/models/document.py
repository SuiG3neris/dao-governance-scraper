# src/document_processing/models/document.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import mimetypes
import hashlib

@dataclass
class DocumentMetadata:
    """Metadata for a document."""
    filename: str
    file_type: str
    size: int
    created_at: datetime
    modified_at: datetime
    mime_type: str
    encoding: Optional[str] = None
    hash: Optional[str] = None
    pages: Optional[int] = None
    author: Optional[str] = None
    title: Optional[str] = None
    language: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TableData:
    """Structured table data extracted from a document."""
    headers: List[str]
    rows: List[List[Any]]
    page_number: Optional[int] = None
    table_number: Optional[int] = None
    metadata: Optional[Dict] = None

@dataclass
class ExtractedContent:
    """Container for extracted document content."""
    text: str
    tables: List[TableData] = field(default_factory=list)
    metadata: DocumentMetadata = None
    sections: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    language: Optional[str] = None
    structure: Dict[str, Any] = field(default_factory=dict)
    raw_content: Any = None

@dataclass
class ProcessingOptions:
    """Options for document processing."""
    extract_tables: bool = True
    extract_images: bool = False
    ocr_enabled: bool = False
    ocr_language: str = 'eng'
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    timeout: int = 300  # seconds
    batch_size: int = 10
    supported_formats: List[str] = field(default_factory=lambda: [
        'application/pdf',
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'image/jpeg',
        'image/png'
    ])

@dataclass
class Document:
    """
    Represents a document with its content and metadata.
    
    This is the main document model that combines metadata,
    extracted content, and processing state.
    """
    path: Path
    metadata: DocumentMetadata
    content: Optional[ExtractedContent] = None
    processing_errors: List[str] = field(default_factory=list)
    processing_warnings: List[str] = field(default_factory=list)
    processing_options: ProcessingOptions = field(default_factory=ProcessingOptions)
    processing_status: str = 'new'  # new, processing, completed, failed
    processed_at: Optional[datetime] = None
    
    @classmethod
    def from_file(cls, file_path: Path, options: Optional[ProcessingOptions] = None) -> 'Document':
        """Create a Document instance from a file path."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Get file stats
        stats = file_path.stat()
        
        # Detect mime type
        mime_type, encoding = mimetypes.guess_type(str(file_path))
        
        # Calculate file hash
        file_hash = cls._calculate_file_hash(file_path)
        
        # Create metadata
        metadata = DocumentMetadata(
            filename=file_path.name,
            file_type=file_path.suffix.lower()[1:],
            size=stats.st_size,
            created_at=datetime.fromtimestamp(stats.st_ctime),
            modified_at=datetime.fromtimestamp(stats.st_mtime),
            mime_type=mime_type or 'application/octet-stream',
            encoding=encoding,
            hash=file_hash
        )
        
        return cls(
            path=file_path,
            metadata=metadata,
            processing_options=options or ProcessingOptions()
        )
    
    @staticmethod
    def _calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
        """Calculate SHA-256 hash of file."""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
                
        return sha256.hexdigest()
    
    def validate(self) -> bool:
        """Validate document against processing options."""
        # Check file size
        if self.metadata.size > self.processing_options.max_file_size:
            self.processing_errors.append(
                f"File size {self.metadata.size} exceeds limit "
                f"{self.processing_options.max_file_size}"
            )
            return False
            
        # Check mime type
        if self.metadata.mime_type not in self.processing_options.supported_formats:
            self.processing_errors.append(
                f"Unsupported file type: {self.metadata.mime_type}"
            )
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary representation."""
        return {
            'path': str(self.path),
            'metadata': {
                'filename': self.metadata.filename,
                'file_type': self.metadata.file_type,
                'size': self.metadata.size,
                'created_at': self.metadata.created_at.isoformat(),
                'modified_at': self.metadata.modified_at.isoformat(),
                'mime_type': self.metadata.mime_type,
                'encoding': self.metadata.encoding,
                'hash': self.metadata.hash,
                'pages': self.metadata.pages,
                'author': self.metadata.author,
                'title': self.metadata.title,
                'language': self.metadata.language,
                'raw_metadata': self.metadata.raw_metadata
            },
            'content': {
                'text': self.content.text if self.content else None,
                'tables': [
                    {
                        'headers': table.headers,
                        'rows': table.rows,
                        'page_number': table.page_number,
                        'table_number': table.table_number,
                        'metadata': table.metadata
                    }
                    for table in (self.content.tables if self.content else [])
                ],
                'sections': self.content.sections if self.content else [],
                'images': self.content.images if self.content else [],
                'links': self.content.links if self.content else [],
                'language': self.content.language if self.content else None,
                'structure': self.content.structure if self.content else {}
            } if self.content else None,
            'processing_errors': self.processing_errors,
            'processing_warnings': self.processing_warnings,
            'processing_status': self.processing_status,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document instance from dictionary representation."""
        metadata = DocumentMetadata(
            filename=data['metadata']['filename'],
            file_type=data['metadata']['file_type'],
            size=data['metadata']['size'],
            created_at=datetime.fromisoformat(data['metadata']['created_at']),
            modified_at=datetime.fromisoformat(data['metadata']['modified_at']),
            mime_type=data['metadata']['mime_type'],
            encoding=data['metadata']['encoding'],
            hash=data['metadata']['hash'],
            pages=data['metadata']['pages'],
            author=data['metadata']['author'],
            title=data['metadata']['title'],
            language=data['metadata']['language'],
            raw_metadata=data['metadata']['raw_metadata']
        )
        
        content = None
        if data.get('content'):
            tables = [
                TableData(
                    headers=t['headers'],
                    rows=t['rows'],
                    page_number=t['page_number'],
                    table_number=t['table_number'],
                    metadata=t['metadata']
                )
                for t in data['content'].get('tables', [])
            ]
            
            content = ExtractedContent(
                text=data['content']['text'],
                tables=tables,
                metadata=metadata,
                sections=data['content']['sections'],
                images=data['content']['images'],
                links=data['content']['links'],
                language=data['content']['language'],
                structure=data['content']['structure']
            )
        
        return cls(
            path=Path(data['path']),
            metadata=metadata,
            content=content,
            processing_errors=data['processing_errors'],
            processing_warnings=data['processing_warnings'],
            processing_status=data['processing_status'],
            processed_at=datetime.fromisoformat(data['processed_at']) 
                if data.get('processed_at') else None
        )
    