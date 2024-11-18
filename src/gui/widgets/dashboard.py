# src/gui/widgets/dashboard.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QGroupBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class StatisticWidget(QFrame):
    """Widget for displaying a single statistic."""
    
    def __init__(self, title: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title label
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Value label
        self.value_label = QLabel(value)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(16)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        layout.addWidget(self.value_label)
        
    def update_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(str(value))

class DashboardWidget(QWidget):
    """Main dashboard widget displaying scraping status and statistics."""
    
    # Signals
    scrape_started = pyqtSignal(str)  # Emitted when scraping starts with space_id
    scrape_stopped = pyqtSignal()    # Emitted when scraping is stopped
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.scraping_active = False
        
    def _init_ui(self):
        """Initialize the dashboard UI."""
        layout = QVBoxLayout(self)
        
        # Status section
        status_group = QGroupBox("Scraping Status")
        status_layout = QVBoxLayout(status_group)
        
        # Status indicators
        status_grid = QGridLayout()
        
        self.space_label = QLabel("Current Space: None")
        status_grid.addWidget(self.space_label, 0, 0)
        
        self.status_label = QLabel("Status: Idle")
        status_grid.addWidget(self.status_label, 0, 1)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_grid.addWidget(self.progress_bar, 1, 0, 1, 2)
        
        status_layout.addLayout(status_grid)
        layout.addWidget(status_group)
        
        # Statistics section
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout(stats_group)
        
        # Create statistic widgets
        self.spaces_stat = StatisticWidget("Spaces Scraped")
        stats_layout.addWidget(self.spaces_stat, 0, 0)
        
        self.proposals_stat = StatisticWidget("Total Proposals")
        stats_layout.addWidget(self.proposals_stat, 0, 1)
        
        self.votes_stat = StatisticWidget("Total Votes")
        stats_layout.addWidget(self.votes_stat, 0, 2)
        
        self.rate_stat = StatisticWidget("Current Rate", "0/min")
        stats_layout.addWidget(self.rate_stat, 1, 0)
        
        self.errors_stat = StatisticWidget("Errors")
        stats_layout.addWidget(self.errors_stat, 1, 1)
        
        self.uptime_stat = StatisticWidget("Uptime", "0:00:00")
        stats_layout.addWidget(self.uptime_stat, 1, 2)
        
        layout.addWidget(stats_group)
        
        # Controls section
        controls_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Scraping")
        self.start_button.clicked.connect(self.toggle_scraping)
        controls_layout.addWidget(self.start_button)
        
        self.clear_button = QPushButton("Clear Statistics")
        self.clear_button.clicked.connect(self.clear_statistics)
        controls_layout.addWidget(self.clear_button)
        
        layout.addLayout(controls_layout)
        
        # Add stretch to bottom
        layout.addStretch()
        
    def toggle_scraping(self):
        """Toggle the scraping process."""
        self.scraping_active = not self.scraping_active
        
        if self.scraping_active:
            self.start_button.setText("Stop Scraping")
            self.status_label.setText("Status: Active")
            self.scrape_started.emit("test-space")  # Replace with actual space ID
        else:
            self.start_button.setText("Start Scraping")
            self.status_label.setText("Status: Idle")
            self.scrape_stopped.emit()
            
    def clear_statistics(self):
        """Reset all statistics to zero."""
        self.spaces_stat.update_value("0")
        self.proposals_stat.update_value("0")
        self.votes_stat.update_value("0")
        self.rate_stat.update_value("0/min")
        self.errors_stat.update_value("0")
        self.uptime_stat.update_value("0:00:00")
        self.progress_bar.setValue(0)
        
    def update_progress(self, value: int):
        """Update the progress bar value."""
        self.progress_bar.setValue(value)
        
    def update_space(self, space_id: str):
        """Update the current space being scraped."""
        self.space_label.setText(f"Current Space: {space_id}")
        
    def update_statistics(self, stats: dict):
        """Update dashboard statistics."""
        if 'spaces' in stats:
            self.spaces_stat.update_value(str(stats['spaces']))
        if 'proposals' in stats:
            self.proposals_stat.update_value(str(stats['proposals']))
        if 'votes' in stats:
            self.votes_stat.update_value(str(stats['votes']))
        if 'rate' in stats:
            self.rate_stat.update_value(f"{stats['rate']}/min")
        if 'errors' in stats:
            self.errors_stat.update_value(str(stats['errors']))
        if 'uptime' in stats:
            self.uptime_stat.update_value(stats['uptime'])