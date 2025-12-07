import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon as FIF, SplashScreen

from ui.pages.dashboard import Dashboard
from ui.pages.live_feed import LiveFeed
from ui.pages.media_scan import MediaScan
from ui.pages.records import Records
from ui.pages.settings import Settings
from ui.pages.analytics import Analytics
from ui.pages.watchlist import Watchlist
from ui.pages.help import HelpPage
from database.db_manager import DatabaseManager

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize Backend
        self.db = DatabaseManager('npds_data.db')
        
        # Setup Window
        self.setWindowTitle("Number Plate Detection System")
        self.resize(1100, 750)
        
        # Create Sub-Interfaces
        self.dashboard_interface = Dashboard(self.db)
        self.live_interface = LiveFeed(self.db)
        self.scan_interface = MediaScan(self.db)
        self.records_interface = Records(self.db)
        self.analytics_interface = Analytics(self.db)
        self.watchlist_interface = Watchlist(self.db)
        self.help_interface = HelpPage(self.db)
        self.settings_interface = Settings(self.db)
        
        # Add Navigation Items
        self.init_navigation()
        
        # Apply Theme (Optional)
        # qfluentwidgets.setTheme(qfluentwidgets.Theme.DARK)

    def init_navigation(self):
        self.addSubInterface(self.dashboard_interface, FIF.HOME, 'Dashboard')
        self.addSubInterface(self.live_interface, FIF.VIDEO, 'Live Feed')
        self.addSubInterface(self.scan_interface, FIF.PHOTO, 'Media Scan')
        self.addSubInterface(self.records_interface, FIF.FOLDER, 'Records')
        self.addSubInterface(self.analytics_interface, FIF.TILES, 'Analytics')
        self.addSubInterface(self.watchlist_interface, FIF.SEARCH, 'Watchlist')
        
        self.addSubInterface(self.settings_interface, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.help_interface, FIF.INFO, 'Example Help', NavigationItemPosition.BOTTOM)
        
        # Add some settings at bottom if needed
        # self.addSubInterface(self.setting_interface, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

if __name__ == '__main__':
    # Enable High DPI scaling
    # QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
