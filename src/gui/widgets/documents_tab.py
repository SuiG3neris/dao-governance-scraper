# src/gui/widgets/documents_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QProgressBar, QFileDialog,
    QTreeView, QTextEdit, QComboBox, QGroupBox,
    QFormLayout, QSpinBox, QCheckBox, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QDropEvent, QDragEnterEvent

import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from ...document_processing.document_processor import BatchProcessor, ProcessingResult, FileType
from ..utils import show_error_dialog, show_info_dialog

class FileDropArea(QWidget):
    """Custom widget for drag and drop file upload."""
    
    files_dropped = pyqtSignal(list)  # List of file paths
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI."""
        self.setAcceptDrops(True)
        self.setMinimumSize(QSize(300, 200))
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel("Drop files here or click to browse")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        self.setStyleSheet("""
            FileDropArea {
                border: 2px dashed #999;
                border-radius: 5px;
                background-color: #f0f0f0;
            }
            FileDropArea:hover {
                border-color: #666;
                background-color: #e0e0e0;
            }
        """)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                FileDropArea {
                    border: 2px dashed #333;
                    background-color: #e0e0e0;
                }
            """)
            
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self.setStyleSheet("""
            FileDropArea {
                border: 2px dashed #999;
                background-color: #f0f0f0;
            }
        """)
        
    def dropEvent(self, event: QDropEvent):
        """Handle file drop event."""
        file_paths = []
        for url in event.mimeData().urls():
            file_paths.append(Path(url.toLocalFile()))
        self.files_dropped.emit(file_paths)
        self.setStyleSheet("""
            FileDropArea {
                border: 2px dashed #999;
                background-color: #f0f0f0;
            }
        """)
        
    def mousePressEvent(self, event):
        """Handle click to browse files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            str(Path.home()),
            "All Files (*.*)"
        )
        if files:
            self.files_dropped.emit([Path(f) for f in files])

class FileTreeView(QTreeView):
    """Tree view for displaying project files and their status."""
    
    file_selected = pyqtSignal(Path)  # Emitted when a file is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['File', 'Type', 'Status', 'Size'])
        self.setModel(self.model)
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.clicked.connect(self._handle_click)
        
    def add_file(self, file_path: Path, file_type: str, status: str = "Pending"):
        """Add a file to the tree view."""
        file_item = QStandardItem(file_path.name)
        type_item = QStandardItem(file_type)
        status_item = QStandardItem(status)
        size_item = QStandardItem(self._format_size(file_path.stat().st_size))
        
        self.model.appendRow([file_item, type_item, status_item, size_item])
        
    def update_status(self, file_path: Path, status: str):
        """Update the status of a file."""
        for row in range(self.model.rowCount()):
            if self.model.item(row, 0).text() == file_path.name:
                self.model.item(row, 2).setText(status)
                break
                
    def _handle_click(self, index):
        """Handle item click."""
        file_name = self.model.item(index.row(), 0).text()
        self.file_selected.emit(Path(file_name))
        
    def _format_size(self, size: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

class PreviewPanel(QWidget):
    """Panel for previewing document contents and extraction results."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Add tabs for different views
        self.tab_widget = QTabWidget()
        
        # Text preview
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.tab_widget.addTab(self.text_preview, "Text")
        
        # Structured data preview
        self.data_preview = QTextEdit()
        self.data_preview.setReadOnly(True)
        self.tab_widget.addTab(self.data_preview, "Data")
        
        # Metadata view
        self.metadata_view = QTextEdit()
        self.metadata_view.setReadOnly(True)
        self.tab_widget.addTab(self.metadata_view, "Metadata")
        
        layout.addWidget(self.tab_widget)
        
    def show_preview(self, result: ProcessingResult):
        """Show preview of processing result."""
        if not result.success:
            self.text_preview.setText(f"Error: {result.error_message}")
            return
            
        # Show extracted text
        if result.extracted_text:
            self.text_preview.setText(result.extracted_text)
            
        # Show structured data
        if result.extracted_data:
            self.data_preview.setText(str(result.extracted_data))
            
        # Show metadata
        if result.metadata:
            metadata_text = "\n".join(f"{k}: {v}" for k, v in result.metadata.items())
            self.metadata_view.setText(metadata_text)

