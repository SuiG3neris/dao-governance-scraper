# src/utils/extraction_utils.py

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
import re
from datetime import datetime
import json

import pandas as pd
import numpy as np
from PIL import Image
import pytesseract
import pdfplumber
import PyPDF2
from docx import Document
import cv2
import numpy as np
from pdf2image import convert_from_path
import tabula
from openpyxl import load_workbook

@dataclass
class TableData:
    """Container for extracted table data."""
    headers: List[str]
    rows: List[List[Any]]
    page_number: Optional[int] = None
    table_number: Optional[int] = None
    metadata: Optional[Dict] = None

class TextExtractor:
    """Utilities for text extraction from various sources."""
    
    @staticmethod
    def extract_from_pdf(file_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF.
        
        Args:
            file_path: Path to PDF file
            **kwargs: Additional extraction options
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            result = {
                'text': [],
                'tables': [],
                'images': [],
                'metadata': {}
            }
            
            # Extract text using PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                result['metadata'] = {
                    'pages': len(reader.pages),
                    'encrypted': reader.is_encrypted,
                    'size': file_path.stat().st_size
                }
                
                for page in reader.pages:
                    result['text'].append(page.extract_text())
            
            # Use pdfplumber for better text extraction if needed
            if not "".join(result['text']).strip():
                with pdfplumber.open(file_path) as pdf:
                    result['text'] = [page.extract_text() for page in pdf.pages]
            
            # Extract tables if requested
            if kwargs.get('extract_tables', True):
                result['tables'] = TextExtractor.extract_tables_from_pdf(file_path)
            
            # Extract images if requested
            if kwargs.get('extract_images', True):
                result['images'] = TextExtractor.extract_images_from_pdf(file_path)
                
            return result
            
        except Exception as e:
            logging.error(f"PDF extraction error: {str(e)}")
            raise
    
    @staticmethod
    def extract_tables_from_pdf(file_path: Path) -> List[TableData]:
        """
        Extract tables from PDF using multiple methods.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of TableData objects
        """
        tables = []
        
        try:
            # Try tabula-py first
            df_list = tabula.read_pdf(str(file_path), pages='all')
            for i, df in enumerate(df_list):
                if not df.empty:
                    tables.append(TableData(
                        headers=df.columns.tolist(),
                        rows=df.values.tolist(),
                        table_number=i + 1
                    ))
            
            # If no tables found, try pdfplumber
            if not tables:
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        for i, table in enumerate(page.extract_tables(), 1):
                            if table:
                                headers = table[0]
                                rows = table[1:]
                                tables.append(TableData(
                                    headers=headers,
                                    rows=rows,
                                    page_number=page_num,
                                    table_number=i
                                ))
                                
            return tables
            
        except Exception as e:
            logging.error(f"Table extraction error: {str(e)}")
            return []
    
    @staticmethod
    def extract_images_from_pdf(file_path: Path) -> List[Dict[str, Any]]:
        """
        Extract images from PDF.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of dictionaries containing image data and metadata
        """
        images = []
        try:
            # Convert PDF pages to images
            pdf_images = convert_from_path(file_path)
            
            for i, image in enumerate(pdf_images):
                # Save image temporarily
                temp_path = Path(f"/tmp/page_{i+1}.png")
                image.save(temp_path)
                
                # Extract text from image using OCR
                text = pytesseract.image_to_string(image)
                
                images.append({
                    'page': i + 1,
                    'size': image.size,
                    'mode': image.mode,
                    'path': str(temp_path),
                    'extracted_text': text
                })
                
            return images
            
        except Exception as e:
            logging.error(f"Image extraction error: {str(e)}")
            return []

    @staticmethod
    def extract_from_image(file_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Extract text and data from image using OCR.
        
        Args:
            file_path: Path to image file
            **kwargs: OCR options
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            image = Image.open(file_path)
            
            # Preprocess image if needed
            if kwargs.get('preprocess', True):
                # Convert to OpenCV format
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Apply preprocessing
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                denoised = cv2.fastNlMeansDenoising(gray)
                threshold = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                
                # Convert back to PIL Image
                image = Image.fromarray(threshold)
            
            # Perform OCR
            text = pytesseract.image_to_string(
                image,
                lang=kwargs.get('lang', 'eng'),
                config=kwargs.get('config', '')
            )
            
            # Get image metadata
            metadata = {
                'size': image.size,
                'mode': image.mode,
                'format': image.format,
                'dpi': image.info.get('dpi')
            }
            
            return {
                'text': text,
                'metadata': metadata
            }
            
        except Exception as e:
            logging.error(f"Image extraction error: {str(e)}")
            raise

class DataStructureDetector:
    """Utilities for detecting and extracting structured data."""
    
    @staticmethod
    def detect_tables(text: str) -> List[Dict[str, Any]]:
        """
        Detect potential tables in text.
        
        Args:
            text: Input text
            
        Returns:
            List of detected table structures
        """
        tables = []
        
        # Look for common table patterns
        patterns = [
            r'[\|\+][-\+]+[\|\+]',  # ASCII table borders
            r'\b\w+\s*\|\s*\w+\s*\|',  # Pipe-separated values
            r'^\s*\w+\t+\w+\t+\w+',  # Tab-separated values
            r'^\s*\w+\s{2,}\w+\s{2,}\w+'  # Space-aligned columns
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                # Extract and analyze the potential table region
                table_text = TextExtractor._extract_table_region(text, match.start())
                if table_text:
                    structure = DataStructureDetector._analyze_table_structure(table_text)
                    if structure:
                        tables.append(structure)
        
        return tables
    
    @staticmethod
    def _extract_table_region(text: str, start_pos: int) -> Optional[str]:
        """Extract complete table region from text."""
        lines = text[start_pos:].split('\n')
        table_lines = []
        
        for line in lines:
            if not line.strip():
                if table_lines:
                    break
            else:
                table_lines.append(line)
                
        return '\n'.join(table_lines) if table_lines else None
    
    @staticmethod
    def _analyze_table_structure(table_text: str) -> Optional[Dict[str, Any]]:
        """Analyze and extract table structure."""
        lines = table_text.split('\n')
        if len(lines) < 2:
            return None
            
        # Try to detect delimiter
        delimiters = ['|', '\t', ',']
        delimiter = None
        max_parts = 0
        
        for d in delimiters:
            parts = len(lines[0].split(d))
            if parts > max_parts:
                max_parts = parts
                delimiter = d
                
        if not delimiter:
            return None
            
        # Parse table
        rows = [line.split(delimiter) for line in lines]
        headers = [col.strip() for col in rows[0]]
        data = [[col.strip() for col in row] for row in rows[1:]]
        
        return {
            'type': 'table',
            'delimiter': delimiter,
            'headers': headers,
            'data': data,
            'rows': len(data),
            'columns': len(headers)
        }

class FormatConverter:
    """Utilities for converting between different data formats."""
    
    @staticmethod
    def table_to_dataframe(table_data: TableData) -> pd.DataFrame:
        """Convert TableData to pandas DataFrame."""
        return pd.DataFrame(table_data.rows, columns=table_data.headers)
    
    @staticmethod
    def table_to_json(table_data: TableData) -> str:
        """Convert TableData to JSON string."""
        data = {
            'headers': table_data.headers,
            'rows': table_data.rows,
            'metadata': table_data.metadata
        }
        return json.dumps(data)
    
    @staticmethod
    def dataframe_to_table(df: pd.DataFrame) -> TableData:
        """Convert pandas DataFrame to TableData."""
        return TableData(
            headers=df.columns.tolist(),
            rows=df.values.tolist()
        )
    
    @staticmethod
    def structure_for_claude(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure data in Claude-friendly format.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Restructured data suitable for Claude analysis
        """
        structured = {
            'content': {
                'text': data.get('text', ''),
                'tables': [],
                'metadata': data.get('metadata', {})
            },
            'analysis_hints': {
                'document_type': data.get('type', 'unknown'),
                'content_structure': [],
                'key_elements': []
            }
        }
        
        # Add tables in a structured format
        if 'tables' in data:
            for table in data['tables']:
                structured['content']['tables'].append({
                    'headers': table.headers,
                    'data': table.rows,
                    'metadata': table.metadata
                })
        
        # Detect content structure
        if isinstance(data.get('text'), str):
            # Detect sections
            sections = re.split(r'\n\s*#{1,6}\s+', data['text'])
            structured['analysis_hints']['content_structure'] = [
                {'type': 'section', 'count': len(sections)}
            ]
            
            # Detect lists
            list_items = re.findall(r'^\s*[-*]\s+.+$', data['text'], re.MULTILINE)
            if list_items:
                structured['analysis_hints']['content_structure'].append(
                    {'type': 'list', 'count': len(list_items)}
                )
        
        return structured