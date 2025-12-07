from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidgetItem, QHeaderView
from qfluentwidgets import TableWidget
from datetime import datetime

from core.signals import signal_bus

class Records(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setObjectName('recordsInterface')
        self.init_ui()
        
        # Connect signal
        signal_bus.database_updated.connect(self.refresh_data)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Table
        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['ID', 'Number Plate', 'Confidence', 'Timestamp', 'Source'])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        
        layout.addWidget(self.table)
        
        self.refresh_data()

    def refresh_data(self):
        records = self.db.get_all_records()
        self.table.setRowCount(len(records))
        
        for i, row in enumerate(records):
            # ID
            self.table.setItem(i, 0, QTableWidgetItem(str(row.id)))
            # Number
            self.table.setItem(i, 1, QTableWidgetItem(row.number_text))
            # Confidence
            self.table.setItem(i, 2, QTableWidgetItem(f"{row.confidence:.2f}"))
            # Timestamp
            ts = row.timestamp.strftime("%Y-%m-%d %H:%M:%S") if row.timestamp else ""
            self.table.setItem(i, 3, QTableWidgetItem(ts))
            # Source
            self.table.setItem(i, 4, QTableWidgetItem(str(row.source_type)))
