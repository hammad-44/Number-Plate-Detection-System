import cv2
import numpy as np
import onnxruntime as ort
import time

class PlateDetector:
    def __init__(self, model_path, input_shape=(640, 640), conf_thres=0.5, iou_thres=0.45):
        self.input_shape = input_shape
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        
        # Load model logic
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        try:
            self.session = ort.InferenceSession(model_path, providers=providers)
        except Exception as e:
            print(f"Warning: Failed to load with CUDA, falling back to CPU. Error: {e}")
            self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])

        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]

    def preprocess(self, img):
        """
        Resize image to model input shape and normalize.
        Returns preprocessed image and scale factor.
        """
        height, width = img.shape[:2]
        
        # Resize/Letterbox logic could go here, but for simplicity we resize
        # A proper letterbox is better for accuracy, but direct resize works for fixed aspect ratio models
        # Let's do a simple resize for now to verify. 
        # For production quality, letterbox is recommended.
        
        img_resized = cv2.resize(img, self.input_shape)
        
        # Normalize
        img_data = img_resized / 255.0
        img_data = img_data.transpose(2, 0, 1)  # HWC to CHW
        img_data = np.expand_dims(img_data, axis=0).astype(np.float32)
        
        return img_data, (width, height)

    def xywh2xyxy(self, x):
        # Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2]
        y = np.copy(x)
        y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
        y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
        y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
        y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
        return y

    def nms(self, boxes, scores, iou_threshold):
        # Apply Non-Max Suppression
        indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), self.conf_thres, iou_threshold)
        if len(indices) > 0:
            return indices.flatten() if isinstance(indices, np.ndarray) else indices
        return []

    def detect(self, img):
        """
        Inference on a single frame.
        Returns list of (x1, y1, x2, y2, score, class_id)
        """
        img_data, original_size = self.preprocess(img)
        
        outputs = self.session.run(self.output_names, {self.input_name: img_data})
        output = outputs[0] # Shape usually (1, 84, 8400) for YOLOv8 or different for v5.
        
        # Handle Output Shape
        # YOLOv8 output is often (1, 4 + nc, num_anchors) -> Transpose to (1, num_anchors, 4+nc)
        # Check shape to identify
        if output.shape[1] > output.shape[2]: # (1, 8400, 84) - likely v5/v7 structure
             predictions = output[0]
        else: # (1, 84, 8400) - likely v8 structure
             predictions = output[0].transpose()
        
        # Fast vectorized filtering
        if predictions.shape[1] == 5:
            scores = predictions[:, 4]
            class_ids = np.zeros(len(scores), dtype=int)
        elif predictions.shape[1] > 5:
            class_scores = predictions[:, 4:]
            class_ids = np.argmax(class_scores, axis=1)
            scores = np.max(class_scores, axis=1)
        else:
            return []

        mask = scores > self.conf_thres
        if not np.any(mask):
            return []

        filtered_preds = predictions[mask]
        filtered_scores = scores[mask]
        filtered_class_ids = class_ids[mask]

        # Scale coordinates back to original image size
        w_scale = original_size[0] / self.input_shape[0]
        h_scale = original_size[1] / self.input_shape[1]

        cx = filtered_preds[:, 0] * w_scale
        cy = filtered_preds[:, 1] * h_scale
        w = filtered_preds[:, 2] * w_scale
        h = filtered_preds[:, 3] * h_scale

        left = (cx - w / 2).astype(int)
        top = (cy - h / 2).astype(int)
        width = w.astype(int)
        height = h.astype(int)

        boxes = np.column_stack([left, top, width, height]).tolist()
        confidences = [float(s) for s in filtered_scores]
        class_ids_list = [int(c) for c in filtered_class_ids]

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_thres, self.iou_thres)
        
        results = []
        if len(indices) > 0:
            for i in indices:
                idx = i[0] if isinstance(i, (list, tuple, np.ndarray)) else i
                box = boxes[idx]
                x, y, w, h = box
                # Clamp within image bounds
                x = max(0, x)
                y = max(0, y)
                w = min(w, original_size[0] - x)
                h = min(h, original_size[1] - y)
                
                results.append({
                    "box": [x, y, x + w, y + h],
                    "score": confidences[idx],
                    "class_id": class_ids_list[idx]
                })

        return results
