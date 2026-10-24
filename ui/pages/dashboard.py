from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (CardWidget, TitleLabel, BodyLabel, 
                            StrongBodyLabel, IconWidget, FluentIcon as FIF,
                            InfoBadge)
from core.signals import signal_bus

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
        
        self.total_card, self.total_val_label = self.create_stat_card("Total Detections", "0", FIF.FOLDER)
        self.today_card, self.today_val_label = self.create_stat_card("Today's Detections", "0", FIF.DATE_TIME)
        self.status_card, self.status_val_label = self.create_stat_card("System Status", "Online", FIF.HEART)
        
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
        
        self.content_layout.addWidget(self.msgs_card, 2)

        # Right Column: Quick Overview & Health
        self.right_col_layout = QVBoxLayout()
        self.content_layout.addLayout(self.right_col_layout, 1)
        
        # System Overview
        self.health_card = CardWidget(self)
        health_layout = QVBoxLayout(self.health_card)
        health_layout.addWidget(StrongBodyLabel("Database Overview", self))
        
        self.db_vehicles_label = BodyLabel("Registered Vehicles: 0", self)
        self.db_watchlist_label = BodyLabel("Watchlist Items: 0", self)
        self.engine_label = BodyLabel("AI Inference: ONNX Runtime", self)
        
        health_layout.addWidget(self.db_vehicles_label)
        health_layout.addWidget(self.db_watchlist_label)
        health_layout.addWidget(self.engine_label)
        
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
        
        v_layout.addWidget(title_label)
        v_layout.addWidget(value_label)
        
        h_layout.addWidget(icon_widget)
        h_layout.addLayout(v_layout)
        
        return card, value_label

    def refresh_stats(self):
        total, today = self.db.get_stats()
        self.total_val_label.setText(str(total))
        self.today_val_label.setText(str(today))
        
        # Update Database Overview
        try:
            num_v = len(self.db.get_all_vehicles())
            num_w = len(self.db.get_watchlist())
            self.db_vehicles_label.setText(f"Registered Vehicles: {num_v}")
            self.db_watchlist_label.setText(f"Watchlist Hotlist: {num_w}")
        except Exception:
            pass
        
        # Update Recent Activity
        while self.recent_list_layout.count():
            child = self.recent_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Fetch last 5
        recents = self.db.get_recent_plates(5)
        for r in recents:
            row = QHBoxLayout()
            badge = InfoBadge.success(r.number_text) if r.number_text != "[Unrecognized]" else InfoBadge.warning("???")
            time_lbl = BodyLabel(r.timestamp.strftime("%H:%M:%S") if r.timestamp else "-")
            
            row.addWidget(badge)
            row.addWidget(time_lbl)
            row.addStretch()
            
            container = QWidget()
            container.setLayout(row)
            self.recent_list_layout.addWidget(container)
