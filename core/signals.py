from PyQt5.QtCore import QObject, pyqtSignal

class SignalBus(QObject):
    database_updated = pyqtSignal()

# Global singleton
signal_bus = SignalBus()
