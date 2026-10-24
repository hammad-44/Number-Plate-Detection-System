from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem
from qfluentwidgets import (CardWidget, TitleLabel, StrongBodyLabel, PrimaryPushButton, 
                            PushButton, LineEdit, FluentIcon as FIF, InfoBar)
from PyQt5.QtCore import Qt
from core.signals import signal_bus

class Watchlist(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setObjectName('watchlistInterface')
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        layout.addWidget(TitleLabel("Watchlist Manager", self))
        
        # Add New
        add_card = CardWidget(self)
        add_layout = QHBoxLayout(add_card)
        
        self.input_field = LineEdit(self)
        self.input_field.setPlaceholderText("Enter Plate Number (e.g. ABC 1234 or LE-123)")
        self.input_field.setClearButtonEnabled(True)
        
        self.add_btn = PrimaryPushButton("Add to Watchlist", self, FIF.ADD)
        self.add_btn.clicked.connect(self.add_plate)
        
        add_layout.addWidget(self.input_field)
        add_layout.addWidget(self.add_btn)
        
        layout.addWidget(add_card)
        
        # List
        list_card = CardWidget(self)
        list_layout = QVBoxLayout(list_card)
        list_layout.addWidget(StrongBodyLabel("Current Watchlist", self))
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 6px; padding: 5px;")
        list_layout.addWidget(self.list_widget)
        
        # Remove Button
        self.remove_btn = PushButton("Remove Selected", self, FIF.DELETE)
        self.remove_btn.clicked.connect(self.remove_selected)
        list_layout.addWidget(self.remove_btn)
        
        layout.addWidget(list_card)
        layout.addStretch()

    def load_data(self):
        self.list_widget.clear()
        plates = self.db.get_watchlist()
        for plate in plates:
            self.list_widget.addItem(plate)

    def add_plate(self):
        text = self.input_field.text().strip().upper()
        if text:
            success = self.db.add_to_watchlist(text)
            if success:
                self.input_field.clear()
                self.load_data()
                signal_bus.database_updated.emit()
                InfoBar.success('Added', f"Added {text} to watchlist", parent=self)
            else:
                InfoBar.warning('Duplicate', f"{text} already in watchlist", parent=self)

    def remove_selected(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            number = current_item.text()
            self.db.remove_from_watchlist(number)
            self.load_data()
            signal_bus.database_updated.emit()
            InfoBar.success('Removed', f"Removed {number} from watchlist", parent=self)
