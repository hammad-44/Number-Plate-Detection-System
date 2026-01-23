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
        
        boxes = []
        confidences = []
        class_ids = []
        
        # Iterate and filter
        # Format usually: x, y, w, h, class_scores...
        # If output is [x, y, w, h, obj_conf, class_scores...] (YOLOv5)
        # If output is [x, y, w, h, class_scores...] (YOLOv8)
        
        rows = predictions.shape[0]
        
        # Let's assume YOLOv8 format where 4 items are box, rest are classes
        # or YOLOv5 format where index 4 is objness.
        
        # We need to be generic or check dimensions.
        # Assuming user's model is standard YOLO export.
        
        for i in range(rows):
            row = predictions[i]
            if len(row) > 5: # Possible YOLOv5 [x,y,w,h, conf, cls...]
                 confidence = row[4]
                 if confidence < self.conf_thres:
                     continue
                 classes_scores = row[5:]
                 class_id = np.argmax(classes_scores)
                 score = classes_scores[class_id] * confidence # multiply by obj conf
            else: # Possible YOLOv8 [x,y,w,h, cls1, cls2...] or just 1 class
                 classes_scores = row[4:]
                 class_id = np.argmax(classes_scores)
                 score = classes_scores[class_id]
                 confidence = score # For v8, score is confidence
            
            if score > self.conf_thres:
                x, y, w, h = row[0:4]
                
                # Scale boxes back to original image size
                # The prediction is extracting on 640x640 range
                
                # We need to unscale.
                # However, since we did direct resize, we just scale by ratio
                w_scale = original_size[0] / self.input_shape[0]
                h_scale = original_size[1] / self.input_shape[1]
                
                x = x * w_scale
                y = y * h_scale
                w = w * w_scale
                h = h * h_scale
                
                # Convert to top-left x,y,w,h for NMS
                left = int(x - w/2)
                top = int(y - h/2)
                width = int(w)
                height = int(h)
                
                boxes.append([left, top, width, height])
                confidences.append(float(score))
                class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_thres, self.iou_thres)
        
        results = []
        if len(indices) > 0:
            for i in indices: # indices might be list of standard python ints or numpy
                if isinstance(i, (list, tuple, np.ndarray)):
                    idx = i[0] # Unpack if needed
                else:
                    idx = i
                    
                box = boxes[idx]
                x, y, w, h = box
                # Ensure they are within image bounds
                x = max(0, x)
                y = max(0, y)
                w = min(w, original_size[0] - x)
                h = min(h, original_size[1] - y)
                
                results.append({
                    "box": [x, y, x+w, y+h], # x1, y1, x2, y2
                    "score": confidences[idx],
                    "class_id": class_ids[idx]
                })

        return results
    
        return results
