import sys
print(f"Python: {sys.version}")

try:
    print("Importing ONNX Runtime (FIRST)...")
    import onnxruntime
    print(f"ONNX Runtime Version: {onnxruntime.__version__}")

    print("Importing PyQt5...")
    from PyQt5.QtWidgets import QApplication
    print("PyQt5 imported.")
    
    print("Importing OpenCV...")
    import cv2
    print(f"OpenCV imported: {cv2.__version__}")
    
    print("Success!")

except ImportError as e:
    print(f"Import Failed: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
