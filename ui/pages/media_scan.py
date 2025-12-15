from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QProgressBar
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qfluentwidgets import PrimaryPushButton, StrongBodyLabel, CardWidget, FluentIcon as FIF, InfoBar, InfoBarPosition
import cv2
import time
import os

class MediaWorker(QThread):
    finished = pyqtSignal(object, int) # QImage (preview), count
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, path, db, detector, ocr):
        super().__init__()
        self.path = path
        self.db = db
        self.detector = detector
        self.ocr = ocr
        self.is_running = True
        
    def run(self):
        try:
            # Init engines if not passed (fallback, but should be passed)
            if not self.detector:
                 from core.detector import PlateDetector
                 self.detector = PlateDetector('models/best.onnx')
            if not self.ocr:
                 from core.ocr import OCREngine
                 self.ocr = OCREngine()
                 
            if not os.path.exists(self.path):
                self.error.emit(f"File not found: {self.path}")
                return

            ext = self.path.split('.')[-1].lower()
            if ext in ['jpg', 'png', 'jpeg', 'bmp']:
                self._process_image()
            elif ext in ['mp4', 'avi', 'mov', 'mkv']:
                self._process_video()
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _process_image(self):
        img = cv2.imread(self.path)
        if img is None:
            self.error.emit("Failed to read image")
            return

        results = self.detector.detect(img)
        count = 0
        
        for res in results:
            x1, y1, x2, y2 = res['box']
            h, w, _ = img.shape
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            
            if x2 > x1 and y2 > y1:
                plate_crop = img[y1:y2, x1:x2]
                text = self.ocr.recognize(plate_crop)
                
                display_text = text if text.strip() else "[Unrecognized]"
                res['text'] = display_text
                
                if self.db:
                    self.db.add_plate(display_text, res['score'], self.path, "", "file", self.path)
                
                # Draw
                color = (0, 255, 0) if text.strip() else (0, 0, 255) 
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
                cv2.putText(img, display_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                count += 1
        
        # Refresh UI once for single image
        if self.db:
            from core.signals import signal_bus
            signal_bus.database_updated.emit()

        self.progress.emit(100)
        
        # Convert for display
        qImg = self._to_qimage(img)
        self.finished.emit(qImg, count)

    def _process_video(self):
        cap = cv2.VideoCapture(self.path)
        if not cap.isOpened():
            self.error.emit("Failed to open video")
            return
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0: total_frames = 1 # Prevent div/0
        
        count = 0
        frame_idx = 0
        last_display_frame = None
        
        # Process every Nth frame to be faster
        SKIP_FRAMES = 5 
        
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_idx += 1
            
            # Update progress
            progress_pct = int((frame_idx / total_frames) * 100)
            self.progress.emit(progress_pct)
            
            if frame_idx % SKIP_FRAMES != 0:
                continue
                
            results = self.detector.detect(frame)
            found_in_frame = False
            
            for res in results:
                x1, y1, x2, y2 = res['box']
                h, w, _ = frame.shape
                x1, y1 = max(0, int(x1)), max(0, int(y1))
                x2, y2 = min(w, int(x2)), min(h, int(y2))
                
                if x2 > x1 and y2 > y1:
                    plate_crop = frame[y1:y2, x1:x2]
                    text = self.ocr.recognize(plate_crop)
                    
                    if len(text) > 3:
                        display_text = text
                        
                        if self.db:
                             # Timestamp can be calculated from frame_idx / fps
                             self.db.add_plate(display_text, res['score'], self.path, "", "file", self.path)
                        
                        count += 1
                        found_in_frame = True
                        
                        # Draw on frame for preview
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            if found_in_frame or last_display_frame is None:
                last_display_frame = frame.copy()

        cap.release()
        
        if self.db:
            from core.signals import signal_bus
            signal_bus.database_updated.emit()
            
        if last_display_frame is not None:
             qImg = self._to_qimage(last_display_frame)
             self.finished.emit(qImg, count)
        else:
             self.finished.emit(None, 0)
             
    def _to_qimage(self, img):
        height, width, channel = img.shape
        bytesPerLine = 3 * width
        qImg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return QImage(qImg.data, width, height, bytesPerLine, QImage.Format_RGB888)

    def stop(self):
        self.is_running = False


class MediaScan(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.worker = None
        self.detector = None
        self.ocr = None
        self.setObjectName('mediaScanInterface')
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        layout.addWidget(StrongBodyLabel("Scan Image or Video File", self))
        
        # File Picker
        self.picker_layout = QHBoxLayout()
        self.upload_btn = PrimaryPushButton("Select Media", self, FIF.FOLDER)
        self.upload_btn.clicked.connect(self.select_file)
        self.path_label = QLabel("No file selected")
        self.path_label.setWordWrap(True)
        
        self.picker_layout.addWidget(self.upload_btn)
        self.picker_layout.addWidget(self.path_label, 1)
        
        layout.addLayout(self.picker_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Preview / Processing Area
        self.preview_card = CardWidget(self)
        self.preview_card.setMinimumHeight(400)
        card_layout = QVBoxLayout(self.preview_card)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.status_label)
        
        # Image Label
        self.image_result_label = QLabel()
        self.image_result_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.image_result_label)
        
        layout.addWidget(self.preview_card)
        layout.addStretch()

    def select_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', 'c:\\', "Media (*.jpg *.png *.mp4 *.avi *.mov *.mkv)")
        if fname:
            self.path_label.setText(fname)
            self.status_label.setText("Preparing...")
            self.process_media(fname)

    def process_media(self, path):
        # Lazy load engines once
        if not self.detector:
            try:
                self.status_label.setText("Loading models (first time only)...")
                # Force UI update 
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                
                from core.detector import PlateDetector
                self.detector = PlateDetector('models/best.onnx')
            except Exception as e:
                self.status_label.setText(f"Model Load Error: {e}")
                return
                
        if not self.ocr:
            try:
                from core.ocr import OCREngine
                self.ocr = OCREngine()
            except Exception as e:
                self.status_label.setText(f"OCR Load Error: {e}")
                return

        # Disable UI
        self.upload_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.setText("Processing... 0%")
        self.image_result_label.clear()
        
        self.worker = MediaWorker(path, self.db, self.detector, self.ocr)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.progress.connect(self.on_progress)
        self.worker.error.connect(self.on_process_error)
        self.worker.start()

    def on_progress(self, val):
        self.progress_bar.setValue(val)
        self.status_label.setText(f"Processing... {val}%")

    def on_process_finished(self, q_img, count):
        self.upload_btn.setEnabled(True)
        self.progress_bar.hide()
        
        if q_img:
            pixmap = QPixmap.fromImage(q_img)
            self.image_result_label.setPixmap(pixmap.scaled(600, 400, Qt.KeepAspectRatio))
        else:
             self.image_result_label.setText("No detections to display or bad file.")
        
        self.status_label.setText(f"Completed! Found {count} plates.")
        
        InfoBar.success(
            title='Processing Complete',
            content=f"Successfully detected {count} Number Plates.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self
        )

    def on_process_error(self, msg):
        self.upload_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"Error: {msg}")
        
        InfoBar.error(
            title='Error',
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=-1,
            parent=self
        )
