# src/gui/widgets/data_preview.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView,
    QPushButton, QComboBox, QHBoxLayout,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem

from ..utils import show_error_dialog, show_info_dialog, set_table_style

class DataPreviewWidget(QWidget):
    """Widget for previewing scraped data."""
    
    refresh_requested = pyqtSignal(str)  # Emitted when refresh is requested for a table
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QStandardItemModel()
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.table_selector = QComboBox()
        self.table_selector.addItems(["Spaces", "Proposals", "Votes"])
        self.table_selector.currentTextChanged.connect(self._on_table_changed)
        controls_layout.addWidget(self.table_selector)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        controls_layout.addWidget(self.refresh_button)
        
        # Add stretch to push controls to the left
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        set_table_style(self.table_view)
        layout.addWidget(self.table_view)
        
    def _on_table_changed(self, table_name: str):
        """Handle table selection change."""
        self.refresh_requested.emit(table_name.lower())
        
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        current_table = self.table_selector.currentText().lower()
        self.refresh_requested.emit(current_table)
        
    def show_loading(self, show: bool = True):
        """Show/hide loading progress bar."""
        self.progress_bar.setVisible(show)
        if show:
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
        
    def update_data(self, headers: list, data: list):
        """
        Update table with new data.
        
        Args:
            headers: List of column headers
            data: List of data rows
        """
        self.model.clear()
        
        # Set headers
        self.model.setHorizontalHeaderLabels(headers)
        
        # Add data rows
        for row_data in data:
            row = []
            for item in row_data:
                cell = QStandardItem(str(item))
                cell.setEditable(False)
                row.append(cell)
            self.model.appendRow(row)
            
        # Resize columns to content
        self.table_view.resizeColumnsToContents()
        
    def clear(self):
        """Clear the table view."""
        self.model.clear()