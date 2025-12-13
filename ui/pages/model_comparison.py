from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFileDialog, QProgressBar)
from PyQt5.QtGui import QPixmap, QImage
from qfluentwidgets import (CardWidget, PushButton, TitleLabel, BodyLabel, 
                            StrongBodyLabel, FluentIcon as FIF, InfoBar,
                            InfoBarPosition, ComboBox)
import cv2
import numpy as np
from pathlib import Path
import json

from core.model_comparison import ModelComparison


class ComparisonThread(QThread):
    """Thread for running model comparison without blocking UI."""
    
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, input_path, pt_model, onnx_model, is_video, max_frames):
        super().__init__()
        self.input_path = input_path
        self.pt_model = pt_model
        self.onnx_model = onnx_model
        self.is_video = is_video
        self.max_frames = max_frames
    
    def run(self):
        try:
            self.progress.emit("Initializing models...")
            
            # Create comparator
            comparator = ModelComparison(
                pt_model_path=self.pt_model,
                onnx_model_path=self.onnx_model
            )
            
            if self.is_video:
                self.progress.emit(f"Processing video (max {self.max_frames} frames)...")
                comparator.compare_on_video(self.input_path, max_frames=self.max_frames)
                summary = comparator.get_summary()
                # For video, result doesn't include images
                result = {'summary': summary, 'has_images': False}
            else:
                self.progress.emit("Processing image...")
                # For images, get visual results
                comparison_result = comparator.compare_on_image(self.input_path, return_images=True)
                summary = comparator.get_summary()
                result = {
                    'summary': summary,
                    'has_images': True,
                    'pytorch_image': comparison_result['pytorch']['image'],
                    'onnx_image': comparison_result['onnx']['image'],
                    'original_image': comparison_result['original_image']
                }
            
            self.progress.emit("Complete!")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class ModelComparisonPage(QWidget):
    """UI page for comparing PyTorch and ONNX models."""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setObjectName('modelComparisonInterface')
        
        self.pt_model_path = 'models/best.pt'
        self.onnx_model_path = 'models/best.onnx'
        self.input_file = None
        self.comparison_thread = None
        
        self.init_ui()
    
    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        
        # Title
        title = TitleLabel("Model Comparison", self)
        self.main_layout.addWidget(title)
        
        # Description
        desc = BodyLabel(
            "Compare PyTorch (.pt) and ONNX (.onnx) models for timing and accuracy metrics.",
            self
        )
        desc.setWordWrap(True)
        self.main_layout.addWidget(desc)
        
        # Input Selection Card
        self.input_card = self._create_input_card()
        self.main_layout.addWidget(self.input_card)
        
        # Progress Card
        self.progress_card = self._create_progress_card()
        self.main_layout.addWidget(self.progress_card)
        self.progress_card.hide()
        
        # Results Cards
        self.results_layout = QHBoxLayout()
        self.main_layout.addLayout(self.results_layout)
        
        self.pt_results_card = self._create_results_card("PyTorch Model (.pt)")
        self.onnx_results_card = self._create_results_card("ONNX Model (.onnx)")
        
        self.results_layout.addWidget(self.pt_results_card)
        self.results_layout.addWidget(self.onnx_results_card)
        
        self.pt_results_card.hide()
        self.onnx_results_card.hide()
        
        # Image Visualization Card
        self.images_card = self._create_images_card()
        self.main_layout.addWidget(self.images_card)
        self.images_card.hide()
        
        # Comparison Summary Card
        self.comparison_card = self._create_comparison_card()
        self.main_layout.addWidget(self.comparison_card)
        self.comparison_card.hide()
        
        self.main_layout.addStretch()
    
    def _create_input_card(self):
        """Create input selection card."""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        
        layout.addWidget(StrongBodyLabel("Test Input", self))
        
        # File selection
        file_layout = QHBoxLayout()
        
        self.file_label = BodyLabel("No file selected", self)
        self.file_label.setWordWrap(True)
        
        self.select_btn = PushButton(FIF.PHOTO, "Select Image/Video", self)
        self.select_btn.clicked.connect(self.select_input_file)
        
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(self.select_btn)
        
        layout.addLayout(file_layout)
        
        # Max frames for video
        frames_layout = QHBoxLayout()
        frames_layout.addWidget(BodyLabel("Max Frames (for video):", self))
        
        self.frames_combo = ComboBox(self)
        self.frames_combo.addItems(["50", "100", "200", "500", "1000"])
        self.frames_combo.setCurrentIndex(1)  # Default 100
        
        frames_layout.addWidget(self.frames_combo)
        frames_layout.addStretch()
        
        layout.addLayout(frames_layout)
        
        # Run comparison button
        self.run_btn = PushButton(FIF.PLAY, "Run Comparison", self)
        self.run_btn.clicked.connect(self.run_comparison)
        self.run_btn.setEnabled(False)
        
        layout.addWidget(self.run_btn)
        
        return card
    
    def _create_progress_card(self):
        """Create progress indicator card."""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        
        self.progress_label = BodyLabel("Processing...", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        return card
    
    def _create_results_card(self, title):
        """Create results display card for a model."""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        
        layout.addWidget(StrongBodyLabel(title, self))
        
        # Create labels for metrics
        avg_time_label = BodyLabel("Avg Time: -", self)
        min_time_label = BodyLabel("Min Time: -", self)
        max_time_label = BodyLabel("Max Time: -", self)
        total_frames_label = BodyLabel("Total Frames: -", self)
        total_detections_label = BodyLabel("Total Detections: -", self)
        avg_detections_label = BodyLabel("Avg Detections/Frame: -", self)
        avg_confidence_label = BodyLabel("Avg Confidence: -", self)
        
        # Store references
        card.avg_time_label = avg_time_label
        card.min_time_label = min_time_label
        card.max_time_label = max_time_label
        card.total_frames_label = total_frames_label
        card.total_detections_label = total_detections_label
        card.avg_detections_label = avg_detections_label
        card.avg_confidence_label = avg_confidence_label
        
        layout.addWidget(avg_time_label)
        layout.addWidget(min_time_label)
        layout.addWidget(max_time_label)
        layout.addWidget(total_frames_label)
        layout.addWidget(total_detections_label)
        layout.addWidget(avg_detections_label)
        layout.addWidget(avg_confidence_label)
        
        return card
    
    def _create_comparison_card(self):
        """Create comparison summary card."""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        
        layout.addWidget(StrongBodyLabel("Comparison Summary", self))
        
        self.faster_model_label = TitleLabel("-", self)
        self.speed_ratio_label = BodyLabel("Speed Ratio: -", self)
        self.detection_diff_label = BodyLabel("Detection Difference: -", self)
        
        layout.addWidget(self.faster_model_label)
        layout.addWidget(self.speed_ratio_label)
        layout.addWidget(self.detection_diff_label)
        
        return card
    
    def _create_images_card(self):
        """Create card for displaying detection images."""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        
        layout.addWidget(StrongBodyLabel("Detection Visualization", self))
        
        # Images layout (side by side)
        images_layout = QHBoxLayout()
        
        # PyTorch image
        pt_image_container = QVBoxLayout()
        pt_image_container.addWidget(BodyLabel("PyTorch (.pt)", self))
        self.pt_image_label = QLabel(self)
        self.pt_image_label.setAlignment(Qt.AlignCenter)
        self.pt_image_label.setMinimumSize(300, 200)
        self.pt_image_label.setScaledContents(False)
        pt_image_container.addWidget(self.pt_image_label)
        
        # ONNX image
        onnx_image_container = QVBoxLayout()
        onnx_image_container.addWidget(BodyLabel("ONNX (.onnx)", self))
        self.onnx_image_label = QLabel(self)
        self.onnx_image_label.setAlignment(Qt.AlignCenter)
        self.onnx_image_label.setMinimumSize(300, 200)
        self.onnx_image_label.setScaledContents(False)
        onnx_image_container.addWidget(self.onnx_image_label)
        
        images_layout.addLayout(pt_image_container)
        images_layout.addLayout(onnx_image_container)
        
        layout.addLayout(images_layout)
        
        return card
    
    def select_input_file(self):
        """Open file dialog to select input."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Test Image or Video",
            "",
            "Media Files (*.jpg *.jpeg *.png *.mp4 *.avi *.mov *.mkv);;All Files (*.*)"
        )
        
        if file_path:
            self.input_file = file_path
            self.file_label.setText(f"Selected: {Path(file_path).name}")
            self.run_btn.setEnabled(True)
    
    def run_comparison(self):
        """Start the comparison process."""
        if not self.input_file:
            InfoBar.warning(
                title="No Input",
                content="Please select an image or video file first.",
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        
        # Check if models exist
        if not Path(self.pt_model_path).exists():
            InfoBar.error(
                title="Model Not Found",
                content=f"PyTorch model not found: {self.pt_model_path}",
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        
        if not Path(self.onnx_model_path).exists():
            InfoBar.error(
                title="Model Not Found",
                content=f"ONNX model not found: {self.onnx_model_path}",
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        
        # Determine if video
        file_ext = Path(self.input_file).suffix.lower()
        is_video = file_ext in ['.mp4', '.avi', '.mov', '.mkv']
        
        max_frames = int(self.frames_combo.currentText())
        
        # Hide results, show progress
        self.pt_results_card.hide()
        self.onnx_results_card.hide()
        self.comparison_card.hide()
        self.images_card.hide()
        self.progress_card.show()
        
        # Disable run button
        self.run_btn.setEnabled(False)
        
        # Start comparison thread
        self.comparison_thread = ComparisonThread(
            self.input_file,
            self.pt_model_path,
            self.onnx_model_path,
            is_video,
            max_frames
        )
        
        self.comparison_thread.progress.connect(self.on_progress)
        self.comparison_thread.finished.connect(self.on_comparison_complete)
        self.comparison_thread.error.connect(self.on_error)
        
        self.comparison_thread.start()
    
    def on_progress(self, message):
        """Update progress message."""
        self.progress_label.setText(message)
    
    def on_comparison_complete(self, result):
        """Handle comparison completion."""
        # Hide progress
        self.progress_card.hide()
        
        # Extract summary
        summary = result.get('summary', result)  # Handle both old and new format
        
        # Update PyTorch results
        pt_stats = summary['pytorch']
        self.pt_results_card.avg_time_label.setText(f"Avg Time: {pt_stats['avg_time_ms']:.2f} ms")
        self.pt_results_card.min_time_label.setText(f"Min Time: {pt_stats['min_time_ms']:.2f} ms")
        self.pt_results_card.max_time_label.setText(f"Max Time: {pt_stats['max_time_ms']:.2f} ms")
        self.pt_results_card.total_frames_label.setText(f"Total Frames: {pt_stats['total_frames']}")
        self.pt_results_card.total_detections_label.setText(f"Total Detections: {pt_stats['total_detections']}")
        self.pt_results_card.avg_detections_label.setText(f"Avg Detections/Frame: {pt_stats['avg_detections']:.2f}")
        self.pt_results_card.avg_confidence_label.setText(f"Avg Confidence: {pt_stats['avg_confidence']:.3f}")
        
        # Update ONNX results
        onnx_stats = summary['onnx']
        self.onnx_results_card.avg_time_label.setText(f"Avg Time: {onnx_stats['avg_time_ms']:.2f} ms")
        self.onnx_results_card.min_time_label.setText(f"Min Time: {onnx_stats['min_time_ms']:.2f} ms")
        self.onnx_results_card.max_time_label.setText(f"Max Time: {onnx_stats['max_time_ms']:.2f} ms")
        self.onnx_results_card.total_frames_label.setText(f"Total Frames: {onnx_stats['total_frames']}")
        self.onnx_results_card.total_detections_label.setText(f"Total Detections: {onnx_stats['total_detections']}")
        self.onnx_results_card.avg_detections_label.setText(f"Avg Detections/Frame: {onnx_stats['avg_detections']:.2f}")
        self.onnx_results_card.avg_confidence_label.setText(f"Avg Confidence: {onnx_stats['avg_confidence']:.3f}")
        
        # Update comparison summary
        comparison = summary['comparison']
        faster = comparison.get('faster_model', 'N/A')
        speed_ratio = comparison.get('speed_ratio', 0)
        
        if faster != 'N/A':
            self.faster_model_label.setText(f"🏆 Faster Model: {faster.upper()}")
            
            if faster == 'pytorch':
                ratio_text = f"PyTorch is {speed_ratio:.2f}x faster than ONNX"
            else:
                ratio_text = f"ONNX is {1/speed_ratio:.2f}x faster than PyTorch"
            
            self.speed_ratio_label.setText(f"Speed Ratio: {ratio_text}")
        
        det_diff = comparison.get('detection_difference', 0)
        self.detection_diff_label.setText(f"Detection Difference: {det_diff:.2f} detections/frame")
        
        # Display images if available (for single image comparison)
        if result.get('has_images', False):
            self._display_detection_images(
                result['pytorch_image'],
                result['onnx_image']
            )
            self.images_card.show()
        
        # Show results
        self.pt_results_card.show()
        self.onnx_results_card.show()
        self.comparison_card.show()
        
        # Re-enable button
        self.run_btn.setEnabled(True)
        
        # Show success message
        InfoBar.success(
            title="Comparison Complete",
            content=f"Faster model: {faster.upper()}",
            duration=3000,
            position=InfoBarPosition.TOP,
            parent=self
        )
    
    def on_error(self, error_msg):
        """Handle comparison error."""
        self.progress_card.hide()
        self.run_btn.setEnabled(True)
        
        InfoBar.error(
            title="Comparison Failed",
            content=error_msg,
            duration=5000,
            position=InfoBarPosition.TOP,
            parent=self
        )
    
    def _display_detection_images(self, pt_image, onnx_image):
        """Display detection images in the UI."""
        # Convert BGR to RGB for Qt
        pt_image_rgb = cv2.cvtColor(pt_image, cv2.COLOR_BGR2RGB)
        onnx_image_rgb = cv2.cvtColor(onnx_image, cv2.COLOR_BGR2RGB)
        
        # Convert to QPixmap
        pt_pixmap = self._numpy_to_pixmap(pt_image_rgb)
        onnx_pixmap = self._numpy_to_pixmap(onnx_image_rgb)
        
        # Scale pixmaps to fit labels while maintaining aspect ratio
        pt_scaled = pt_pixmap.scaled(
            self.pt_image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        onnx_scaled = onnx_pixmap.scaled(
            self.onnx_image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # Set pixmaps
        self.pt_image_label.setPixmap(pt_scaled)
        self.onnx_image_label.setPixmap(onnx_scaled)
    
    def _numpy_to_pixmap(self, img: np.ndarray) -> QPixmap:
        """Convert numpy array to QPixmap."""
        height, width, channel = img.shape
        bytes_per_line = 3 * width
        q_image = QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_image)
    
    def on_error(self, error_msg):
        """Handle comparison error."""
        self.progress_card.hide()
        self.run_btn.setEnabled(True)
        
        InfoBar.error(
            title="Comparison Failed",
            content=error_msg,
            duration=5000,
            position=InfoBarPosition.TOP,
            parent=self
        )
