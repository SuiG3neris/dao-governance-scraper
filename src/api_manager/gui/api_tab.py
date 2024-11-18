"""
PyQt6 GUI interface for API credential management.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import datetime

from .. import APIManager
from ..models import APICredential, APIType
from .dialogs import AddCredentialDialog

class APIManagerTab(QWidget):
    """Tab widget for managing API credentials."""
    
    status_message = pyqtSignal(str)  # Emitted when status should be shown
    
    def __init__(self, api_manager: APIManager):
        super().__init__()
        self.api_manager = api_manager
        self._init_ui()
        self._load_credentials()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        self.add_btn = QPushButton("Add Credential")
        self.add_btn.clicked.connect(self._add_credential)
        controls_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_credential)
        self.edit_btn.setEnabled(False)
        controls_layout.addWidget(self.edit_btn)
        
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self._validate_credential)
        self.validate_btn.setEnabled(False)
        controls_layout.addWidget(self.validate_btn)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_credential)
        self.remove_btn.setEnabled(False)
        controls_layout.addWidget(self.remove_btn)
        
        layout.addWidget(controls_group)
        
        # Credentials table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Type", "Endpoint", "Rate Limit",
            "Valid", "Created", "Last Used"
        ])
        
        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        layout.addWidget(self.table)
        
    def _load_credentials(self):
        """Load credentials into table."""
        self.table.setRowCount(0)
        
        for cred in self.api_manager.list_credentials():
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(cred['name']))
            self.table.setItem(row, 1, QTableWidgetItem(cred['api_type']))
            self.table.setItem(row, 2, QTableWidgetItem(cred['endpoint'] or ''))
            self.table.setItem(row, 3, QTableWidgetItem(str(cred.get('rate_limit', ''))))
            
            valid_item = QTableWidgetItem('✓' if cred['is_valid'] else '✗')
            valid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, valid_item)
            
            created = datetime.fromisoformat(cred['created_at'])
            self.table.setItem(row, 5, QTableWidgetItem(created.strftime('%Y-%m-%d')))
            
            last_used = datetime.fromisoformat(cred['last_used'])
            self.table.setItem(row, 6, QTableWidgetItem(last_used.strftime('%Y-%m-%d')))
            
    def _on_selection_changed(self):
        """Handle credential selection change."""
        has_selection = bool(self.table.selectedItems())
        self.edit_btn.setEnabled(has_selection)
        self.validate_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
        
    def _add_credential(self):
        """Add new API credential."""
        dialog = AddCredentialDialog(self)
        if dialog.exec():
            credential = dialog.get_credential()
            if credential:
                try:
                    self.api_manager.add_credential(credential)
                    self._load_credentials()
                    self.status_message.emit(f"Added credential: {credential.name}")
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to add credential: {str(e)}"
                    )
                    
    def _edit_credential(self):
        """Edit selected credential."""
        row = self.table.currentRow()
        if row >= 0:
            name = self.table.item(row, 0).text()
            credential = self.api_manager.get_credential(name)
            if credential:
                dialog = AddCredentialDialog(self)
                
                # Pre-fill existing values
                dialog.name_input.setText(credential.name)
                dialog.name_input.setEnabled(False)  # Don't allow name change
                
                index = dialog.type_selector.findText(credential.api_type.name)
                if index >= 0:
                    dialog.type_selector.setCurrentIndex(index)
                
                dialog.key_input.setText(credential.key)
                if credential.endpoint:
                    dialog.endpoint_input.setText(credential.endpoint)
                dialog.rate_limit.setValue(credential.rate_limit)
                dialog.notes_input.setPlainText(credential.notes)
                
                if dialog.exec():
                    new_credential = dialog.get_credential()
                    if new_credential:
                        try:
                            # Update existing credential
                            self.api_manager.update_credential(
                                name,
                                key=new_credential.key,
                                endpoint=new_credential.endpoint,
                                rate_limit=new_credential.rate_limit,
                                notes=new_credential.notes
                            )
                            self._load_credentials()
                            self.status_message.emit(f"Updated credential: {name}")
                        except Exception as e:
                            QMessageBox.critical(
                                self,
                                "Error",
                                f"Failed to update credential: {str(e)}"
                            )
                            
    def _validate_credential(self):
        """Validate selected credential."""
        row = self.table.currentRow()
        if row >= 0:
            name = self.table.item(row, 0).text()
            
            try:
                is_valid = self.api_manager.validate_credential(name)
                self._load_credentials()
                
                status = "valid" if is_valid else "invalid"
                self.status_message.emit(f"Credential {name} is {status}")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Validation Error",
                    f"Failed to validate credential: {str(e)}"
                )
                
    def _remove_credential(self):
        """Remove selected credential."""
        row = self.table.currentRow()
        if row >= 0:
            name = self.table.item(row, 0).text()
            
            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                f"Are you sure you want to remove credential '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.api_manager.remove_credential(name)
                    self._load_credentials()
                    self.status_message.emit(f"Removed credential: {name}")
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to remove credential: {str(e)}"
                    )