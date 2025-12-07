from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from qfluentwidgets import (CardWidget, SimpleCardWidget, TitleLabel, BodyLabel, 
                            StrongBodyLabel, IconWidget, FluentIcon as FIF,
                            InfoBadge, InfoBar)
from core.signals import signal_bus
import random

class Dashboard(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setObjectName('dashboardInterface')
        self.init_ui()
        
        # Connect signal
        signal_bus.database_updated.connect(self.refresh_stats)

    def init_ui(self):
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(30, 30, 30, 30)
        self.v_layout.setSpacing(20)

        # Title
        self.title = TitleLabel("Dashboard", self)
        self.v_layout.addWidget(self.title)

        # 1. Top Stats Row
        self.stats_layout = QHBoxLayout()
        self.v_layout.addLayout(self.stats_layout)
        
        self.total_card = self.create_stat_card("Total Detections", "0", FIF.FOLDER)
        self.today_card = self.create_stat_card("Today's Detections", "0", FIF.DATE_TIME)
        self.status_card = self.create_stat_card("System Status", "Online", FIF.HEART)
        
        self.stats_layout.addWidget(self.total_card)
        self.stats_layout.addWidget(self.today_card)
        self.stats_layout.addWidget(self.status_card)

        # 2. Main Content Area (Split)
        self.content_layout = QHBoxLayout()
        self.v_layout.addLayout(self.content_layout)
        
        # Left Column: Recent Activity
        self.msgs_card = CardWidget(self)
        self.msgs_layout = QVBoxLayout(self.msgs_card)
        self.msgs_layout.addWidget(StrongBodyLabel("Recent Detections", self))
        
        self.recent_list_layout = QVBoxLayout()
        self.msgs_layout.addLayout(self.recent_list_layout)
        self.msgs_layout.addStretch()
        
        self.content_layout.addWidget(self.msgs_card, 2) # Stretch factor 2

        # Right Column: Quick Actions & Health
        self.right_col_layout = QVBoxLayout()
        self.content_layout.addLayout(self.right_col_layout, 1) # Stretch factor 1
        
        # System Health
        self.health_card = CardWidget(self)
        health_layout = QVBoxLayout(self.health_card)
        health_layout.addWidget(StrongBodyLabel("System Health", self))
        
        self.cpu_label = BodyLabel("CPU Usage: Low", self)
        self.mem_label = BodyLabel("Memory: Normal", self)
        
        health_layout.addWidget(self.cpu_label)
        health_layout.addWidget(self.mem_label)
        
        self.right_col_layout.addWidget(self.health_card)
        self.right_col_layout.addStretch()
        
        # Initial Load
        self.refresh_stats()

    def create_stat_card(self, title, value, icon):
        card = CardWidget(self)
        card.setFixedHeight(100)
        
        h_layout = QHBoxLayout(card)
        
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(48, 48)
        
        v_layout = QVBoxLayout()
        title_label = BodyLabel(title)
        value_label = TitleLabel(value)
        value_label.setObjectName("valueLabel") 
        
        v_layout.addWidget(title_label)
        v_layout.addWidget(value_label)
        
        h_layout.addWidget(icon_widget)
        h_layout.addLayout(v_layout)
        
        return card

    def refresh_stats(self):
        total, today = self.db.get_stats()
        
        # Update Cards (Dirty hack to access widgets - assuming structure stays same)
        self.total_card.findChild(TitleLabel, "valueLabel").setText(str(total))
        self.today_card.findChild(TitleLabel, "valueLabel").setText(str(today))
        
        # Update Recent Activity
        # Clear old
        while self.recent_list_layout.count():
            child = self.recent_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Fetch last 5
        recents = self.db.get_recent_plates(5)
        for r in recents:
            row = QHBoxLayout()
            # Badge
            badge = InfoBadge.success(r.number_text) if r.number_text != "[Unrecognized]" else InfoBadge.warning("???")
            time_lbl = BodyLabel(r.timestamp.strftime("%H:%M:%S"))
            
            row.addWidget(badge)
            row.addWidget(time_lbl)
            row.addStretch()
            
            container = QWidget()
            container.setLayout(row)
            self.recent_list_layout.addWidget(container)
