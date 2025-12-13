"""
Standalone Model Comparison Script

Run this script to quickly compare PyTorch (.pt) and ONNX (.onnx) models
from the command line.

Usage:
    python compare_models.py --input path/to/test/image.jpg
    python compare_models.py --input path/to/test/video.mp4 --max-frames 100
    python compare_models.py --input path/to/test/video.mp4 --output results/
"""

import argparse
import sys
from pathlib import Path
import cv2

from core.model_comparison import ModelComparison


def main():
    parser = argparse.ArgumentParser(description='Compare PyTorch and ONNX number plate detection models')
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='Path to input image or video file'
    )
    
    parser.add_argument(
        '--pt-model',
        type=str,
        default='models/best.pt',
        help='Path to PyTorch model (default: models/best.pt)'
    )
    
    parser.add_argument(
        '--onnx-model',
        type=str,
        default='models/best.onnx',
        help='Path to ONNX model (default: models/best.onnx)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='comparison_results',
        help='Output directory for results (default: comparison_results)'
    )
    
    parser.add_argument(
        '--conf-threshold',
        type=float,
        default=0.5,
        help='Confidence threshold (default: 0.5)'
    )
    
    parser.add_argument(
        '--iou-threshold',
        type=float,
        default=0.45,
        help='IOU threshold for NMS (default: 0.45)'
    )
    
    parser.add_argument(
        '--max-frames',
        type=int,
        default=100,
        help='Maximum frames to process from video (default: 100)'
    )
    
    parser.add_argument(
        '--no-charts',
        action='store_true',
        help='Skip generating charts'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"✗ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Validate model files
    pt_model_path = Path(args.pt_model)
    onnx_model_path = Path(args.onnx_model)
    
    if not pt_model_path.exists():
        print(f"✗ Error: PyTorch model not found: {args.pt_model}")
        sys.exit(1)
    
    if not onnx_model_path.exists():
        print(f"✗ Error: ONNX model not found: {args.onnx_model}")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*70)
    print("MODEL COMPARISON TOOL")
    print("="*70)
    print(f"Input: {args.input}")
    print(f"PyTorch Model: {args.pt_model}")
    print(f"ONNX Model: {args.onnx_model}")
    print(f"Output Directory: {args.output}")
    print("="*70 + "\n")
    
    # Initialize comparison
    try:
        comparator = ModelComparison(
            pt_model_path=str(pt_model_path),
            onnx_model_path=str(onnx_model_path),
            conf_thres=args.conf_threshold,
            iou_thres=args.iou_threshold
        )
    except Exception as e:
        print(f"✗ Error initializing models: {e}")
        sys.exit(1)
    
    # Determine if input is image or video
    file_ext = input_path.suffix.lower()
    is_video = file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    
    try:
        if is_video:
            print(f"Running comparison on video (max {args.max_frames} frames)...")
            comparator.compare_on_video(str(input_path), max_frames=args.max_frames)
        else:
            print("Running comparison on image...")
            result = comparator.compare_on_image(str(input_path))
            
            # Print single image results
            print("\nSingle Image Results:")
            print(f"  PyTorch: {result['pytorch']['count']} detections in {result['pytorch']['time_ms']:.2f} ms")
            print(f"  ONNX: {result['onnx']['count']} detections in {result['onnx']['time_ms']:.2f} ms")
    
    except Exception as e:
        print(f"✗ Error during comparison: {e}")
        sys.exit(1)
    
    # Print summary
    comparator.print_summary()
    
    # Save results
    results_file = output_dir / 'comparison_results.json'
    comparator.save_results(str(results_file))
    
    # Generate charts
    if not args.no_charts:
        print("\nGenerating comparison charts...")
        try:
            comparator.generate_comparison_charts(str(output_dir))
        except Exception as e:
            print(f"Warning: Failed to generate charts: {e}")
    
    print(f"\n✓ Comparison complete! Results saved to: {output_dir}")
    print("\nGenerated files:")
    print(f"  - {results_file}")
    if not args.no_charts:
        print(f"  - {output_dir / 'timing_comparison.png'}")
        print(f"  - {output_dir / 'detection_comparison.png'}")
        print(f"  - {output_dir / 'confidence_distribution.png'}")


if __name__ == '__main__':
    main()
