"""
Dialog windows for API management GUI.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QTextEdit, QSpinBox, QMessageBox
)
from typing import Optional

from ..models import APICredential, APIType

class AddCredentialDialog(QDialog):
    """Dialog for adding new API credentials."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add API Credential")
        self.setModal(True)
        self.resize(400, 400)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize dialog UI."""
        layout = QVBoxLayout(self)
        
        # Create form
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter a unique name for this credential")
        form.addRow("Name:", self.name_input)
        
        self.type_selector = QComboBox()
        self.type_selector.addItems([t.name for t in APIType])
        self.type_selector.currentTextChanged.connect(self._on_type_changed)
        form.addRow("API Type:", self.type_selector)
        
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Enter API key or token")
        form.addRow("API Key:", self.key_input)
        
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setPlaceholderText("Optional: Enter custom API endpoint")
        form.addRow("Endpoint:", self.endpoint_input)
        
        self.rate_limit = QSpinBox()
        self.rate_limit.setRange(0, 10000)
        self.rate_limit.setSuffix(" requests/minute")
        self.rate_limit.setSpecialValueText("No limit")
        form.addRow("Rate Limit:", self.rate_limit)
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Optional: Add notes about this credential")
        self.notes_input.setMaximumHeight(100)
        form.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form)
        
        # Add help text
        help_text = QLabel()
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: gray;")
        layout.addWidget(help_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._validate_and_accept)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Set initial help text
        self._on_type_changed(self.type_selector.currentText())
        
    def _on_type_changed(self, api_type: str):
        """Update help text and defaults when API type changes."""
        help_texts = {
            'ETHERSCAN': "Enter your Etherscan API key. You can find this in your Etherscan account settings.",
            'GITLAB': "Enter your GitLab personal access token with api scope.",
            'ANTHROPIC': "Enter your Anthropic API key for Claude access.",
            'SNAPSHOT': "Enter your Snapshot.org API key.",
            'CUSTOM': "Enter the API key and endpoint for your custom API."
        }
        
        endpoints = {
            'ETHERSCAN': "https://api.etherscan.io/api",
            'GITLAB': "https://gitlab.com/api/v4",
            'ANTHROPIC': "https://api.anthropic.com/v1",
            'SNAPSHOT': "https://hub.snapshot.org/graphql",
            'CUSTOM': ""
        }
        
        self.endpoint_input.setText(endpoints.get(api_type, ""))
        self.findChild(QLabel, "help_text").setText(help_texts.get(api_type, ""))
        
    def _validate_and_accept(self):
        """Validate inputs before accepting."""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required.")
            return
            
        if not self.key_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "API key is required.")
            return
            
        if self.type_selector.currentText() == 'CUSTOM' and not self.endpoint_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Endpoint is required for custom APIs.")
            return
            
        self.accept()
        
    def get_credential(self) -> Optional[APICredential]:
        """Get entered credential information."""
        if not self.name_input.text() or not self.key_input.text():
            return None
            
        return APICredential(
            name=self.name_input.text().strip(),
            key=self.key_input.text().strip(),
            api_type=APIType[self.type_selector.currentText()],
            endpoint=self.endpoint_input.text().strip() or None,
            rate_limit=self.rate_limit.value(),
            notes=self.notes_input.toPlainText().strip()
        )