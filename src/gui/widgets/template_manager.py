"""
Export template manager widget for customizing and managing Claude analysis templates.
"""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QListWidget, QDialog,
    QMessageBox, QInputDialog, QComboBox, QGroupBox,
    QDialogButtonBox, QFileDialog, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.gui.widgets.export_manager import ExportManager


class TemplateManagerWidget(QWidget):
    """Widget for managing export templates."""
    
    templateUpdated = pyqtSignal(str)  # Emits template_name when updated
    
    def __init__(
        self, 
        export_manager: ExportManager,
        parent: Optional[QWidget] = None
    ):
        """Initialize template manager widget."""
        super().__init__(parent)
        self.export_manager = export_manager
        self._init_ui()
        
    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Create splitter for template list and editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Template List Section
        list_widget = QWidget()
        list_layout = QVBoxLayout()
        
        list_label = QLabel("Available Templates")
        list_layout.addWidget(list_label)
        
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._load_template)
        list_layout.addWidget(self.template_list)
        
        # Template Actions
        action_layout = QHBoxLayout()
        
        new_btn = QPushButton("New Template")
        new_btn.clicked.connect(self._create_template)
        action_layout.addWidget(new_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_template)
        action_layout.addWidget(delete_btn)
        
        list_layout.addLayout(action_layout)
        
        list_widget.setLayout(list_layout)
        splitter.addWidget(list_widget)
        
        # Template Editor Section
        editor_widget = QWidget()
        editor_layout = QVBoxLayout()
        
        # Template Info
        info_group = QGroupBox("Template Information")
        info_layout = QVBoxLayout()
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_label = QLabel()
        name_layout.addWidget(self.name_label)
        info_layout.addLayout(name_layout)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Analysis Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Governance Analysis",
            "Voter Behavior",
            "Proposal Success",
            "Community Engagement",
            "Custom Analysis"
        ])
        type_layout.addWidget(self.type_combo)
        info_layout.addLayout(type_layout)
        
        info_group.setLayout(info_layout)
        editor_layout.addWidget(info_group)
        
        # Template Content
        content_group = QGroupBox("Template Content")
        content_layout = QVBoxLayout()
        
        self.editor = QTextEdit()
        content_layout.addWidget(self.editor)
        
        # Template Variables
        variables_layout = QHBoxLayout()
        variables_layout.addWidget(QLabel("Insert Variable:"))
        self.variable_combo = QComboBox()
        self.variable_combo.addItems([
            "space_name",
            "proposal_count",
            "vote_count",
            "active_voters",
            "total_voting_power",
            "avg_participation",
            "success_rate",
            "voter_distribution",
            "temporal_patterns"
        ])
        variables_layout.addWidget(self.variable_combo)
        
        insert_btn = QPushButton("Insert")
        insert_btn.clicked.connect(self._insert_variable)
        variables_layout.addWidget(insert_btn)
        
        content_layout.addLayout(variables_layout)
        
        content_group.setLayout(content_layout)
        editor_layout.addWidget(content_group)
        
        # Editor Actions
        editor_actions = QHBoxLayout()
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._save_changes)
        editor_actions.addWidget(save_btn)
        
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self._preview_template)
        editor_actions.addWidget(preview_btn)
        
        export_btn = QPushButton("Export Template")
        export_btn.clicked.connect(self._export_template)
        editor_actions.addWidget(export_btn)
        
        editor_layout.addLayout(editor_actions)
        
        editor_widget.setLayout(editor_layout)
        splitter.addWidget(editor_widget)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Load templates
        self._refresh_templates()
        
    def _refresh_templates(self) -> None:
        """Refresh the template list."""
        self.template_list.clear()
        templates = self.export_manager.get_available_templates()
        for template_name in templates:
            self.template_list.addItem(template_name)
            
    def _load_template(self, current, previous) -> None:
        """Load selected template into editor."""
        if not current:
            return
            
        template_name = current.text()
        self.name_label.setText(template_name)
        
        try:
            template_content = self.export_manager.get_template_content(
                template_name
            )
            self.editor.setPlainText(template_content)
            
            # Load template metadata
            metadata = self.export_manager.get_template_metadata(template_name)
            if metadata and 'analysis_type' in metadata:
                index = self.type_combo.findText(metadata['analysis_type'])
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Error loading template: {str(e)}"
            )
            
    def _create_template(self) -> None:
        """Create a new template."""
        try:
            name, ok = QInputDialog.getText(
                self,
                "New Template",
                "Template Name:"
            )
            if not ok or not name:
                return
                
            # Create new template
            template_content = self._get_default_template()
            self.export_manager.save_template(
                name,
                template_content,
                analysis_type=self.type_combo.currentText()
            )
            
            self._refresh_templates()
            
            # Select new template
            items = self.template_list.findItems(
                name,
                Qt.MatchFlag.MatchExactly
            )
            if items:
                self.template_list.setCurrentItem(items[0])
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Create Error",
                f"Error creating template: {str(e)}"
            )
            
    def _delete_template(self) -> None:
        """Delete selected template."""
        current = self.template_list.currentItem()
        if not current:
            return
            
        template_name = current.text()
        
        reply = QMessageBox.question(
            self,
            "Delete Template",
            f"Are you sure you want to delete template '{template_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.export_manager.delete_template(template_name)
                self._refresh_templates()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Delete Error",
                    f"Error deleting template: {str(e)}"
                )
                
    def _save_changes(self) -> None:
        """Save changes to current template."""
        current = self.template_list.currentItem()
        if not current:
            return
            
        template_name = current.text()
        
        try:
            self.export_manager.save_template(
                template_name,
                self.editor.toPlainText(),
                analysis_type=self.type_combo.currentText()
            )
            
            self.templateUpdated.emit(template_name)
            
            QMessageBox.information(
                self,
                "Save Successful",
                "Template changes saved successfully!"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Error saving changes: {str(e)}"
            )
            
    def _preview_template(self) -> None:
        """Preview current template."""
        try:
            preview_data = self._get_preview_data()
            preview = self.export_manager.preview_template(
                self.template_list.currentItem().text(),
                preview_data
            )
            
            dialog = PreviewDialog(preview, self)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Preview Error",
                f"Error generating preview: {str(e)}"
            )
            
    def _export_template(self) -> None:
        """Export current template to file."""
        current = self.template_list.currentItem()
        if not current:
            return
            
        template_name = current.text()
        
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Template",
                f"{template_name}.yaml",
                "YAML Files (*.yaml);;All Files (*)"
            )
            
            if file_path:
                self.export_manager.export_template(template_name, Path(file_path))
                
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Template exported to {file_path}"
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Error exporting template: {str(e)}"
            )
            
    def _insert_variable(self) -> None:
        """Insert selected variable at cursor position."""
        variable = self.variable_combo.currentText()
        self.editor.insertPlainText(f"{{{{ {variable} }}}}")
        
    @staticmethod
    def _get_default_template() -> str:
        """Get default template content."""
        return """# {{space_name}} Governance Analysis

## Overview
Total Proposals: {{proposal_count}}
Total Votes: {{vote_count}}
Active Voters: {{active_voters}}

## Participation Metrics
Average Participation: {{avg_participation}}%
Success Rate: {{success_rate}}%

## Voter Distribution
{{voter_distribution}}

## Temporal Patterns
{{temporal_patterns}}

"""
    
    @staticmethod
    def _get_preview_data() -> Dict[str, Any]:
        """Get sample data for template preview."""
        return {
            'space_name': 'Example DAO',
            'proposal_count': 150,
            'vote_count': 3500,
            'active_voters': 250,
            'total_voting_power': 1000000,
            'avg_participation': 65.4,
            'success_rate': 78.2,
            'voter_distribution': {
                'active': 100,
                'moderate': 75,
                'casual': 75
            },
            'temporal_patterns': {
                'weekly_avg': 12,
                'peak_day': 'Wednesday',
                'peak_time': '14:00 UTC'
            }
        }


class PreviewDialog(QDialog):
    """Dialog for previewing templates."""
    
    def __init__(self, preview_content: str, parent: Optional[QWidget] = None):
        """Initialize preview dialog."""
        super().__init__(parent)
        self.setWindowTitle("Template Preview")
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        preview = QTextEdit()
        preview.setPlainText(preview_content)
        preview.setReadOnly(True)
        layout.addWidget(preview)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)