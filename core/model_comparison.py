"""
Model Comparison Utility for Number Plate Detection System

This module provides functionality to compare PyTorch (.pt) and ONNX (.onnx) models
for timing and accuracy metrics.
"""

import cv2
import numpy as np
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
from datetime import datetime

from core.detector import PlateDetector
from core.detector_pytorch import PlateDetectorPyTorch


class ModelComparison:
    """Compare PyTorch and ONNX models for performance and accuracy."""
    
    def __init__(self, pt_model_path: str, onnx_model_path: str, conf_thres=0.5, iou_thres=0.45):
        """
        Initialize both models for comparison.
        
        Args:
            pt_model_path: Path to .pt model
            onnx_model_path: Path to .onnx model
            conf_thres: Confidence threshold
            iou_thres: IOU threshold for NMS
        """
        print("Initializing models for comparison...")
        
        # Initialize both detectors
        self.pt_detector = PlateDetectorPyTorch(pt_model_path, conf_thres, iou_thres)
        self.onnx_detector = PlateDetector(onnx_model_path, conf_thres=conf_thres, iou_thres=iou_thres)
        
        # Results storage
        self.results = {
            'pytorch': {
                'timings': [],
                'detection_counts': [],
                'confidence_scores': [],
                'total_detections': 0
            },
            'onnx': {
                'timings': [],
                'detection_counts': [],
                'confidence_scores': [],
                'total_detections': 0
            },
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'pt_model': pt_model_path,
                'onnx_model': onnx_model_path,
                'conf_threshold': conf_thres,
                'iou_threshold': iou_thres
            }
        }
        
        print("✓ Both models initialized successfully")
    
    def draw_detections(self, img: np.ndarray, detections: List[Dict], color=(0, 255, 0)) -> np.ndarray:
        """
        Draw bounding boxes on image.
        
        Args:
            img: Input image
            detections: List of detections
            color: BGR color for boxes
            
        Returns:
            Image with drawn boxes
        """
        result_img = img.copy()
        
        for det in detections:
            box = det['box']
            score = det['score']
            
            x1, y1, x2, y2 = box
            
            # Draw rectangle
            cv2.rectangle(result_img, (x1, y1), (x2, y2), color, 2)
            
            # Draw confidence score
            label = f"{score:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            
            # Draw label background
            cv2.rectangle(
                result_img,
                (x1, y1 - label_size[1] - 4),
                (x1 + label_size[0], y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                result_img,
                label,
                (x1, y1 - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
        
        return result_img
    
    def compare_on_image(self, image_path: str, return_images: bool = False) -> Dict:
        """
        Compare both models on a single image.
        
        Args:
            image_path: Path to test image
            return_images: If True, return images with drawn detections
            
        Returns:
            Dictionary containing comparison results
        """
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Run PyTorch model
        pt_detections, pt_time = self.pt_detector.detect_with_timing(img)
        
        # Run ONNX model
        onnx_detections, onnx_time = self.onnx_detector.detect_with_timing(img)
        
        # Store results
        self._store_results('pytorch', pt_detections, pt_time)
        self._store_results('onnx', onnx_detections, onnx_time)
        
        result = {
            'pytorch': {
                'detections': pt_detections,
                'time_ms': pt_time,
                'count': len(pt_detections)
            },
            'onnx': {
                'detections': onnx_detections,
                'time_ms': onnx_time,
                'count': len(onnx_detections)
            }
        }
        
        # Add visualized images if requested
        if return_images:
            result['pytorch']['image'] = self.draw_detections(img, pt_detections, color=(46, 204, 113))  # Green
            result['onnx']['image'] = self.draw_detections(img, onnx_detections, color=(52, 152, 219))  # Blue
            result['original_image'] = img
        
        return result
    
    def compare_on_video(self, video_path: str, max_frames: int = 100) -> Dict:
        """
        Compare both models on video frames.
        
        Args:
            video_path: Path to test video
            max_frames: Maximum number of frames to process
            
        Returns:
            Dictionary containing aggregated comparison results
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")
        
        frame_count = 0
        
        print(f"Processing video: {video_path}")
        
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run both models
            pt_detections, pt_time = self.pt_detector.detect_with_timing(frame)
            onnx_detections, onnx_time = self.onnx_detector.detect_with_timing(frame)
            
            # Store results
            self._store_results('pytorch', pt_detections, pt_time)
            self._store_results('onnx', onnx_detections, onnx_time)
            
            frame_count += 1
            
            if frame_count % 10 == 0:
                print(f"  Processed {frame_count} frames...")
        
        cap.release()
        
        print(f"✓ Processed {frame_count} frames")
        
        return self.get_summary()
    
    def _store_results(self, model_name: str, detections: List[Dict], timing: float):
        """Store detection results and timing."""
        self.results[model_name]['timings'].append(timing)
        self.results[model_name]['detection_counts'].append(len(detections))
        self.results[model_name]['total_detections'] += len(detections)
        
        # Store confidence scores
        for det in detections:
            self.results[model_name]['confidence_scores'].append(det['score'])
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics for both models.
        
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'pytorch': self._calculate_stats('pytorch'),
            'onnx': self._calculate_stats('onnx'),
            'comparison': {}
        }
        
        # Calculate relative performance
        if summary['onnx']['avg_time_ms'] > 0:
            speedup = summary['onnx']['avg_time_ms'] / summary['pytorch']['avg_time_ms']
            summary['comparison']['speed_ratio'] = speedup
            summary['comparison']['faster_model'] = 'pytorch' if speedup > 1 else 'onnx'
        
        # Compare detection rates
        summary['comparison']['detection_difference'] = (
            summary['pytorch']['avg_detections'] - summary['onnx']['avg_detections']
        )
        
        return summary
    
    def _calculate_stats(self, model_name: str) -> Dict:
        """Calculate statistics for a specific model."""
        data = self.results[model_name]
        
        if not data['timings']:
            return {
                'avg_time_ms': 0,
                'min_time_ms': 0,
                'max_time_ms': 0,
                'total_frames': 0,
                'total_detections': 0,
                'avg_detections': 0,
                'avg_confidence': 0
            }
        
        return {
            'avg_time_ms': np.mean(data['timings']),
            'min_time_ms': np.min(data['timings']),
            'max_time_ms': np.max(data['timings']),
            'std_time_ms': np.std(data['timings']),
            'total_frames': len(data['timings']),
            'total_detections': data['total_detections'],
            'avg_detections': np.mean(data['detection_counts']),
            'avg_confidence': np.mean(data['confidence_scores']) if data['confidence_scores'] else 0,
            'min_confidence': np.min(data['confidence_scores']) if data['confidence_scores'] else 0,
            'max_confidence': np.max(data['confidence_scores']) if data['confidence_scores'] else 0
        }
    
    def save_results(self, output_path: str):
        """Save detailed results to JSON file."""
        # Calculate summary
        summary = self.get_summary()
        
        # Combine with raw data
        output_data = {
            'summary': summary,
            'metadata': self.results['metadata'],
            'raw_data': {
                'pytorch': {
                    'timings': self.results['pytorch']['timings'],
                    'detection_counts': self.results['pytorch']['detection_counts']
                },
                'onnx': {
                    'timings': self.results['onnx']['timings'],
                    'detection_counts': self.results['onnx']['detection_counts']
                }
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"✓ Results saved to: {output_path}")
    
    def generate_comparison_charts(self, output_dir: str):
        """Generate visual comparison charts."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Timing Comparison
        self._plot_timing_comparison(str(output_path / 'timing_comparison.png'))
        
        # 2. Detection Count Comparison
        self._plot_detection_comparison(str(output_path / 'detection_comparison.png'))
        
        # 3. Confidence Distribution
        self._plot_confidence_distribution(str(output_path / 'confidence_distribution.png'))
        
        print(f"✓ Charts saved to: {output_dir}")
    
    def _plot_timing_comparison(self, output_path: str):
        """Plot timing comparison chart."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Box plot
        data_to_plot = [
            self.results['pytorch']['timings'],
            self.results['onnx']['timings']
        ]
        ax1.boxplot(data_to_plot, labels=['PyTorch (.pt)', 'ONNX (.onnx)'])
        ax1.set_ylabel('Inference Time (ms)')
        ax1.set_title('Inference Time Distribution')
        ax1.grid(True, alpha=0.3)
        
        # Bar chart - average times
        summary = self.get_summary()
        models = ['PyTorch', 'ONNX']
        avg_times = [
            summary['pytorch']['avg_time_ms'],
            summary['onnx']['avg_time_ms']
        ]
        colors = ['#2ecc71', '#3498db']
        
        ax2.bar(models, avg_times, color=colors, alpha=0.7)
        ax2.set_ylabel('Average Inference Time (ms)')
        ax2.set_title('Average Inference Time Comparison')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for i, v in enumerate(avg_times):
            ax2.text(i, v + 0.5, f'{v:.2f} ms', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def _plot_detection_comparison(self, output_path: str):
        """Plot detection count comparison."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        frames = range(len(self.results['pytorch']['detection_counts']))
        
        ax.plot(frames, self.results['pytorch']['detection_counts'], 
                label='PyTorch', marker='o', markersize=3, alpha=0.7, color='#2ecc71')
        ax.plot(frames, self.results['onnx']['detection_counts'], 
                label='ONNX', marker='s', markersize=3, alpha=0.7, color='#3498db')
        
        ax.set_xlabel('Frame Number')
        ax.set_ylabel('Number of Detections')
        ax.set_title('Detection Count per Frame')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def _plot_confidence_distribution(self, output_path: str):
        """Plot confidence score distribution."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if self.results['pytorch']['confidence_scores'] and self.results['onnx']['confidence_scores']:
            ax.hist(self.results['pytorch']['confidence_scores'], bins=20, 
                   alpha=0.6, label='PyTorch', color='#2ecc71')
            ax.hist(self.results['onnx']['confidence_scores'], bins=20, 
                   alpha=0.6, label='ONNX', color='#3498db')
            
            ax.set_xlabel('Confidence Score')
            ax.set_ylabel('Frequency')
            ax.set_title('Confidence Score Distribution')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def print_summary(self):
        """Print summary to console."""
        summary = self.get_summary()
        
        print("\n" + "="*70)
        print("MODEL COMPARISON SUMMARY")
        print("="*70)
        
        print("\n📊 PYTORCH MODEL (.pt)")
        print("-" * 70)
        self._print_model_stats(summary['pytorch'])
        
        print("\n📊 ONNX MODEL (.onnx)")
        print("-" * 70)
        self._print_model_stats(summary['onnx'])
        
        print("\n🏆 COMPARISON")
        print("-" * 70)
        faster = summary['comparison'].get('faster_model', 'N/A')
        speed_ratio = summary['comparison'].get('speed_ratio', 0)
        
        if faster != 'N/A':
            print(f"Faster Model: {faster.upper()}")
            print(f"Speed Ratio: {speed_ratio:.2f}x")
            
            if faster == 'pytorch':
                print(f"  → PyTorch is {speed_ratio:.2f}x faster than ONNX")
            else:
                print(f"  → ONNX is {1/speed_ratio:.2f}x faster than PyTorch")
        
        det_diff = summary['comparison'].get('detection_difference', 0)
        print(f"\nDetection Difference: {det_diff:.2f} detections/frame")
        
        print("\n" + "="*70)
    
    def _print_model_stats(self, stats: Dict):
        """Print statistics for a model."""
        print(f"  Average Time: {stats['avg_time_ms']:.2f} ms")
        print(f"  Min Time: {stats['min_time_ms']:.2f} ms")
        print(f"  Max Time: {stats['max_time_ms']:.2f} ms")
        print(f"  Std Dev: {stats.get('std_time_ms', 0):.2f} ms")
        print(f"  Total Frames: {stats['total_frames']}")
        print(f"  Total Detections: {stats['total_detections']}")
        print(f"  Avg Detections/Frame: {stats['avg_detections']:.2f}")
        print(f"  Avg Confidence: {stats['avg_confidence']:.3f}")
