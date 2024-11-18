# src/gui/utils.py
from PyQt6.QtWidgets import (
    QMessageBox, QTableView, QFrame, QToolButton
)
from PyQt6.QtGui import QIcon
from typing import Optional

def show_error_dialog(
    parent,
    message: str,
    title: str = "Error",
    detailed_text: Optional[str] = None
) -> None:
    """Show an error dialog with optional detailed text."""
    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Icon.Critical)
    dialog.setText(message)
    dialog.setWindowTitle(title)
    if detailed_text:
        dialog.setDetailedText(detailed_text)
    dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
    dialog.exec()

def show_info_dialog(
    parent,
    message: str,
    title: str = "Information"
) -> None:
    """Show an information dialog."""
    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Icon.Information)
    dialog.setText(message)
    dialog.setWindowTitle(title)
    dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
    dialog.exec()

def show_confirmation_dialog(
    parent,
    message: str,
    title: str = "Confirm Action"
) -> bool:
    """Show a confirmation dialog and return user's choice."""
    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes

def create_tool_button(
    icon_name: str,
    tooltip: str = "",
    enabled: bool = True
) -> QToolButton:
    """
    Create a standardized tool button with icon.
    
    Args:
        icon_name: Name of the icon from theme
        tooltip: Button tooltip text
        enabled: Whether button should be enabled
        
    Returns:
        QToolButton instance
    """
    button = QToolButton()
    button.setIcon(QIcon.fromTheme(icon_name))
    button.setToolTip(tooltip)
    button.setEnabled(enabled)
    return button

def set_table_style(table_view: QTableView) -> None:
    """Apply consistent styling to a table view."""
    table_view.setAlternatingRowColors(True)
    table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    table_view.horizontalHeader().setStretchLastSection(True)
    table_view.verticalHeader().setVisible(False)
    
def create_horizontal_separator() -> QFrame:
    """Create a horizontal line separator."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line

def create_vertical_separator() -> QFrame:
    """Create a vertical line separator."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line