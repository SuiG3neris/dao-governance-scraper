# src/gui/blockchain/blockchain_manager_gui.py

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QToolBar, QDialog,
    QLineEdit, QComboBox, QListWidget, QTextEdit, QProgressBar,
    QGroupBox, QFormLayout, QSpinBox, QTableWidget, QCheckBox,
    QMessageBox, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from typing import Dict, List, Optional

from .tabs.network_tab import NetworkManagementTab
from .tabs.contract_tab import ContractManagementTab
from .tabs.wallet_tab import WalletTrackingTab
from .tabs.data_tab import DataCollectionTab
from .dialogs.network_dialog import AddNetworkDialog
from .utils.blockchain_monitor import BlockchainMonitor
from .utils.network_templates import NetworkTemplates

class BlockchainManagerGUI(QMainWindow):
    """Main window for blockchain data management interface."""
    
    network_status_updated = pyqtSignal(dict)  # Emitted when network status changes
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blockchain Data Manager")
        self.setMinimumSize(1200, 800)
        
        # Initialize components
        self.network_monitor = BlockchainMonitor()
        self.network_templates = NetworkTemplates()
        
        self._init_ui()
        self._setup_signals()
        self._start_monitoring()
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Add specialized tabs
        self.network_tab = NetworkManagementTab(self.network_templates)
        self.contract_tab = ContractManagementTab()
        self.wallet_tab = WalletTrackingTab()
        self.data_tab = DataCollectionTab()
        
        self.tabs.addTab(self.network_tab, "Networks")
        self.tabs.addTab(self.contract_tab, "Contracts")
        self.tabs.addTab(self.wallet_tab, "Wallets")
        self.tabs.addTab(self.data_tab, "Data Collection")
        
        # Create status bar
        self.status_bar = self.create_status_bar()
        
    def create_toolbar(self):
        """Create and configure the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add Network button
        add_network_action = toolbar.addAction("Add Network")
        add_network_action.triggered.connect(self.show_add_network_dialog)
        
        # Quick import button
        import_action = toolbar.addAction("Quick Import")
        import_action.triggered.connect(self.show_import_dialog)
        
        toolbar.addSeparator()
        
        # Monitoring controls
        self.monitor_btn = QPushButton("Start Monitoring")
        self.monitor_btn.setCheckable(True)
        self.monitor_btn.toggled.connect(self.toggle_monitoring)
        toolbar.addWidget(self.monitor_btn)
        
    def create_status_bar(self) -> QStatusBar:
        """Create and configure the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Add network status indicators
        self.network_status = QLabel("Networks: 0 active")
        status_bar.addPermanentWidget(self.network_status)
        
        # Add sync status
        self.sync_status = QLabel("Sync: --")
        status_bar.addPermanentWidget(self.sync_status)
        
        # Add latest block indicator
        self.block_status = QLabel("Latest Block: --")
        status_bar.addPermanentWidget(self.block_status)
        
        return status_bar
    
    def _setup_signals(self):
        """Connect signals and slots."""
        # Network status updates
        self.network_monitor.status_updated.connect(self.update_network_status)
        self.network_tab.network_added.connect(self.network_monitor.add_network)
        self.network_tab.network_removed.connect(self.network_monitor.remove_network)
        
        # Contract/Wallet tracking
        self.contract_tab.contract_added.connect(self.network_monitor.track_contract)
        self.wallet_tab.wallet_added.connect(self.network_monitor.track_wallet)
        
        # Data collection updates
        self.data_tab.collection_started.connect(self.network_monitor.start_collection)
        self.data_tab.collection_stopped.connect(self.network_monitor.stop_collection)
    
    def _start_monitoring(self):
        """Start the network monitoring system."""
        self.network_monitor.start()
        self.monitor_btn.setChecked(True)
    
    def show_add_network_dialog(self):
        """Show dialog for adding a new network."""
        dialog = AddNetworkDialog(self.network_templates)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            network_config = dialog.get_network_config()
            self.network_tab.add_network(network_config)
    
    def show_import_dialog(self):
        """Show dialog for quick import of addresses/contracts."""
        # TODO: Implement quick import dialog
        pass
    
    def toggle_monitoring(self, checked: bool):
        """Toggle the monitoring system."""
        if checked:
            self.network_monitor.start()
            self.monitor_btn.setText("Stop Monitoring")
        else:
            self.network_monitor.stop()
            self.monitor_btn.setText("Start Monitoring")
    
    def update_network_status(self, status: Dict):
        """Update status bar with network information."""
        self.network_status.setText(f"Networks: {status['active_networks']} active")
        self.sync_status.setText(f"Sync: {status['sync_status']}")
        self.block_status.setText(f"Latest Block: {status['latest_block']}")
    
    def closeEvent(self, event):
        """Handle application close event."""
        reply = QMessageBox.question(
            self,
            'Confirm Exit',
            'Are you sure you want to exit? This will stop all monitoring.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.network_monitor.stop()
            event.accept()
        else:
            event.ignore()