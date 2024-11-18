# src/gui/widgets/config_panel.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QFormLayout, QMessageBox, QComboBox,
    QGroupBox, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
import yaml
from pathlib import Path
from typing import Dict, Any

class ConfigurationPanel(QWidget):
    """Widget for managing application configuration settings."""
    
    # Signal emitted when configuration is updated
    config_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_path = Path("config/config.yaml")
        self.current_config = {}
        self._init_ui()
        self.load_config()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different configuration sections
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Add configuration tabs
        self.scraping_tab = self._create_scraping_tab()
        self.tab_widget.addTab(self.scraping_tab, "Scraping")
        
        self.database_tab = self._create_database_tab()
        self.tab_widget.addTab(self.database_tab, "Database")
        
        self.logging_tab = self._create_logging_tab()
        self.tab_widget.addTab(self.logging_tab, "Logging")
        
        self.storage_tab = self._create_storage_tab()
        self.tab_widget.addTab(self.storage_tab, "Storage")
        
        # Add buttons for save/reload
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save Configuration")
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)
        
        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.load_config)
        button_layout.addWidget(self.reload_button)
        
        layout.addLayout(button_layout)
        
    def _create_scraping_tab(self) -> QWidget:
        """Create the scraping configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Rate limiting group
        rate_group = QGroupBox("Rate Limiting")
        rate_layout = QFormLayout(rate_group)
        
        self.requests_per_minute = QSpinBox()
        self.requests_per_minute.setRange(1, 100)
        rate_layout.addRow("Requests per minute:", self.requests_per_minute)
        
        self.delay_between_requests = QDoubleSpinBox()
        self.delay_between_requests.setRange(0.1, 10.0)
        self.delay_between_requests.setSingleStep(0.1)
        rate_layout.addRow("Delay between requests (s):", self.delay_between_requests)
        
        layout.addWidget(rate_group)
        
        # Snapshot API group
        snapshot_group = QGroupBox("Snapshot.org API")
        snapshot_layout = QFormLayout(snapshot_group)
        
        self.api_endpoint = QLineEdit()
        snapshot_layout.addRow("API Endpoint:", self.api_endpoint)
        
        self.batch_size = QSpinBox()
        self.batch_size.setRange(100, 5000)
        self.batch_size.setSingleStep(100)
        snapshot_layout.addRow("Batch size:", self.batch_size)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 10)
        snapshot_layout.addRow("Max retries:", self.max_retries)
        
        layout.addWidget(snapshot_group)
        
        return widget
        
    def _create_database_tab(self) -> QWidget:
        """Create the database configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Database connection group
        db_group = QGroupBox("Database Connection")
        db_layout = QFormLayout(db_group)
        
        self.db_type = QComboBox()
        self.db_type.addItems(["sqlite"])  # Add more if supported
        db_layout.addRow("Database type:", self.db_type)
        
        self.db_path = QLineEdit()
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_db_path)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.db_path)
        path_layout.addWidget(browse_button)
        db_layout.addRow("Database path:", path_layout)
        
        layout.addWidget(db_group)
        
        # Connection pool group
        pool_group = QGroupBox("Connection Pool")
        pool_layout = QFormLayout(pool_group)
        
        self.pool_size = QSpinBox()
        self.pool_size.setRange(1, 20)
        pool_layout.addRow("Pool size:", self.pool_size)
        
        self.max_overflow = QSpinBox()
        self.max_overflow.setRange(0, 50)
        pool_layout.addRow("Max overflow:", self.max_overflow)
        
        layout.addWidget(pool_group)
        
        return widget
        
    def _create_logging_tab(self) -> QWidget:
        """Create the logging configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logging settings group
        log_group = QGroupBox("Logging Settings")
        log_layout = QFormLayout(log_group)
        
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        log_layout.addRow("Log level:", self.log_level)
        
        self.log_file = QLineEdit()
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_log_path)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.log_file)
        path_layout.addWidget(browse_button)
        log_layout.addRow("Log file:", path_layout)
        
        layout.addWidget(log_group)
        
        # Rotation settings group
        rotation_group = QGroupBox("Log Rotation")
        rotation_layout = QFormLayout(rotation_group)
        
        self.max_bytes = QSpinBox()
        self.max_bytes.setRange(1, 100)
        self.max_bytes.setSuffix(" MB")
        rotation_layout.addRow("Max file size:", self.max_bytes)
        
        self.backup_count = QSpinBox()
        self.backup_count.setRange(1, 20)
        rotation_layout.addRow("Backup count:", self.backup_count)
        
        layout.addWidget(rotation_group)
        
        return widget
        
    def _create_storage_tab(self) -> QWidget:
        """Create the storage configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Storage paths group
        paths_group = QGroupBox("Storage Paths")
        paths_layout = QFormLayout(paths_group)
        
        self.raw_data_path = QLineEdit()
        raw_browse = QPushButton("Browse...")
        raw_browse.clicked.connect(lambda: self._browse_directory(self.raw_data_path))
        
        raw_layout = QHBoxLayout()
        raw_layout.addWidget(self.raw_data_path)
        raw_layout.addWidget(raw_browse)
        paths_layout.addRow("Raw data path:", raw_layout)
        
        self.processed_data_path = QLineEdit()
        processed_browse = QPushButton("Browse...")
        processed_browse.clicked.connect(lambda: self._browse_directory(self.processed_data_path))
        
        processed_layout = QHBoxLayout()
        processed_layout.addWidget(self.processed_data_path)
        processed_layout.addWidget(processed_browse)
        paths_layout.addRow("Processed data path:", processed_layout)
        
        layout.addWidget(paths_group)
        
        # File format group
        format_group = QGroupBox("File Format")
        format_layout = QFormLayout(format_group)
        
        self.file_format = QComboBox()
        self.file_format.addItems(["json", "csv", "parquet"])
        format_layout.addRow("File format:", self.file_format)
        
        layout.addWidget(format_group)
        
        return widget
    
    def _browse_db_path(self):
        """Open file dialog for database path selection."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Database File",
            str(Path.home()),
            "SQLite Database (*.db);;All Files (*.*)"
        )
        if path:
            self.db_path.setText(path)
            
    def _browse_log_path(self):
        """Open file dialog for log file selection."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File",
            str(Path.home()),
            "Log Files (*.log);;All Files (*.*)"
        )
        if path:
            self.log_file.setText(path)
            
    def _browse_directory(self, line_edit: QLineEdit):
        """Open directory selection dialog."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if path:
            line_edit.setText(path)
            
    def load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self.current_config = yaml.safe_load(f)
                
            # Update UI with loaded values
            scraping = self.current_config.get('scraping', {})
            self.requests_per_minute.setValue(
                scraping.get('rate_limit', {}).get('requests_per_minute', 30)
            )
            self.delay_between_requests.setValue(
                scraping.get('rate_limit', {}).get('delay_between_requests', 2)
            )
            
            snapshot = scraping.get('snapshot', {})
            self.api_endpoint.setText(snapshot.get('api_endpoint', ''))
            self.batch_size.setValue(snapshot.get('batch_size', 1000))
            self.max_retries.setValue(snapshot.get('max_retries', 3))
            
            database = self.current_config.get('database', {})
            self.db_type.setCurrentText(database.get('type', 'sqlite'))
            self.db_path.setText(database.get('path', ''))
            
            connection = database.get('connection', {})
            self.pool_size.setValue(connection.get('pool_size', 5))
            self.max_overflow.setValue(connection.get('max_overflow', 10))
            
            logging_config = self.current_config.get('logging', {})
            self.log_level.setCurrentText(logging_config.get('level', 'INFO'))
            self.log_file.setText(logging_config.get('file', ''))
            
            rotate = logging_config.get('rotate', {})
            self.max_bytes.setValue(rotate.get('max_bytes', 10) // 1048576)  # Convert to MB
            self.backup_count.setValue(rotate.get('backup_count', 5))
            
            storage = self.current_config.get('storage', {})
            self.raw_data_path.setText(storage.get('raw_data_path', ''))
            self.processed_data_path.setText(storage.get('processed_data_path', ''))
            self.file_format.setCurrentText(storage.get('file_format', 'json'))
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Configuration Error",
                f"Error loading configuration: {str(e)}"
            )
            
    def save_config(self):
        """Save configuration to YAML file."""
        try:
            config = {
                'scraping': {
                    'rate_limit': {
                        'requests_per_minute': self.requests_per_minute.value(),
                        'delay_between_requests': self.delay_between_requests.value()
                    },
                    'snapshot': {
                        'api_endpoint': self.api_endpoint.text(),
                        'batch_size': self.batch_size.value(),
                        'max_retries': self.max_retries.value()
                    }
                },
                'database': {
                    'type': self.db_type.currentText(),
                    'path': self.db_path.text(),
                    'connection': {
                        'pool_size': self.pool_size.value(),
                        'max_overflow': self.max_overflow.value()
                    }
                },
                'logging': {
                    'level': self.log_level.currentText(),
                    'file': self.log_file.text(),
                    'rotate': {
                        'max_bytes': self.max_bytes.value() * 1048576,  # Convert MB to bytes
                        'backup_count': self.backup_count.value()
                    }
                },
                'storage': {
                    'raw_data_path': self.raw_data_path.text(),
                    'processed_data_path': self.processed_data_path.text(),
                    'file_format': self.file_format.currentText()
                }
            }
            
            # Create config directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save configuration
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
                
            self.current_config = config
            self.config_updated.emit(config)
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                "Configuration has been saved successfully."
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Error saving configuration: {str(e)}"
            )