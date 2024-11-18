# src/gui/widgets/forum_tab.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLineEdit, QLabel, QComboBox,
    QTableView, QGroupBox, QFormLayout, QSpinBox,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem

from ..forum_scraper import CommonwealthScraper, DiscourseScraper
from ..utils import show_error_dialog, show_info_dialog, set_table_style

class ForumTab(QWidget):
    """Widget for managing forum data scraping."""
    
    # Signals for scraping status
    scrape_started = pyqtSignal(str)  # Emitted when scraping starts
    scrape_finished = pyqtSignal()   # Emitted when scraping finishes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.commonwealth_scraper = None
        self.discourse_scraper = None
        self.model = QStandardItemModel()
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different forum types
        self.tab_widget = QTabWidget()
        
        # Add Commonwealth tab
        self.commonwealth_tab = self._create_commonwealth_tab()
        self.tab_widget.addTab(self.commonwealth_tab, "Commonwealth")
        
        # Add Discourse tab
        self.discourse_tab = self._create_discourse_tab()
        self.tab_widget.addTab(self.discourse_tab, "Discourse")
        
        layout.addWidget(self.tab_widget)
        
        # Results table
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableView()
        self.results_table.setModel(self.model)
        set_table_style(self.results_table)
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
    def _create_commonwealth_tab(self) -> QWidget:
        """Create the Commonwealth scraping interface tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Settings group
        settings_group = QGroupBox("Commonwealth Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.community_input = QLineEdit()
        settings_layout.addRow("Community ID:", self.community_input)
        
        self.discussions_limit = QSpinBox()
        self.discussions_limit.setRange(1, 1000)
        self.discussions_limit.setValue(100)
        settings_layout.addRow("Max Discussions:", self.discussions_limit)
        
        self.commonwealth_scrape_button = QPushButton("Scrape Discussions")
        self.commonwealth_scrape_button.clicked.connect(self._scrape_commonwealth)
        settings_layout.addRow(self.commonwealth_scrape_button)
        
        layout.addWidget(settings_group)
        
        # Filtering group
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout(filter_group)
        
        self.date_filter = QComboBox()
        self.date_filter.addItems(["All Time", "Last Week", "Last Month", "Last Year"])
        filter_layout.addRow("Date Range:", self.date_filter)
        
        self.sort_by = QComboBox()
        self.sort_by.addItems(["Newest", "Most Comments", "Most Reactions"])
        filter_layout.addRow("Sort By:", self.sort_by)
        
        layout.addWidget(filter_group)
        
        return widget
        
    def _create_discourse_tab(self) -> QWidget:
        """Create the Discourse scraping interface tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Settings group
        settings_group = QGroupBox("Discourse Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.forum_url = QLineEdit()
        settings_layout.addRow("Forum URL:", self.forum_url)
        
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        settings_layout.addRow("API Key:", self.api_key)
        
        self.api_username = QLineEdit()
        settings_layout.addRow("API Username:", self.api_username)
        
        self.category_id = QSpinBox()
        self.category_id.setSpecialValueText("All Categories")
        settings_layout.addRow("Category ID:", self.category_id)
        
        self.topics_limit = QSpinBox()
        self.topics_limit.setRange(1, 1000)
        self.topics_limit.setValue(100)
        settings_layout.addRow("Max Topics:", self.topics_limit)
        
        self.discourse_scrape_button = QPushButton("Scrape Topics")
        self.discourse_scrape_button.clicked.connect(self._scrape_discourse)
        settings_layout.addRow(self.discourse_scrape_button)
        
        layout.addWidget(settings_group)
        
        return widget
        
    def _scrape_commonwealth(self):
        """Handle Commonwealth scraping."""
        community = self.community_input.text().strip()
        if not community:
            show_error_dialog(self, "Please enter a community ID")
            return
            
        try:
            self._show_loading(True)
            self.scrape_started.emit("commonwealth")
            
            # Initialize scraper if needed
            if not self.commonwealth_scraper:
                self.commonwealth_scraper = CommonwealthScraper({})
            
            # Clear current results
            self.model.clear()
            self.model.setHorizontalHeaderLabels([
                "ID", "Title", "Author", "Created", "Comments", "URL"
            ])
            
            # Fetch discussions
            row = 0
            for discussion in self.commonwealth_scraper.get_discussions(community):
                if row >= self.discussions_limit.value():
                    break
                    
                self.model.appendRow([
                    QStandardItem(str(discussion['id'])),
                    QStandardItem(discussion['title']),
                    QStandardItem(discussion['author']),
                    QStandardItem(discussion['created_at']),
                    QStandardItem(str(discussion['comments_count'])),
                    QStandardItem(discussion['url'])
                ])
                row += 1
                
                # Update progress
                progress = min(100, int((row / self.discussions_limit.value()) * 100))
                self.progress_bar.setValue(progress)
            
            show_info_dialog(self, f"Successfully scraped {row} discussions")
            
        except Exception as e:
            show_error_dialog(self, f"Error scraping Commonwealth: {str(e)}")
            
        finally:
            self._show_loading(False)
            self.scrape_finished.emit()
            
    def _scrape_discourse(self):
        """Handle Discourse scraping."""
        forum_url = self.forum_url.text().strip()
        if not forum_url:
            show_error_dialog(self, "Please enter the forum URL")
            return
            
        try:
            self._show_loading(True)
            self.scrape_started.emit("discourse")
            
            # Initialize scraper if needed
            if not self.discourse_scraper:
                self.discourse_scraper = DiscourseScraper({})
            
            # Configure scraper
            self.discourse_scraper.configure(
                forum_url,
                self.api_key.text().strip(),
                self.api_username.text().strip()
            )
            
            # Clear current results
            self.model.clear()
            self.model.setHorizontalHeaderLabels([
                "ID", "Title", "Author", "Created", "Views", "Posts", "URL"
            ])
            
            # Fetch topics
            row = 0
            category_id = self.category_id.value() if self.category_id.value() > 0 else None
            for topic in self.discourse_scraper.get_topics(category_id):
                if row >= self.topics_limit.value():
                    break
                    
                self.model.appendRow([
                    QStandardItem(str(topic['id'])),
                    QStandardItem(topic['title']),
                    QStandardItem(str(topic['author'])),
                    QStandardItem(topic['created_at']),
                    QStandardItem(str(topic['views'])),
                    QStandardItem(str(topic['posts_count'])),
                    QStandardItem(topic['url'])
                ])
                row += 1
                
                # Update progress
                progress = min(100, int((row / self.topics_limit.value()) * 100))
                self.progress_bar.setValue(progress)
            
            show_info_dialog(self, f"Successfully scraped {row} topics")
            
        except Exception as e:
            show_error_dialog(self, f"Error scraping Discourse: {str(e)}")
            
        finally:
            self._show_loading(False)
            self.scrape_finished.emit()
            
    def _show_loading(self, show: bool):
        """Show/hide loading indicators."""
        self.progress_bar.setVisible(show)
        self.commonwealth_scrape_button.setEnabled(not show)
        self.discourse_scrape_button.setEnabled(not show)
        
        if show:
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setValue(100)

    def save_results(self, filepath: str):
        """
        Save scraped results to file.
        
        Args:
            filepath: Path to save file
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write headers
                headers = []
                for col in range(self.model.columnCount()):
                    headers.append(self.model.headerData(col, Qt.Orientation.Horizontal))
                f.write('\t'.join(headers) + '\n')
                
                # Write data
                for row in range(self.model.rowCount()):
                    row_data = []
                    for col in range(self.model.columnCount()):
                        item = self.model.item(row, col)
                        row_data.append(item.text() if item else '')
                    f.write('\t'.join(row_data) + '\n')
                    
            show_info_dialog(self, f"Results saved to {filepath}")
            
        except Exception as e:
            show_error_dialog(self, f"Error saving results: {str(e)}")
            
    def clear_results(self):
        """Clear the results table."""
        self.model.clear()