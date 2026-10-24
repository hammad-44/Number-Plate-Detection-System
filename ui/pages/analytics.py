from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog
from PyQt5.QtCore import Qt, QDate
from qfluentwidgets import (CardWidget, TitleLabel, StrongBodyLabel, PrimaryPushButton, 
                            FluentIcon as FIF, InfoBar, DatePicker)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime, timedelta
import csv
from core.signals import signal_bus

class Analytics(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setObjectName('analyticsInterface')
        
        # Default date range (last 30 days)
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=30)
        
        self.init_ui()
        self.refresh_chart()
        
        # Auto-refresh when database changes
        signal_bus.database_updated.connect(self.refresh_chart)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        title = TitleLabel("Analytics & Reports", self)
        layout.addWidget(title)
        
        # Date Filter Card
        filter_card = CardWidget(self)
        filter_layout = QHBoxLayout(filter_card)
        
        filter_layout.addWidget(QLabel("Start Date:"))
        self.start_picker = DatePicker(self)
        self.start_picker.setDate(QDate.fromString(self.start_date.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
        self.start_picker.dateChanged.connect(self.validate_dates)
        filter_layout.addWidget(self.start_picker)
        
        filter_layout.addWidget(QLabel("End Date:"))
        self.end_picker = DatePicker(self)
        self.end_picker.setDate(QDate.fromString(self.end_date.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
        self.end_picker.dateChanged.connect(self.validate_dates)
        filter_layout.addWidget(self.end_picker)
        
        self.apply_btn = PrimaryPushButton("Apply Filter", self, FIF.SEARCH)
        self.apply_btn.clicked.connect(self.refresh_chart)
        filter_layout.addWidget(self.apply_btn)
        
        filter_layout.addStretch()
        layout.addWidget(filter_card)
        
        # Chart Card
        chart_card = CardWidget(self)
        chart_card.setMinimumHeight(400)
        c_layout = QVBoxLayout(chart_card)
        c_layout.addWidget(StrongBodyLabel("Detection Trends", self))
        
        # Matplotlib Figure
        self.figure = Figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        c_layout.addWidget(self.canvas)
        
        layout.addWidget(chart_card)
        
        # Export Options
        export_card = CardWidget(self)
        e_layout = QHBoxLayout(export_card)
        e_layout.addWidget(StrongBodyLabel("Data Export", self))
        
        btn = PrimaryPushButton("Export to CSV", self, FIF.DOWNLOAD)
        btn.clicked.connect(self.export_csv)
        e_layout.addWidget(btn)
        e_layout.addStretch()
        
        layout.addWidget(export_card)
        layout.addStretch()

    def validate_dates(self):
        start = self.start_picker.date.toPyDate()
        end = self.end_picker.date.toPyDate()
        
        # Calculate difference
        diff = (end - start).days
        
        # Max 90 days (3 months)
        if diff > 90:
            InfoBar.warning(
                'Date Range Too Large',
                'Maximum range is 3 months (90 days)',
                parent=self
            )
            # Reset to 90 days from start
            self.end_picker.setDate(QDate.fromString((start + timedelta(days=90)).strftime("%Y-%m-%d"), "yyyy-MM-dd"))
        elif diff < 0:
            InfoBar.warning(
                'Invalid Range',
                'End date must be after start date',
                parent=self
            )

    def refresh_chart(self):
        # Get dates
        start = self.start_picker.date.toPyDate()
        end = self.end_picker.date.toPyDate()
        
        # Convert to datetime
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        
        # Fetch data
        data = self.db.get_daily_stats(start_dt, end_dt)
        
        # Prepare data
        dates = []
        counts = []
        for date_str, count in data:
            dates.append(date_str)
            counts.append(count)
        
        # Clear figure
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if data:
            # Modern bar chart
            bars = ax.bar(dates, counts, color='#0078D4', alpha=0.8, edgecolor='#005A9E', linewidth=1.5)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=9)
            
            ax.set_xlabel('Date', fontweight='bold')
            ax.set_ylabel('Detections', fontweight='bold')
            ax.set_title('Daily Detection Count', fontsize=14, fontweight='bold')
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Rotate x labels for better readability
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        else:
            ax.text(0.5, 0.5, 'No data available for selected range',
                   ha='center', va='center', fontsize=12, color='gray')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
        
        self.figure.tight_layout()
        self.canvas.draw()

    def export_csv(self):
        # Get dates
        start = self.start_picker.date.toPyDate()
        end = self.end_picker.date.toPyDate()
        
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        
        # Fetch data
        data = self.db.get_daily_stats(start_dt, end_dt)
        
        if not data:
            InfoBar.warning('No Data', 'No data to export', parent=self)
            return
        
        # Let user choose file destination safely
        default_filename = f"analytics_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Analytics CSV", default_filename, "CSV Files (*.csv)")
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Date', 'Detection Count'])
                for date_str, count in data:
                    writer.writerow([date_str, count])
            
            InfoBar.success(
                'Export Successful',
                f"Data saved to {file_path}",
                parent=self,
                duration=3000
            )
        except Exception as e:
            InfoBar.error('Export Failed', str(e), parent=self)
