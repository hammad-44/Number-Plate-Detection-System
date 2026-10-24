import sys
import os

# Fix working directory, sys.path, and Windows DLL directories BEFORE importing native extensions
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    MEI_DIR = getattr(sys, '_MEIPASS', APP_DIR)
    os.chdir(APP_DIR)
    sys.path.insert(0, MEI_DIR)
    
    # Critical: Register DLL directories for onnxruntime, torch, numpy, and native extensions on Windows
    if sys.platform == 'win32':
        candidate_dirs = [
            APP_DIR,
            MEI_DIR,
            os.path.join(MEI_DIR, 'onnxruntime', 'capi'),
            os.path.join(MEI_DIR, 'onnxruntime'),
            os.path.join(MEI_DIR, 'numpy.libs'),
            os.path.join(MEI_DIR, 'torch', 'lib'),
            os.path.join(MEI_DIR, 'PyQt5', 'Qt5', 'bin'),
            os.path.join(APP_DIR, 'PyQt5', 'Qt5', 'bin'),
        ]
        for d in candidate_dirs:
            if os.path.isdir(d):
                if hasattr(os, 'add_dll_directory'):
                    try:
                        os.add_dll_directory(d)
                    except Exception:
                        pass
                os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(APP_DIR)
    sys.path.insert(0, APP_DIR)

import numpy
import onnxruntime

from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    app = QApplication(sys.argv)
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
