from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from qfluentwidgets import (CardWidget, TitleLabel, BodyLabel, HyperlinkButton, 
                            StrongBodyLabel, FluentIcon as FIF)
from PyQt5.QtCore import Qt

class HelpPage(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        # db not used but kept for signature consistency
        self.setObjectName('helpInterface')
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # App Info
        card = CardWidget(self)
        c_layout = QVBoxLayout(card)
        
        c_layout.addWidget(TitleLabel("Number Plate Detection System", self))
        c_layout.addWidget(StrongBodyLabel("Version 1.0.0 (Pro)", self))
        c_layout.addWidget(BodyLabel("AI-Powered Vehicle Identification Software.", self))
        
        c_layout.addSpacing(20)
        c_layout.addWidget(StrongBodyLabel("Features:", self))
        c_layout.addWidget(BodyLabel("- Real-time Camera Detection", self))
        c_layout.addWidget(BodyLabel("- Video/Image File Scanning", self))
        c_layout.addWidget(BodyLabel("- Automatic OCR & Data Logging", self))
        c_layout.addWidget(BodyLabel("- Pakistani License Plate Optimized", self))
        
        c_layout.addSpacing(20)
        c_layout.addWidget(StrongBodyLabel("Credits:", self))
        c_layout.addWidget(BodyLabel("Developed by Hammad Haider", self))
        
        layout.addWidget(card)
        layout.addStretch()
