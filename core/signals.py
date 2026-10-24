from PyQt5.QtCore import QObject, pyqtSignal

class SignalBus(QObject):
    database_updated = pyqtSignal()
    conf_updated = pyqtSignal(float)

# Global singleton
signal_bus = SignalBus()
