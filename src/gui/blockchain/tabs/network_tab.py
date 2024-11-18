# src/gui/blockchain/tabs/network_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QLineEdit, QFormLayout, QSpinBox,
    QHeaderView, QMenu, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, List, Optional
import json

from ..utils.network_templates import NetworkTemplates
from ..utils.blockchain_types import NetworkConfig, NetworkStatus

class NetworkManagementTab(QWidget):
    """Tab for managing blockchain network connections."""
    
    network_added = pyqtSignal(dict)  # Emitted when new network is added
    network_removed = pyqtSignal(str)  # Emitted when network is removed
    network_updated = pyqtSignal(str, dict)  # Emitted when network config is updated
    
    def __init__(self, network_templates: NetworkTemplates):
        super().__init__()
        self.network_templates = network_templates
        self.networks: Dict[str, NetworkConfig] = {}
        self.status_indicators: Dict[str, Dict] = {}
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Quick Add Panel
        quick_add_group = self._create_quick_add_panel()
        layout.addWidget(quick_add_group)
        
        # Active Networks Panel
        networks_group = self._create_networks_panel()
        layout.addWidget(networks_group)
        
        # Templates Panel
        templates_group = self._create_templates_panel()
        layout.addWidget(templates_group)
        
    def _create_quick_add_panel(self) -> QGroupBox:
        """Create the quick add network panel."""
        group = QGroupBox("Quick Add Network")
        layout = QFormLayout(group)
        
        # Network type selection
        self.network_type = QComboBox()
        self.network_type.addItems(["EVM", "Solana", "Cosmos", "Polkadot"])
        self.network_type.currentTextChanged.connect(self._update_form_fields)
        layout.addRow("Network Type:", self.network_type)
        
        # Network name
        self.network_name = QLineEdit()
        layout.addRow("Name:", self.network_name)
        
        # RPC URL
        self.rpc_url = QLineEdit()
        layout.addRow("RPC URL:", self.rpc_url)
        
        # Chain ID (for EVM)
        self.chain_id = QSpinBox()
        self.chain_id.setRange(1, 999999)
        layout.addRow("Chain ID:", self.chain_id)
        
        # API Key
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("API Key:", self.api_key)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._test_connection)
        button_layout.addWidget(self.test_btn)
        
        self.add_btn = QPushButton("Add Network")
        self.add_btn.clicked.connect(self._add_network)
        button_layout.addWidget(self.add_btn)
        
        layout.addRow("", button_layout)
        
        return group
        
    def _create_networks_panel(self) -> QGroupBox:
        """Create the active networks panel."""
        group = QGroupBox("Active Networks")
        layout = QVBoxLayout(group)
        
        # Networks table
        self.networks_table = QTableWidget()
        self.networks_table.setColumnCount(6)
        self.networks_table.setHorizontalHeaderLabels([
            "Name", "Type", "Status", "Current Block", 
            "Sync Status", "Health"
        ])
        
        # Configure table
        header = self.networks_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        self.networks_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.networks_table.customContextMenuRequested.connect(self._show_network_menu)
        
        layout.addWidget(self.networks_table)
        
        return group
        
    def _create_templates_panel(self) -> QGroupBox:
        """Create the network templates panel."""
        group = QGroupBox("Network Templates")
        layout = QVBoxLayout(group)
        
        # Template categories
        categories_layout = QHBoxLayout()
        
        # EVM Templates
        evm_group = QGroupBox("EVM Chains")
        evm_layout = QVBoxLayout(evm_group)
        
        evm_templates = self.network_templates.get_evm_templates()
        for name, config in evm_templates.items():
            btn = QPushButton(name)
            btn.clicked.connect(lambda c, cfg=config: self._load_template(cfg))
            evm_layout.addWidget(btn)
            
        categories_layout.addWidget(evm_group)
        
        # Non-EVM Templates
        non_evm_group = QGroupBox("Non-EVM Chains")
        non_evm_layout = QVBoxLayout(non_evm_group)
        
        non_evm_templates = self.network_templates.get_non_evm_templates()
        for name, config in non_evm_templates.items():
            btn = QPushButton(name)
            btn.clicked.connect(lambda c, cfg=config: self._load_template(cfg))
            non_evm_layout.addWidget(btn)
            
        categories_layout.addWidget(non_evm_group)
        
        layout.addLayout(categories_layout)
        
        return group
        
    def _update_form_fields(self, network_type: str):
        """Update form fields based on network type."""
        # Show/hide chain ID for EVM networks
        self.chain_id.setVisible(network_type == "EVM")
        self.chain_id.setEnabled(network_type == "EVM")
        
    def _test_connection(self):
        """Test network connection."""
        config = self._get_current_config()
        # TODO: Implement actual connection testing
        pass
        
    def _add_network(self):
        """Add new network configuration."""
        config = self._get_current_config()
        
        # Validate config
        if not self._validate_config(config):
            return
            
        # Add to networks dict
        self.networks[config['name']] = config
        
        # Add to table
        self._add_network_to_table(config)
        
        # Emit signal
        self.network_added.emit(config)
        
        # Clear form
        self._clear_form()
        
    def _get_current_config(self) -> Dict:
        """Get current network configuration from form."""
        return {
            'name': self.network_name.text(),
            'type': self.network_type.currentText(),
            'rpc_url': self.rpc_url.text(),
            'chain_id': self.chain_id.value() if self.network_type.currentText() == "EVM" else None,
            'api_key': self.api_key.text()
        }
        
    def _validate_config(self, config: Dict) -> bool:
        """Validate network configuration."""
        if not config['name']:
            return False
        if not config['rpc_url']:
            return False
        if config['type'] == "EVM" and not config['chain_id']:
            return False
        return True
        
    def _add_network_to_table(self, config: Dict):
        """Add network to the display table."""
        row = self.networks_table.rowCount()
        self.networks_table.insertRow(row)
        
        # Add network info
        self.networks_table.setItem(row, 0, QTableWidgetItem(config['name']))
        self.networks_table.setItem(row, 1, QTableWidgetItem(config['type']))
        
        # Add status indicators
        status_cell = QTableWidgetItem("Connecting...")
        self.networks_table.setItem(row, 2, status_cell)
        
        block_cell = QTableWidgetItem("--")
        self.networks_table.setItem(row, 3, block_cell)
        
        sync_progress = QProgressBar()
        self.networks_table.setCellWidget(row, 4, sync_progress)
        
        health_cell = QTableWidgetItem("--")
        self.networks_table.setItem(row, 5, health_cell)
        
        # Store status indicators
        self.status_indicators[config['name']] = {
            'status': status_cell,
            'block': block_cell,
            'sync': sync_progress,
            'health': health_cell
        }
        
    def _show_network_menu(self, position):
        """Show context menu for network management."""
        menu = QMenu()
        
        remove_action = menu.addAction("Remove Network")
        edit_action = menu.addAction("Edit Configuration")
        
        action = menu.exec(self.networks_table.mapToGlobal(position))
        if action == remove_action:
            self._remove_selected_network()
        elif action == edit_action:
            self._edit_selected_network()
            
    def _remove_selected_network(self):
        """Remove selected network."""
        row = self.networks_table.currentRow()
        if row >= 0:
            network_name = self.networks_table.item(row, 0).text()
            
            # Remove from tracking
            self.networks.pop(network_name, None)
            self.status_indicators.pop(network_name, None)
            
            # Remove from table
            self.networks_table.removeRow(row)
            
            # Emit signal
            self.network_removed.emit(network_name)
            
    def _edit_selected_network(self):
        """Edit selected network configuration."""
        # TODO: Implement network editing
        pass
        
    def _load_template(self, template_config: Dict):
        """Load network template into form."""
        self.network_type.setCurrentText(template_config['type'])
        self.network_name.setText(template_config.get('name', ''))
        self.rpc_url.setText(template_config.get('rpc_url', ''))
        if template_config['type'] == "EVM":
            self.chain_id.setValue(template_config.get('chain_id', 1))
            
    def _clear_form(self):
        """Clear the quick add form."""
        self.network_name.clear()
        self.rpc_url.clear()
        self.api_key.clear()
        self.chain_id.setValue(1)
        
    def update_network_status(self, name: str, status: NetworkStatus):
        """Update status indicators for a network."""
        if name not in self.status_indicators:
            return
            
        indicators = self.status_indicators[name]
        
        # Update status
        indicators['status'].setText(status.status)
        indicators['block'].setText(str(status.current_block))
        indicators['sync'].setValue(status.sync_progress)
        indicators['health'].setText(status.health)