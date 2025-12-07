import easyocr
import re

class OCREngine:
    def __init__(self, languages=['en']):
        # Initialize EasyOCR Reader
        # gpu=True will use CUDA if available, else CPU.
        # For mid-cpu requirement, it works fine on CPU but is slower. 
        # Since we use 'plates_v12' which is presumably good at cropping, OCR has less noise.
        print("Initializing OCR Engine...")
        self.reader = easyocr.Reader(languages, gpu=True) 

    def recognize(self, plate_image):
        """
        Takes a cropped plate image (numpy array) and returns text.
        """
        try:
            # allowlist can be used to restrict characters if we know formats
            # Pakistani plates usually are: AAA-123 or ABC-1234 or LEA-12-123 etc.
            # Allowing alphanumeric and hyphens.
            results = self.reader.readtext(plate_image, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ')
            
            if not results:
                return ""
            
            # Join all detection parts
            full_text = " ".join(results)
            
            # Post-processing to clean up
            clean_text = self.clean_text(full_text)
            return clean_text
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def clean_text(self, text):
        # Remove non-alphanumeric except hyphens
        # Upper case
        text = text.upper()
        # Remove special chars
        text = re.sub(r'[^A-Z0-9-]', '', text)
        return text
