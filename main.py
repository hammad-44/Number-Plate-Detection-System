import sys
import os
import onnxruntime # Fix for DLL load failed error

# Fix working directory and path for both dev mode and PyInstaller frozen executable
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    MEI_DIR = getattr(sys, '_MEIPASS', APP_DIR)
    os.chdir(APP_DIR)
    sys.path.insert(0, MEI_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(APP_DIR)
    sys.path.insert(0, APP_DIR)

from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    app = QApplication(sys.argv)
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
