from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import time

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(object) # Emits the frame (numpy array)
    
    def __init__(self, source=0):
        super().__init__()
        self.source = source
        self._run_flag = True
        self.is_video_file = isinstance(source, str)

    def run(self):
        # source can be int (camera index) or string (video path / rtsp URL)
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            print(f"Failed to open video source: {self.source}")
            self.stop()
            return
        
        while self._run_flag:
            ret, frame = cap.read()
            if ret:
                self.change_pixmap_signal.emit(frame)
                
                # If video file, control speed or loop
                if self.is_video_file:
                    time.sleep(1/30) # Approx 30 FPS cap for files
            else:
                if self.is_video_file:
                    # End of file
                    self.stop()
                    break
                else:
                    # Camera read error or stream dropped - sleep briefly to prevent 100% CPU lockup
                    time.sleep(0.05)
        
        cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()
