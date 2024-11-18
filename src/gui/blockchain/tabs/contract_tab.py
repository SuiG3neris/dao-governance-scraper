# src/gui/blockchain/tabs/contract_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QTextEdit, QComboBox, QLineEdit, QFormLayout,
    QHeaderView, QMenu, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, List, Optional
import json
import re

from ..utils.abi_manager import ABIManager
from ..utils.contract_templates import ContractTemplates
from ..utils.address_validator import validate_address

class ContractManagementTab(QWidget):
    """Tab for managing smart contract interactions and monitoring."""
    
    contract_added = pyqtSignal(dict)  # Emitted when new contract is added
    contract_removed = pyqtSignal(str)  # Emitted when contract is removed
    event_tracking_updated = pyqtSignal(str, list)  # Emitted when event tracking changes
    
    def __init__(self):
        super().__init__()
        self.abi_manager = ABIManager()
        self.contract_templates = ContractTemplates()
        self.contracts: Dict[str, dict] = {}
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create main sections
        input_group = self._create_input_section()
        contract_group = self._create_contract_section()
        monitoring_group = self._create_monitoring_section()
        
        layout.addWidget(input_group)
        layout.addWidget(contract_group)
        layout.addWidget(monitoring_group)
        
    def _create_input_section(self) -> QGroupBox:
        """Create the contract input section."""
        group = QGroupBox("Add Contracts")
        layout = QVBoxLayout(group)
        
        # Batch input area
        input_layout = QHBoxLayout()
        
        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText(
            "Enter contract addresses (one per line)\n"
            "Optional: Add labels with comma separator\n"
            "Example:\n"
            "0x123...,MyContract\n"
            "0x456...,TokenContract"
        )
        input_layout.addWidget(self.address_input)
        
        # Input controls
        controls_layout = QVBoxLayout()
        
        self.import_btn = QPushButton("Import from CSV")
        self.import_btn.clicked.connect(self._import_from_csv)
        controls_layout.addWidget(self.import_btn)
        
        self.validate_btn = QPushButton("Validate Addresses")
        self.validate_btn.clicked.connect(self._validate_addresses)
        controls_layout.addWidget(self.validate_btn)
        
        self.add_btn = QPushButton("Add Contracts")
        self.add_btn.clicked.connect(self._add_contracts)
        controls_layout.addWidget(self.add_btn)
        
        input_layout.addLayout(controls_layout)
        layout.addLayout(input_layout)
        
        # Network selector
        network_layout = QHBoxLayout()
        network_layout.addWidget(QLabel("Network:"))
        self.network_selector = QComboBox()
        network_layout.addWidget(self.network_selector)
        layout.addLayout(network_layout)
        
        return group
        
    def _create_contract_section(self) -> QGroupBox:
        """Create the contract management section."""
        group = QGroupBox("Contract Management")
        layout = QVBoxLayout(group)
        
        # Contract table
        self.contract_table = QTableWidget()
        self.contract_table.setColumnCount(5)
        self.contract_table.setHorizontalHeaderLabels([
            "Address", "Label", "Type", "Network", "Events Tracked"
        ])
        
        header = self.contract_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        self.contract_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.contract_table.customContextMenuRequested.connect(self._show_contract_menu)
        
        layout.addWidget(self.contract_table)
        
        return group
        
    def _create_monitoring_section(self) -> QGroupBox:
        """Create the event monitoring section."""
        group = QGroupBox("Event Monitoring")
        layout = QHBoxLayout(group)
        
        # Event tree
        self.event_tree = QTreeWidget()
        self.event_tree.setHeaderLabels(["Event", "Parameters"])
        self.event_tree.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.event_tree)
        
        # Monitoring controls
        controls_layout = QVBoxLayout()
        
        self.fetch_abi_btn = QPushButton("Fetch ABI")
        self.fetch_abi_btn.clicked.connect(self._fetch_contract_abi)
        controls_layout.addWidget(self.fetch_abi_btn)
        
        self.import_abi_btn = QPushButton("Import ABI")
        self.import_abi_btn.clicked.connect(self._import_abi)
        controls_layout.addWidget(self.import_abi_btn)
        
        self.select_all_btn = QPushButton("Select All Events")
        self.select_all_btn.clicked.connect(lambda: self.event_tree.selectAll())
        controls_layout.addWidget(self.select_all_btn)
        
        self.apply_btn = QPushButton("Apply Selection")
        self.apply_btn.clicked.connect(self._apply_event_selection)
        controls_layout.addWidget(self.apply_btn)
        
        layout.addLayout(controls_layout)
        
        return group
    
    def _import_from_csv(self):
        """Import contract addresses from CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Contracts from CSV",
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if file_path:
            try:
                import pandas as pd
                df = pd.read_csv(file_path)
                
                # Extract addresses and labels
                addresses = []
                for _, row in df.iterrows():
                    address = row.get('address', '').strip()
                    label = row.get('label', '').strip()
                    if address:
                        addresses.append(f"{address},{label}" if label else address)
                
                self.address_input.setPlainText("\n".join(addresses))
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Import Error",
                    f"Error importing CSV: {str(e)}"
                )
    
    def _validate_addresses(self):
        """Validate entered contract addresses."""
        addresses = self._parse_input_addresses()
        invalid = []
        
        for addr, _ in addresses:
            if not validate_address(addr):
                invalid.append(addr)
        
        if invalid:
            QMessageBox.warning(
                self,
                "Invalid Addresses",
                f"The following addresses are invalid:\n{chr(10).join(invalid)}"
            )
        else:
            QMessageBox.information(
                self,
                "Address Validation",
                "All addresses are valid!"
            )
    
    def _add_contracts(self):
        """Add contracts for tracking."""
        addresses = self._parse_input_addresses()
        network = self.network_selector.currentText()
        
        for address, label in addresses:
            if not validate_address(address):
                continue
                
            contract_info = {
                'address': address,
                'label': label or address[:8],
                'network': network,
                'type': 'Unknown',
                'events_tracked': []
            }
            
            self._add_contract_to_table(contract_info)
            self.contracts[address] = contract_info
            self.contract_added.emit(contract_info)
        
        self.address_input.clear()
    
    def _parse_input_addresses(self) -> List[tuple]:
        """Parse input text into address and label pairs."""
        text = self.address_input.toPlainText().strip()
        if not text:
            return []
            
        addresses = []
        for line in text.split('\n'):
            parts = line.strip().split(',')
            address = parts[0].strip()
            label = parts[1].strip() if len(parts) > 1 else ''
            addresses.append((address, label))
            
        return addresses
    
    def _add_contract_to_table(self, contract_info: dict):
        """Add contract to the display table."""
        row = self.contract_table.rowCount()
        self.contract_table.insertRow(row)
        
        self.contract_table.setItem(row, 0, QTableWidgetItem(contract_info['address']))
        self.contract_table.setItem(row, 1, QTableWidgetItem(contract_info['label']))
        self.contract_table.setItem(row, 2, QTableWidgetItem(contract_info['type']))
        self.contract_table.setItem(row, 3, QTableWidgetItem(contract_info['network']))
        self.contract_table.setItem(row, 4, QTableWidgetItem(
            str(len(contract_info['events_tracked']))
        ))
    
    def _show_contract_menu(self, position):
        """Show context menu for contract management."""
        menu = QMenu()
        
        remove_action = menu.addAction("Remove Contract")
        edit_action = menu.addAction("Edit Label")
        fetch_action = menu.addAction("Fetch Events")
        
        action = menu.exec(self.contract_table.mapToGlobal(position))
        if action == remove_action:
            self._remove_selected_contract()
        elif action == edit_action:
            self._edit_contract_label()
        elif action == fetch_action:
            self._fetch_contract_abi()
    
    def _fetch_contract_abi(self):
        """Fetch ABI for selected contract."""
        row = self.contract_table.currentRow()
        if row < 0:
            return
            
        address = self.contract_table.item(row, 0).text()
        network = self.contract_table.item(row, 3).text()
        
        try:
            abi = self.abi_manager.fetch_abi(address, network)
            self._update_event_tree(abi)
            
            # Update contract type if possible
            contract_type = self.abi_manager.detect_contract_type(abi)
            if contract_type:
                self.contract_table.setItem(row, 2, QTableWidgetItem(contract_type))
                self.contracts[address]['type'] = contract_type
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "ABI Fetch Error",
                f"Error fetching ABI: {str(e)}"
            )
    
    def _import_abi(self):
        """Import ABI from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import ABI",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    abi = json.load(f)
                self._update_event_tree(abi)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Import Error",
                    f"Error importing ABI: {str(e)}"
                )
    
    def _update_event_tree(self, abi: List[dict]):
        """Update event tree with ABI information."""
        self.event_tree.clear()
        
        for item in abi:
            if item.get('type') == 'event':
                event_item = QTreeWidgetItem([item['name']])
                params = []
                for input in item.get('inputs', []):
                    params.append(f"{input['name']}: {input['type']}")
                event_item.setText(1, ", ".join(params))
                self.event_tree.addTopLevelItem(event_item)
    
    def _apply_event_selection(self):
        """Apply selected events to current contract."""
        row = self.contract_table.currentRow()
        if row < 0:
            return
            
        address = self.contract_table.item(row, 0).text()
        selected_events = []
        
        for item in self.event_tree.selectedItems():
            selected_events.append(item.text(0))
        
        # Update contract info
        if address in self.contracts:
            self.contracts[address]['events_tracked'] = selected_events
            self.contract_table.setItem(
                row, 4, QTableWidgetItem(str(len(selected_events)))
            )
            
            # Emit signal for event tracking update
            self.event_tracking_updated.emit(address, selected_events)
    
    def _remove_selected_contract(self):
        """Remove selected contract."""
        row = self.contract_table.currentRow()
        if row >= 0:
            address = self.contract_table.item(row, 0).text()
            self.contracts.pop(address, None)
            self.contract_table.removeRow(row)
            self.contract_removed.emit(address)
    
    def _edit_contract_label(self):
        """Edit label for selected contract."""
        row = self.contract_table.currentRow()
        if row >= 0:
            address = self.contract_table.item(row, 0).text()
            current_label = self.contract_table.item(row, 1).text()
            
            new_label, ok = QInputDialog.getText(
                self,
                "Edit Label",
                "Enter new label:",
                QLineEdit.Normal,
                current_label
            )
            
            if ok and new_label:
                self.contract_table.setItem(row, 1, QTableWidgetItem(new_label))
                if address in self.contracts:
                    self.contracts[address]['label'] = new_label
    
    def update_networks(self, networks: List[str]):
        """Update network selector with available networks."""
        current = self.network_selector.currentText()
        self.network_selector.clear()
        self.network_selector.addItems(networks)
        
        # Restore previous selection if possible
        index = self.network_selector.findText(current)
        if index >= 0:
            self.network_selector.setCurrentIndex(index)