class ProcessingOptions(QGroupBox):
    """Widget for configuring processing options."""
    
    options_changed = pyqtSignal(dict)  # Emitted when options change
    
    def __init__(self, parent=None):
        super().__init__("Processing Options", parent)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI."""
        layout = QFormLayout(self)
        
        # OCR language selection
        self.ocr_lang = QComboBox()
        self.ocr_lang.addItems(['eng', 'fra', 'deu', 'spa'])
        layout.addRow("OCR Language:", self.ocr_lang)
        
        # PDF processing options
        self.extract_images = QCheckBox("Extract Images from PDFs")
        self.extract_images.setChecked(True)
        layout.addRow(self.extract_images)
        
        # Table extraction options
        self.extract_tables = QCheckBox("Extract Tables")
        self.extract_tables.setChecked(True)
        layout.addRow(self.extract_tables)
        
        # Batch size
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 100)
        self.batch_size.setValue(10)
        layout.addRow("Batch Size:", self.batch_size)
        
        # Connect signals
        self.ocr_lang.currentTextChanged.connect(self._emit_options)
        self.extract_images.stateChanged.connect(self._emit_options)
        self.extract_tables.stateChanged.connect(self._emit_options)
        self.batch_size.valueChanged.connect(self._emit_options)
        
    def _emit_options(self):
        """Emit current options."""
        options = {
            'ocr_language': self.ocr_lang.currentText(),
            'extract_images': self.extract_images.isChecked(),
            'extract_tables': self.extract_tables.isChecked(),
            'batch_size': self.batch_size.value()
        }
        self.options_changed.emit(options)

class DocumentsTab(QWidget):
    """Main documents tab widget."""
    
    def __init__(self, config: Dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.batch_processor = BatchProcessor(config)
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - File management
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Drop area
        self.drop_area = FileDropArea()
        left_layout.addWidget(self.drop_area)
        
        # File tree
        self.file_tree = FileTreeView()
        left_layout.addWidget(self.file_tree)
        
        # Processing controls
        controls_layout = QHBoxLayout()
        
        self.process_btn = QPushButton("Process Files")
        self.process_btn.clicked.connect(self._start_processing)
        controls_layout.addWidget(self.process_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_files)
        controls_layout.addWidget(self.clear_btn)
        
        left_layout.addLayout(controls_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Preview and options
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Processing options
        self.options = ProcessingOptions()
        right_layout.addWidget(self.options)
        
        # Preview
        self.preview = PreviewPanel()
        right_layout.addWidget(self.preview)
        
        splitter.addWidget(right_panel)
        
        # Add splitter to main layout
        layout.addWidget(splitter)
        
    def _connect_signals(self):
        """Connect signals and slots."""
        # File handling signals
        self.drop_area.files_dropped.connect(self._handle_dropped_files)
        self.file_tree.file_selected.connect(self._handle_file_selected)
        
        # Batch processor signals
        self.batch_processor.progress.connect(self._update_progress)
        self.batch_processor.file_complete.connect(self._handle_file_complete)
        self.batch_processor.batch_complete.connect(self._handle_batch_complete)
        self.batch_processor.error.connect(self._handle_error)
        
        # Options signals
        self.options.options_changed.connect(self._update_processing_options)
        
    def _handle_dropped_files(self, file_paths: List[Path]):
        """Handle dropped files."""
        for path in file_paths:
            try:
                file_type = FileType(path.suffix.lower()[1:]).value
                self.file_tree.add_file(path, file_type)
            except ValueError:
                show_error_dialog(self, f"Unsupported file type: {path.suffix}")
                
    def _handle_file_selected(self, file_path: Path):
        """Handle file selection."""
        pass  # TODO: Implement file preview
        
    def _start_processing(self):
        """Start batch processing."""
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.batch_processor.start()
        
    def _clear_files(self):
        """Clear all files."""
        self.file_tree.model.clear()
        self.file_tree.model.setHorizontalHeaderLabels(['File', 'Type', 'Status', 'Size'])
        self.preview.text_preview.clear()
        self.preview.data_preview.clear()
        self.preview.metadata_view.clear()
        
    def _update_progress(self, progress: int):
        """Update progress bar."""
        self.progress_bar.setValue(progress)
        
    def _handle_file_complete(self, file_path: str, result: ProcessingResult):
        """Handle completed file processing."""
        path = Path(file_path)
        status = "Complete" if result.success else "Failed"
        self.file_tree.update_status(path, status)
        
    def _handle_batch_complete(self, results: List[ProcessingResult]):
        """Handle batch processing completion."""
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        show_info_dialog(self, f"Processed {len(results)} files")
        
    def _handle_error(self, error_msg: str):
        """Handle processing error."""
        show_error_dialog(self, f"Processing error: {error_msg}")
        self.process_btn.setEnabled(True)
        
    def _update_processing_options(self, options: Dict):
        """Update processing options."""
        self.batch_processor.config.update(options)