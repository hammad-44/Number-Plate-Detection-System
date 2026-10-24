from PyQt5.QtCore import Qt, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (PrimaryPushButton, PushButton, ComboBox, LineEdit,
                            StrongBodyLabel, CardWidget, FluentIcon as FIF,
                            BodyLabel, SubtitleLabel, InfoBadge, InfoBar, InfoBarPosition)
from ui.pages.vehicles import VehicleInfoDialog
from core.signals import signal_bus
import cv2
import numpy as np
import time
import re

class DetectionWorker(QThread):
    result_ready = pyqtSignal(list, float)  # results, processing_time

    def __init__(self, detector, ocr):
        super().__init__()
        self.detector = detector
        self.ocr = ocr
        self.pending_frame = None
        self.running = True
        self.is_busy = False

    def process_frame(self, frame):
        if not self.is_busy:
            self.pending_frame = frame.copy() # Copy to avoid race conditions with display
            if not self.isRunning():
                self.start()

    def run(self):
        while self.running:
            if self.pending_frame is not None:
                self.is_busy = True
                frame = self.pending_frame
                self.pending_frame = None
                
                start_time = time.time()
                try:
                    results = self.detector.detect(frame)
                    
                    # Refine results with OCR
                    final_results = []
                    for res in results:
                        x1, y1, x2, y2 = res['box']
                        h, w, _ = frame.shape
                        x1, y1 = max(0, int(x1)), max(0, int(y1))
                        x2, y2 = min(w, int(x2)), min(h, int(y2))
                        
                        if x2 > x1 and y2 > y1:
                            plate_crop = frame[y1:y2, x1:x2]
                            text = self.ocr.recognize(plate_crop)
                            res['text'] = text
                            final_results.append(res)
                            
                    process_time = time.time() - start_time
                    self.result_ready.emit(final_results, process_time)
                    
                except Exception as e:
                    print(f"Detection error: {e}")
                
                self.is_busy = False
            else:
                time.sleep(0.01) # Short sleep to prevent busy waiting

    def stop(self):
        self.running = False
        self.wait()

