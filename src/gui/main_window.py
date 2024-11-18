"""
Main application window for the DAO governance scraper.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget, 
    QMessageBox, QStatusBar, QFileDialog
)
from PyQt6.QtCore import Qt, QSettings
import sys
import os
import logging
from pathlib import Path

# Add the project root to the Python path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from .widgets.dashboard import DashboardWidget
from .widgets.data_preview import DataPreviewWidget
from .widgets.config_panel import ConfigurationPanel
from .widgets.forum_tab import ForumTab
from .widgets.claude_analysis import ClaudeAnalysisTab
from .widgets.export_manager import ExportManagerTab
from .widgets.documents_tab import DocumentsTab

# Import from src.api_manager
from src.api_manager import APIManager, APIManagerTab

class MainWindow(QMainWindow):
    """Main application window for the DAO governance scraper."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAO Governance Data Scraper")
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize settings
        self.settings = QSettings('DAOScraper', 'MainWindow')
        
        # Create application directories
        self.app_dir = Path.home() / '.dao_scraper'
        self.app_dir.mkdir(parents=True, exist_ok=True)
        
        # Create config directory
        self.config_dir = self.app_dir / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize configuration with defaults
        self.config = {
            'max_workers': 4,
            'extraction': {
                'ocr_language': 'eng',
                'extract_tables': True,
                'extract_images': True,
                'batch_size': 10
            },
            'security': {
                'max_file_size': 100 * 1024 * 1024,  # 100MB
                'allowed_mime_types': [
                    'application/pdf',
                    'image/jpeg',
                    'image/png',
                    'text/plain',
                    'text/csv',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ]
            },
            'storage': {
                'temp_dir': str(self.app_dir / 'temp'),
                'output_dir': str(self.app_dir / 'output'),
                'documents_dir': str(self.app_dir / 'documents')
            },
            'processing': {
                'batch_size': 10,
                'max_parallel': 2,
                'timeout': 300
            }
        }
        
        # Create required directories
        for dir_path in [self.config['storage']['temp_dir'], 
                        self.config['storage']['output_dir'],
                        self.config['storage']['documents_dir']]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize API Manager with default config
        try:
            self.api_manager = APIManager()
            self.logger.info("API Manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize API Manager: {e}")
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize API Manager: {str(e)}"
            )
        
        # Restore window geometry
        self.resize(1200, 800)
        if self.settings.value("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        
        self._init_ui()
        self._setup_menubar()
        self._restore_state()
        
    def _init_ui(self):
        """Initialize the main UI components."""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Initialize tabs with error handling
        try:
            self.dashboard = DashboardWidget()
            self.tab_widget.addTab(self.dashboard, "Dashboard")
        except Exception as e:
            self.logger.error(f"Failed to initialize Dashboard: {e}")
        
        try:
            self.data_preview = DataPreviewWidget()
            self.tab_widget.addTab(self.data_preview, "Data Preview")
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Preview: {e}")
        
        try:
            self.documents_tab = DocumentsTab(self.config)
            self.tab_widget.addTab(self.documents_tab, "Documents")
        except Exception as e:
            self.logger.error(f"Failed to initialize Documents tab: {e}")
            QMessageBox.warning(
                self,
                "Initialization Warning",
                "Documents tab could not be initialized. Some features may be unavailable."
            )
        
        try:
            self.config_panel = ConfigurationPanel()
            self.tab_widget.addTab(self.config_panel, "Configuration")
        except Exception as e:
            self.logger.error(f"Failed to initialize Configuration panel: {e}")
        
        try:
            self.forum_tab = ForumTab()
            self.tab_widget.addTab(self.forum_tab, "Forum Data")
        except Exception as e:
            self.logger.error(f"Failed to initialize Forum tab: {e}")
        
        # Add API Management Tab
        try:
            self.api_tab = APIManagerTab(self.api_manager)
            self.tab_widget.addTab(self.api_tab, "API Management")
            # Connect API tab status messages to status bar
            self.api_tab.status_message.connect(self._show_status_message)
        except Exception as e:
            self.logger.error(f"Failed to initialize API tab: {e}")
        
        try:
            self.claude_tab = ClaudeAnalysisTab()
            self.tab_widget.addTab(self.claude_tab, "Claude Analysis")
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude Analysis tab: {e}")
        
        try:
            self.export_tab = ExportManagerTab()
            self.tab_widget.addTab(self.export_tab, "Export Manager")
        except Exception as e:
            self.logger.error(f"Failed to initialize Export Manager tab: {e}")
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def _setup_menubar(self):
        """Set up the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Add actions for file menu
        actions = [
            ("&New Project", "Ctrl+N", self.new_project),
            ("&Open Project", "Ctrl+O", self.open_project),
            ("&Save Project", "Ctrl+S", self.save_project),
            (None, None, None),  # Separator
            ("E&xit", "Alt+F4", self.close)
        ]
        
        for label, shortcut, handler in actions:
            if label is None:
                file_menu.addSeparator()
                continue
                
            action = file_menu.addAction(label)
            if shortcut:
                action.setShortcut(shortcut)
            if handler:
                action.triggered.connect(handler)
        
        # API menu
        api_menu = menubar.addMenu("&APIs")
        
        # Add API menu actions
        api_actions = [
            ("&Add API Credential", "Ctrl+A", lambda: self.api_tab._add_credential()),
            ("&Validate All", None, self._validate_all_credentials),
            (None, None, None),
            ("&Export Credentials", None, self._export_credentials),
            ("&Import Credentials", None, self._import_credentials),
        ]
        
        for label, shortcut, handler in api_actions:
            if label is None:
                api_menu.addSeparator()
                continue
                
            action = api_menu.addAction(label)
            if shortcut:
                action.setShortcut(shortcut)
            if handler:
                action.triggered.connect(handler)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self.show_about)
        
    def _validate_all_credentials(self):
        """Validate all stored API credentials."""
        try:
            results = []
            for cred in self.api_manager.list_credentials():
                name = cred['name']
                is_valid = self.api_manager.validate_credential(name)
                results.append((name, is_valid))
            
            # Show results dialog
            msg = "Validation Results:\n\n"
            for name, is_valid in results:
                status = "✓ valid" if is_valid else "✗ invalid"
                msg += f"{name}: {status}\n"
                
            QMessageBox.information(self, "Validation Results", msg)
            
            # Refresh API tab display
            self.api_tab._load_credentials()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Validation Error",
                f"Error validating credentials: {str(e)}"
            )
            
    def _export_credentials(self):
        """Export API credentials to encrypted file."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Credentials",
                "",
                "Encrypted Files (*.enc);;All Files (*.*)"
            )
            if file_path:
                self.api_manager.save_credentials()
                self._show_status_message("Credentials exported successfully")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Error exporting credentials: {str(e)}"
            )
            
    def _import_credentials(self):
        """Import API credentials from encrypted file."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Credentials",
                "",
                "Encrypted Files (*.enc);;All Files (*.*)"
            )
            if file_path:
                self.api_manager.load_credentials()
                self.api_tab._load_credentials()
                self._show_status_message("Credentials imported successfully")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Error importing credentials: {str(e)}"
            )

    def _show_status_message(self, message: str, timeout: int = 5000):
        """Show message in status bar with timeout."""
        self.status_bar.showMessage(message, timeout)
        
    def new_project(self):
        """Create a new project."""
        reply = QMessageBox.question(
            self, 
            "New Project",
            "Are you sure you want to start a new project? Unsaved changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.dashboard.reset()
            self.data_preview.clear()
            self._show_status_message("New project created")
            
    def open_project(self):
        """Open an existing project."""
        # Implement project loading logic
        pass
        
    def save_project(self):
        """Save current project."""
        # Implement project saving logic
        pass
        
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About DAO Governance Scraper",
            """
            <h3>DAO Governance Data Scraper</h3>
            <p>A tool for collecting and analyzing DAO governance data.</p>
            <p>Version 1.0</p>
            """
        )
        
    def closeEvent(self, event):
        """Handle application close event."""
        # Save window state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        # Check for unsaved changes
        reply = QMessageBox.question(
            self,
            "Exit",
            "Are you sure you want to exit? Unsaved changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
            
    def _restore_state(self):
        """Restore previous window state."""
        if self.settings.value("windowState"):
            self.restoreState(self.settings.value("windowState"))