from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt5.QtCore import Qt
from qfluentwidgets import (ScrollArea, SettingCardGroup, SettingCard, PushSettingCard, 
                            FluentIcon as FIF, MessageBox, InfoBar, InfoBarPosition)
from core.signals import signal_bus

class Settings(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setObjectName('settingsInterface')
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area
        self.scroll = ScrollArea(self)
        self.layout.addWidget(self.scroll)
        self.scroll_widget = QWidget()
        self.scroll.setWidget(self.scroll_widget)
        self.scroll.setWidgetResizable(True)
        
        self.v_layout = QVBoxLayout(self.scroll_widget)
        self.v_layout.setContentsMargins(30, 30, 30, 30)
        self.v_layout.setSpacing(20)
        
        # AI Config Group
        self.ai_group = SettingCardGroup("AI Configuration", self.scroll_widget)
        self.v_layout.addWidget(self.ai_group)
        
        # Custom Confidence Card (Manual implementation)
        self.conf_card = SettingCard(
            FIF.VIEW, "Confidence Threshold", "Adjust detection sensitivity (0.10 - 0.90)",
            self.ai_group
        )
        
        # Add a slider to the card
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(10, 90) # 0.1 to 0.9
        self.slider.setValue(50)
        self.slider.setFixedWidth(200)
        
        self.val_label = QLabel("0.50")
        self.val_label.setFixedWidth(40)
        
        self.conf_card.hBoxLayout.addWidget(self.val_label)
        self.conf_card.hBoxLayout.addSpacing(10)
        self.conf_card.hBoxLayout.addWidget(self.slider)
        self.conf_card.hBoxLayout.addSpacing(20)
        
        self.slider.valueChanged.connect(self.on_conf_change)
        
        self.ai_group.addSettingCard(self.conf_card)
        
        # Database Group
        self.db_group = SettingCardGroup("Data Management", self.scroll_widget)
        self.v_layout.addWidget(self.db_group)
        
        self.clear_card = PushSettingCard(
            "Clear", FIF.DELETE,
            "Clear Database", "Permanently remove all detection logs.",
            self.db_group
        )
        self.clear_card.clicked.connect(self.clear_database)
        self.db_group.addSettingCard(self.clear_card)
        
        self.v_layout.addStretch()

    def on_conf_change(self, value):
        fval = value / 100.0
        self.val_label.setText(f"{fval:.2f}")
        signal_bus.conf_updated.emit(fval)

    def clear_database(self):
        w = MessageBox(
            "Clear All Records?",
            "Are you sure you want to permanently delete all detection logs? This cannot be undone.",
            self
        )
        if w.exec():
            if hasattr(self.db, 'clear_all_records'):
                self.db.clear_all_records()
                signal_bus.database_updated.emit()
                InfoBar.success(
                    title="Database Cleared",
                    content="All detection logs have been removed.",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            else:
                InfoBar.error("Error", "DB Manager missing clear function", parent=self)
