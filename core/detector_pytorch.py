import cv2
import numpy as np
import time
from ultralytics import YOLO


class PlateDetectorPyTorch:
    """
    PyTorch-based Number Plate Detector using native .pt model format.
    Uses Ultralytics YOLO for inference.
    """
    
    def __init__(self, model_path, conf_thres=0.5, iou_thres=0.45):
        """
        Initialize the PyTorch detector.
        
        Args:
            model_path: Path to the .pt model file
            conf_thres: Confidence threshold for detections
            iou_thres: IOU threshold for NMS
        """
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        
        # Load YOLO model
        try:
            self.model = YOLO(model_path)
            print(f"✓ PyTorch model loaded successfully from {model_path}")
        except Exception as e:
            print(f"✗ Failed to load PyTorch model: {e}")
            raise
    
    def detect(self, img):
        """
        Run inference on a single frame.
        
        Args:
            img: Input image as numpy array (BGR format from cv2)
            
        Returns:
            List of detections, each as dict with:
                - box: [x1, y1, x2, y2] coordinates
                - score: confidence score
                - class_id: class identifier
        """
        try:
            # Run inference
            results = self.model.predict(
                img,
                conf=self.conf_thres,
                iou=self.iou_thres,
                verbose=False
            )
            
            # Parse results
            detections = []
            
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                
                for i in range(len(boxes)):
                    # Get box coordinates (xyxy format)
                    box = boxes.xyxy[i].cpu().numpy()
                    x1, y1, x2, y2 = map(int, box)
                    
                    # Get confidence score
                    score = float(boxes.conf[i].cpu().numpy())
                    
                    # Get class ID
                    class_id = int(boxes.cls[i].cpu().numpy())
                    
                    detections.append({
                        "box": [x1, y1, x2, y2],
                        "score": score,
                        "class_id": class_id
                    })
            
            return detections
            
        except Exception as e:
            print(f"Error during PyTorch inference: {e}")
            return []
    
    def detect_with_timing(self, img):
        """
        Run inference and measure timing.
        
        Args:
            img: Input image as numpy array
            
        Returns:
            Tuple of (detections, inference_time_ms)
        """
        start_time = time.time()
        detections = self.detect(img)
        inference_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return detections, inference_time
