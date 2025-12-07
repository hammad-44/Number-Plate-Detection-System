from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (PrimaryPushButton, PushButton, ComboBox, 
                            StrongBodyLabel, CardWidget, FluentIcon as FIF)
import cv2

class LiveFeed(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.video_thread = None
        self.detector = None
        self.detector = None
        self.ocr = None
        self.is_running = False
        self.setObjectName('liveFeedInterface')
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.source_combo = ComboBox()
        self.source_combo.addItems(["Camera (Webcam)", "RTSP Stream (Enter URL)"]) # Simple for now
        self.start_btn = PrimaryPushButton("Start Camera", self, FIF.PLAY)
        self.stop_btn = PushButton("Stop", self, FIF.PAUSE)
        self.stop_btn.setEnabled(False)
        
        controls_layout.addWidget(self.source_combo)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Display Area
        self.display_card = CardWidget(self)
        display_layout = QVBoxLayout(self.display_card)
        self.video_label = QLabel("Camera Feed")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #202020; color: #808080;")
        self.video_label.setMinimumSize(640, 480)
        
        display_layout.addWidget(self.video_label)
        layout.addWidget(self.display_card)
        
        # Results Overlay (Simple Label for now)
        self.result_label = StrongBodyLabel("Last Detected: -", self)
        layout.addWidget(self.result_label)

        # Signals
        self.start_btn.clicked.connect(self.start_feed)
        self.stop_btn.clicked.connect(self.stop_feed)

    def set_engines(self, detector, ocr):
        self.detector = detector
        self.ocr = ocr

    def start_feed(self):
        if self.is_running: return
        
        # Initialize engines if not already passed (lazy load)
        if not self.detector:
            try:
                from core.detector import PlateDetector
                # Determine path relative to main
                model_path = 'models/best.onnx' 
                self.detector = PlateDetector(model_path)
            except Exception as e:
                print(f"Detector init failed: {e}")

        if not self.ocr:
            try:
                from core.ocr import OCREngine
                self.ocr = OCREngine()
            except Exception as e:
                print(f"OCR init failed: {e}")

        from core.video_thread import VideoThread
        
        source = 0 # Default webcam
        if self.source_combo.currentIndex() == 1:
             # Basic RTSP support dialog could go here
             pass 
        
        self.video_thread = VideoThread(source=source)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.start()
        
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.frame_count = 0 

    def stop_feed(self):
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.video_label.setText("Stopped")

    @pyqtSlot(object)
    def update_image(self, cv_img):
        """Updates the video_label with a new opencv image"""
        self.frame_count += 1
        
        # Optimization: Detect every 5th frame to save CPU
        # But we must draw boxes from previous detection if we skip?
        # For simplicity, we just won't update boxes on skipped frames, or we store last boxes.
        
        if self.frame_count % 5 == 0 and self.detector and self.ocr:
            # Run Detection
            results = self.detector.detect(cv_img)
            self.last_results = results # Store for drawing
            
            for res in results:
                x1, y1, x2, y2 = res['box']
                # Crop for OCR
                # Clamp to frame
                h, w, _ = cv_img.shape
                x1, y1 = max(0, int(x1)), max(0, int(y1))
                x2, y2 = min(w, int(x2)), min(h, int(y2))
                
                if x2 > x1 and y2 > y1:
                    plate_crop = cv_img[y1:y2, x1:x2]
                    text = self.ocr.recognize(plate_crop)
                    
                    if len(text) > 3: # Basic noise filter
                        res['text'] = text
                        self.result_label.setText(f"Last Detected: {text} ({res['score']:.2f})")
                        
                        # Save to DB (Avoid spamming same plate? - Simple naive check)
                        # In production, check timestamp of last entry for this number
                        self.db.add_plate(text, res['score'], "", "", "live", "camera")
                        
                        # Trigger UI Refresh
                        from core.signals import signal_bus
                        signal_bus.database_updated.emit()
                        
                        print(f"Detected: {text}")

        # Draw rects
        if hasattr(self, 'last_results'):
            for res in self.last_results:
                x1, y1, x2, y2 = [int(v) for v in res['box']]
                cv2.rectangle(cv_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                if 'text' in res:
                    cv2.putText(cv_img, res['text'], (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        qt_img = self.convert_cv_qt(cv_img)
        self.video_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
