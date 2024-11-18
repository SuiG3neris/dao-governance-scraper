# src/gui/widgets/claude_analysis.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QTextEdit, QProgressBar,
    QGroupBox, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal

class ClaudeAnalysisTab(QWidget):
    """Tab for preparing and analyzing data with Claude."""
    
    analysis_requested = pyqtSignal(dict)  # Signal for analysis parameters
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Data Selection Group
        selection_group = QGroupBox("Data Selection")
        selection_layout = QVBoxLayout()
        
        # Data source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Data Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Proposals", "Votes", "Forum Posts", "Combined"])
        source_layout.addWidget(self.source_combo)
        selection_layout.addLayout(source_layout)
        
        # Date range selection
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date Range:"))
        self.date_combo = QComboBox()
        self.date_combo.addItems(["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        date_layout.addWidget(self.date_combo)
        selection_layout.addLayout(date_layout)
        
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        # Analysis Options Group
        options_group = QGroupBox("Analysis Options")
        options_layout = QVBoxLayout()
        
        # Analysis type checkboxes
        self.sentiment_check = QCheckBox("Sentiment Analysis")
        self.topics_check = QCheckBox("Topic Modeling")
        self.patterns_check = QCheckBox("Pattern Detection")
        self.metrics_check = QCheckBox("Key Metrics")
        
        options_layout.addWidget(self.sentiment_check)
        options_layout.addWidget(self.topics_check)
        options_layout.addWidget(self.patterns_check)
        options_layout.addWidget(self.metrics_check)
        
        # Advanced options
        advanced_layout = QHBoxLayout()
        advanced_layout.addWidget(QLabel("Topics:"))
        self.topics_spin = QSpinBox()
        self.topics_spin.setRange(3, 20)
        self.topics_spin.setValue(5)
        advanced_layout.addWidget(self.topics_spin)
        
        advanced_layout.addSpacing(20)
        
        advanced_layout.addWidget(QLabel("Min. Confidence:"))
        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(50, 100)
        self.confidence_spin.setValue(80)
        self.confidence_spin.setSuffix("%")
        advanced_layout.addWidget(self.confidence_spin)
        
        options_layout.addLayout(advanced_layout)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Progress Section
        progress_group = QGroupBox("Analysis Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        progress_layout.addWidget(self.status_text)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("Start Analysis")
        self.analyze_btn.clicked.connect(self._start_analysis)
        button_layout.addWidget(self.analyze_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        
    def _start_analysis(self):
        """Start the analysis process."""
        # Collect analysis parameters
        params = {
            'source': self.source_combo.currentText(),
            'date_range': self.date_combo.currentText(),
            'analysis_types': {
                'sentiment': self.sentiment_check.isChecked(),
                'topics': self.topics_check.isChecked(),
                'patterns': self.patterns_check.isChecked(),
                'metrics': self.metrics_check.isChecked()
            },
            'num_topics': self.topics_spin.value(),
            'min_confidence': self.confidence_spin.value() / 100
        }
        
        # Update UI state
        self.analyze_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_text.clear()
        
        # Emit signal to start analysis
        self.analysis_requested.emit(params)
        
    def update_progress(self, value: int, status: str):
        """Update progress bar and status text."""
        self.progress_bar.setValue(value)
        self.status_text.append(status)
        
    def analysis_complete(self):
        """Handle analysis completion."""
        self.analyze_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.export_btn.setEnabled(True)
        self.status_text.append("Analysis complete!")
        
    def analysis_error(self, error: str):
        """Handle analysis error."""
        self.analyze_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_text.append(f"Error: {error}")
        
    def stop_analysis(self):
        """Stop the current analysis."""
        # Implement stop logic
        pass