class LiveFeed(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.video_thread = None
        self.detection_worker = None
        self.detector = None
        self.ocr = None
        self.last_results = []
        self.last_popup_plate = ""
        self.last_popup_time = 0
        self.is_running = False
        self.setObjectName('liveFeedInterface')
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.source_combo = ComboBox()
        self.source_combo.addItems(["Camera (Webcam)", "RTSP Stream (Enter URL)"])
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        
        self.rtsp_input = LineEdit(self)
        self.rtsp_input.setPlaceholderText("rtsp://username:password@ip:port/stream")
        self.rtsp_input.setFixedWidth(280)
        self.rtsp_input.setClearButtonEnabled(True)
        self.rtsp_input.hide()
        
        self.start_btn = PrimaryPushButton("Start Feed", self, FIF.PLAY)
        self.stop_btn = PushButton("Stop", self, FIF.PAUSE)
        self.stop_btn.setEnabled(False)
        
        controls_layout.addWidget(self.source_combo)
        controls_layout.addWidget(self.rtsp_input)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Display Area
        self.display_card = CardWidget(self)
        display_layout = QVBoxLayout(self.display_card)
        self.video_label = QLabel("Camera Feed")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #202020; color: #808080; border-radius: 8px;")
        self.video_label.setMinimumSize(640, 480)
        
        display_layout.addWidget(self.video_label)
        layout.addWidget(self.display_card)
        
        layout.addStretch()

        # Signals
        self.start_btn.clicked.connect(self.start_feed)
        self.stop_btn.clicked.connect(self.stop_feed)
        signal_bus.conf_updated.connect(self.on_conf_updated)

    def on_source_changed(self, idx):
        if idx == 1:
            self.rtsp_input.show()
        else:
            self.rtsp_input.hide()

    def on_conf_updated(self, val):
        if self.detector:
            self.detector.conf_thres = val

    def set_engines(self, detector, ocr):
        self.detector = detector
        self.ocr = ocr

    def start_feed(self):
        if self.is_running: return
        
        # Initialize engines if not already passed
        if not self.detector:
            try:
                from core.detector import PlateDetector
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

        # Start Video Thread
        from core.video_thread import VideoThread
        if self.source_combo.currentIndex() == 1:
            rtsp_url = self.rtsp_input.text().strip()
            source = rtsp_url if rtsp_url else 0
        else:
            source = 0 
        
        self.video_thread = VideoThread(source=source)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.start()
        
        # Start Detection Worker
        self.detection_worker = DetectionWorker(self.detector, self.ocr)
        self.detection_worker.result_ready.connect(self.on_detection_result)
        self.detection_worker.start()
        
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_feed(self):
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        
        if self.detection_worker:
            self.detection_worker.stop()
            self.detection_worker = None
        
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.video_label.setText("Stopped")
        self.last_results = [] # Clear results

    @pyqtSlot(object)
    def update_image(self, cv_img):
        """Updates the video_label with a new opencv image at high FPS"""
        if not self.is_running: return

        # Send to detection worker (non-blocking, only if worker is ready)
        if self.detection_worker:
            self.detection_worker.process_frame(cv_img)

        # Draw existing results (from last detection)
        for res in self.last_results:
            x1, y1, x2, y2 = [int(v) for v in res['box']]
            h, w, _ = cv_img.shape
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            cv2.rectangle(cv_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            if 'text' in res and res['text'].strip():
                cv2.putText(cv_img, res['text'], (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        qt_img = self.convert_cv_qt(cv_img)
        self.video_label.setPixmap(qt_img)

    @pyqtSlot(list, float)
    def on_detection_result(self, results, process_time):
        """Called when detection thread finishes a frame"""
        self.last_results = results
        
        for res in results:
            text = res.get('text', '').strip()
            score = res.get('score', 0.0)
            
            if len(text) > 3:
                clean_text = re.sub(r'[^A-Z0-9]', '', text.upper())
                
                # Cooldown logic for alerts (8 seconds per plate)
                current_time = time.time()
                is_new_plate = clean_text != self.last_popup_plate
                is_cooldown_over = (current_time - self.last_popup_time) > 8
                
                if is_new_plate or is_cooldown_over:
                    self.last_popup_plate = clean_text
                    self.last_popup_time = current_time
                    
                    # Look up vehicle in DB
                    vehicle = self.db.get_vehicle(text)
                    
                    # Check Watchlist
                    watchlist = self.db.get_watchlist()
                    is_in_watchlist = clean_text in [re.sub(r'[^A-Z0-9]', '', p.upper()) for p in watchlist]
                    is_stolen = vehicle is not None and vehicle.status == "Stolen"
                    
                    # Non-blocking notification banner (keeps live video smooth)
                    if is_in_watchlist or is_stolen:
                        status_str = "STOLEN" if is_stolen else "ON WATCHLIST"
                        owner_str = vehicle.owner_name if vehicle else "Unregistered"
                        InfoBar.error(
                            title=f"🚨 SECURITY ALERT: {status_str} VEHICLE!",
                            content=f"Plate: {text} | Owner: {owner_str}",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=7000,
                            parent=self
                        )
                    elif vehicle:
                        InfoBar.success(
                            title=f"Vehicle Verified: {text}",
                            content=f"Owner: {vehicle.owner_name} | {vehicle.make} {vehicle.model} ({vehicle.status})",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP_RIGHT,
                            duration=3500,
                            parent=self
                        )
                    else:
                        InfoBar.info(
                            title=f"Detection: {text}",
                            content="Vehicle is not registered in the system.",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP_RIGHT,
                            duration=3000,
                            parent=self
                        )
                
                # Log to DB
                self.db.add_plate(text, score, "", "", "live", "camera")
                signal_bus.database_updated.emit()

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        # Explicit .copy() to preserve memory safety when crossing threads/buffers
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        p = convert_to_Qt_format.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
