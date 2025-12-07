from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QProgressBar
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qfluentwidgets import PrimaryPushButton, StrongBodyLabel, CardWidget, FluentIcon as FIF, InfoBar, InfoBarPosition
import cv2
import time

class MediaWorker(QThread):
    finished = pyqtSignal(object, int) # QImage, count
    error = pyqtSignal(str)
    
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.detector = None
        self.ocr = None
        self.db = None
        
    def set_dependencies(self, db, detector, ocr):
        self.db = db
        self.detector = detector
        self.ocr = ocr

    def run(self):
        try:
            # Init engines if not passed (though ideally passed)
            if not self.detector:
                 from core.detector import PlateDetector
                 self.detector = PlateDetector('models/best.onnx')
            if not self.ocr:
                 from core.ocr import OCREngine
                 self.ocr = OCREngine()
                 
            ext = self.path.split('.')[-1].lower()
            if ext in ['jpg', 'png', 'jpeg']:
                self._process_image()
            elif ext in ['mp4', 'avi', 'mov']:
                self._process_video_stub()
                
        except Exception as e:
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
            
            # Crop
            if x2 > x1 and y2 > y1:
                plate_crop = img[y1:y2, x1:x2]
                text = self.ocr.recognize(plate_crop)
                
                # Logic: Store NO MATTER WHAT
                display_text = text if text.strip() else "[Unrecognized]"
                res['text'] = display_text
                
                # Database Update
                if self.db:
                    self.db.add_plate(display_text, res['score'], self.path, "", "file", self.path)
                    # Refresh UI
                    from core.signals import signal_bus
                    signal_bus.database_updated.emit()
                
                # Draw
                color = (0, 255, 0) if text.strip() else (0, 0, 255) # Green if text, Red if empty
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
                cv2.putText(img, display_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                count += 1

        # Prepare result image
        height, width, channel = img.shape
        bytesPerLine = 3 * width
        qImg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qImg = QImage(qImg.data, width, height, bytesPerLine, QImage.Format_RGB888)
        
        self.finished.emit(qImg, count)

    def _process_video_stub(self):
        # Full video processing in thread is complex, just do 1st frame for now to verify
        cap = cv2.VideoCapture(self.path)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            self.error.emit("Failed to read video")
            return
            
        # Treat as image for the preview
        # In real app, loop through frames
        # Writing temp image to reuse image logic? No, just copy logic or call it
        # Quick hack: Save frame to temp and process? Or refactor.
        # Let's just create a temp logic here for simplicity
        img = frame
        results = self.detector.detect(img)
        count = 0
        for res in results:
             # Minimal logic for video preview
            x1, y1, x2, y2 = res['box']
            h, w, _ = img.shape
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            
            if x2>x1 and y2>y1:
                plate_crop = img[y1:y2, x1:x2]
                text = self.ocr.recognize(plate_crop)
                display_text = text if text.strip() else "[Unrecognized]"
                
                if self.db:
                     self.db.add_plate(display_text, res['score'], self.path, "", "file", self.path)
                
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.putText(img, display_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                count += 1
                
        height, width, channel = img.shape
        bytesPerLine = 3 * width
        qImg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qImg = QImage(qImg.data, width, height, bytesPerLine, QImage.Format_RGB888)
        self.finished.emit(qImg, count)


class MediaScan(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.worker = None
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
        
        self.picker_layout.addWidget(self.upload_btn)
        self.picker_layout.addWidget(self.path_label)
        self.picker_layout.addStretch()
        
        layout.addLayout(self.picker_layout)
        
        # Progress Bar (Hidden by default)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Preview / Processing Area
        self.preview_card = CardWidget(self)
        self.preview_card.setMinimumHeight(400)
        card_layout = QVBoxLayout(self.preview_card)
        self.status_label = QLabel("Ready")
        card_layout.addWidget(self.status_label)
        
        # Image Label
        self.image_result_label = QLabel()
        self.image_result_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.image_result_label)
        
        layout.addWidget(self.preview_card)
        layout.addStretch()

    def select_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', 'c:\\', "Image/Video (*.jpg *.png *.mp4 *.avi)")
        if fname:
            self.path_label.setText(fname)
            self.status_label.setText("Preparing...")
            self.process_media(fname)

    def process_media(self, path):
        # Disable UI
        self.upload_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Processing in background... Please wait.")
        self.image_result_label.clear()
        
        # Init Worker
        # Pass existing engines if possible to save load time? 
        # But engines are not created in this class __init__. 
        # LiveFeed creates them. MainWindow creates them? 
        # Actually engines are in LiveFeed. 
        # We can create new ones here or pass from MainWindow.
        # For thread safety, creating new instances in the thread (or reusing thread-safe ones) is better.
        # ONNX Runtime is thread safe. EasyOCR probably is too.
        # Let's try to lazy load inside thread.
        
        self.worker = MediaWorker(path)
        self.worker.set_dependencies(self.db, None, None) # Let it load its own for now to be safe
        
        self.worker.finished.connect(self.on_process_finished)
        self.worker.error.connect(self.on_process_error)
        self.worker.start()

    def on_process_finished(self, q_img, count):
        self.upload_btn.setEnabled(True)
        self.progress_bar.hide()
        
        pixmap = QPixmap.fromImage(q_img)
        self.image_result_label.setPixmap(pixmap.scaled(600, 400, Qt.KeepAspectRatio))
        
        self.status_label.setText(f"Completed! Found {count} plates (Saved to DB).")
        
        InfoBar.success(
            title='Processing Complete',
            content=f"Successfully detected {count} number plates.",
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
