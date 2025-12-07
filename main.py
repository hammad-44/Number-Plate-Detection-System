import sys
import os
import onnxruntime # Fix for DLL load failed error

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    app = QApplication(sys.argv)
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
