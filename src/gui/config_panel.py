"""
Configuration panel widget for managing scraper settings.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QPushButton, QFileDialog,
    QLabel, QGroupBox, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from .utils import show_error_dialog, show_info_dialog

class ConfigurationPanel(QWidget):
    """Widget for managing scraper configuration."""
    
    config_updated = pyqtSignal(dict)  # Emitted when configuration is updated
    
    def __init__(self, initial_config: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = initial_config.copy()
        self.setup_ui()
        self.load_config(self.config)
        
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Snapshot.org Settings
        snapshot_group = QGroupBox("Snapshot.org Settings")
        snapshot_layout = QFormLayout()
        
        self.snapshot_endpoint = QLineEdit()
        self.snapshot_batch_size = QSpinBox()
        self.snapshot_batch_size.setRange(100, 10000)
        self.snapshot_batch_size.setSingleStep(100)
        
        self.snapshot_rate_limit = QSpinBox()
        self.snapshot_rate_limit.setRange(1, 100)
        
        # Enable verbose logging checkbox
        self.verbose_logging = QCheckBox("Enable Verbose Logging")
        
        snapshot_layout.addRow("API Endpoint:", self.snapshot_endpoint)
        snapshot_layout.addRow("Batch Size:", self.snapshot_batch_size)
        snapshot_layout.addRow("Rate Limit (req/min):", self.snapshot_rate_limit)
        snapshot_layout.addRow(self.verbose_logging)
        snapshot_group.setLayout(snapshot_layout)
        layout.addWidget(snapshot_group)
        
        # Database Settings
        database_group = QGroupBox("Database Settings")
        database_layout = QFormLayout()
        
        self.db_path = QLineEdit()
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_db_path)
        
        db_path_layout = QHBoxLayout()
        db_path_layout.addWidget(self.db_path)
        db_path_layout.addWidget(browse_button)
        
        self.pool_size = QSpinBox()
        self.pool_size.setRange(1, 20)
        
        # Database maintenance options
        self.auto_vacuum = QCheckBox("Enable Auto-Vacuum")
        self.auto_backup = QCheckBox("Enable Auto-Backup")
        
        database_layout.addRow("Database Path:", db_path_layout)
        database_layout.addRow("Connection Pool Size:", self.pool_size)
        database_layout.addRow(self.auto_vacuum)
        database_layout.addRow(self.auto_backup)
        database_group.setLayout(database_layout)
        layout.addWidget(database_group)
        
        # Storage Settings
        storage_group = QGroupBox("Storage Settings")
        storage_layout = QFormLayout()
        
        self.raw_data_path = QLineEdit()
        self.processed_data_path = QLineEdit()
        
        raw_browse = QPushButton("Browse...")
        processed_browse = QPushButton("Browse...")
        raw_browse.clicked.connect(lambda: self.browse_path(self.raw_data_path))
        processed_browse.clicked.connect(lambda: self.browse_path(self.processed_data_path))
        
        raw_path_layout = QHBoxLayout()
        raw_path_layout.addWidget(self.raw_data_path)
        raw_path_layout.addWidget(raw_browse)
        
        processed_path_layout = QHBoxLayout()
        processed_path_layout.addWidget(self.processed_data_path)
        processed_path_layout.addWidget(processed_browse)
        
        storage_layout.addRow("Raw Data Path:", raw_path_layout)
        storage_layout.addRow("Processed Data Path:", processed_path_layout)
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Configuration")
        self.reset_button = QPushButton("Reset to Defaults")
        
        self.save_button.clicked.connect(self.save_config)
        self.reset_button.clicked.connect(self.reset_config)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)
        
        # Add stretch to bottom
        layout.addStretch()
        
    def load_config(self, config: Dict[str, Any]):
        """Load configuration into UI elements."""
        # Snapshot settings
        snapshot_config = config.get('scraping', {}).get('snapshot', {})
        self.snapshot_endpoint.setText(snapshot_config.get('api_endpoint', ''))
        self.snapshot_batch_size.setValue(snapshot_config.get('batch_size', 1000))
        self.snapshot_rate_limit.setValue(
            config.get('scraping', {}).get('rate_limit', {}).get('requests_per_minute', 30)
        )
        
        # Database settings
        db_config = config.get('database', {})
        self.db_path.setText(db_config.get('path', ''))
        self.pool_size.setValue(
            db_config.get('connection', {}).get('pool_size', 5)
        )
        
        # Storage settings
        storage_config = config.get('storage', {})
        self.raw_data_path.setText(storage_config.get('raw_data_path', ''))
        self.processed_data_path.setText(storage_config.get('processed_data_path', ''))
        
        # Logging settings
        self.verbose_logging.setChecked(
            config.get('logging', {}).get('level', '') == 'DEBUG'
        )
        
    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration from UI elements."""
        return {
            'scraping': {
                'rate_limit': {
                    'requests_per_minute': self.snapshot_rate_limit.value()
                },
                'snapshot': {
                    'api_endpoint': self.snapshot_endpoint.text(),
                    'batch_size': self.snapshot_batch_size.value()
                }
            },
            'database': {
                'path': self.db_path.text(),
                'connection': {
                    'pool_size': self.pool_size.value()
                }
            },
            'storage': {
                'raw_data_path': self.raw_data_path.text(),
                'processed_data_path': self.processed_data_path.text()
            },
            'logging': {
                'level': 'DEBUG' if self.verbose_logging.isChecked() else 'INFO'
            }
        }
        
    @pyqtSlot()
    def browse_db_path(self):
        """Open file dialog to select database path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Database Location",
            self.db_path.text(),
            "SQLite Database (*.db);;All Files (*.*)"
        )
        
        if file_path:
            self.db_path.setText(file_path)
            
    def browse_path(self, line_edit: QLineEdit):
        """Open directory dialog to select path."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            line_edit.text()
        )
        
        if dir_path:
            line_edit.setText(dir_path)
            
    @pyqtSlot()
    def save_config(self):
        """Save the current configuration."""
        try:
            config = self.get_current_config()
            
            # Validate configuration
            if not config['scraping']['snapshot']['api_endpoint']:
                raise ValueError("Snapshot API endpoint is required")
                
            if not config['database']['path']:
                raise ValueError("Database path is required")
                
            # Save to file
            config_path = Path('config/config.yaml')
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
                
            self.config_updated.emit(config)
            show_info_dialog(self, "Success", "Configuration saved successfully")
            
        except Exception as e:
            show_error_dialog(self, "Error", f"Failed to save configuration: {str(e)}")
            
    @pyqtSlot()
    def reset_config(self):
        """Reset configuration to initial values."""
        self.load_config(self.config)