import easyocr
import re
import numpy as np

class OCREngine:
    def __init__(self, languages=['en']):
        print("Initializing OCR Engine...")
        self.reader = easyocr.Reader(languages, gpu=True) 

    def recognize(self, plate_image):
        """
        Takes a cropped plate image (numpy array) and returns text.
        Applies size filtering to remove noise (years/city names) and 
        regex validation for Pakistani plate formats.
        """
        try:
            # detail=1 returns list of [bbox, text, prob]
            results = self.reader.readtext(plate_image, detail=1, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ')
            
            if not results:
                return ""
            
            # 1. Filter by Height (remove small text)
            # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            # Height ~ y4 - y1
            
            blocks = []
            max_height = 0
            
            for bbox, text, conf in results:
                # Calculate height
                pts = np.array(bbox)
                h = np.max(pts[:, 1]) - np.min(pts[:, 1])
                max_height = max(max_height, h)
                
                # Store center x for sorting
                center_x = np.mean(pts[:, 0])
                blocks.append({'text': text, 'h': h, 'x': center_x})
            
            # Threshold: Keep text that is at least 35% of the max height on the plate
            # This filters out small "ICT", "2021", etc., but keeps the number even if slightly smaller.
            # 60% was too aggressive.
            valid_blocks = [b for b in blocks if b['h'] >= 0.35 * max_height]
            
            if not valid_blocks:
                return ""
                
            # 2. Sort Left-to-Right
            valid_blocks.sort(key=lambda b: b['x'])
            
            # 3. Concatenate
            full_text = " ".join([b['text'] for b in valid_blocks])
            # 4. Clean and Validate
            clean_text = self.clean_and_format(full_text)
            return clean_text
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def clean_and_format(self, text):
        """
        Cleans text and checks against Pakistani formats.
        Format: 1-4 Letters, Space/Hyphen, 1-5 Digits
        """
        text = text.upper()
        
        # 1. Blacklist for "Noise" words that are visually large but are NOT the registration
        BLACKLIST = {
            'ISLAMABAD', 'PUNJAB', 'SINDH', 'KPK', 'BALOCHISTAN', 
            'PAKISTAN', 'GOVT', 'APPLIED', 'FOR', 'ICT', 'LEB', 'LEE' # Wait, LEB/LEE are valid!
        }
        # Refined Blacklist
        NOISE_WORDS = {
            'ISLAMABAD', 'PUNJAB', 'SINDH', 'KPK', 'BALOCHISTAN', 'PAKISTAN', 
            'GOVERNMENT', 'GOVT', 'APPLIED', 'FOR', 'ICT' # ICT is often top header, actual plate is e.g. AB-123
        }

        # 1. Extract all logical tokens
        tokens = re.findall(r'[A-Z0-9]+', text)
        
        letter_candidates = []
        number_candidates = []
        
        for token in tokens:
            # Check Noise
            if token in NOISE_WORDS:
                continue
                
            if token.isalpha():
                # Letters: 1-4 chars. STRICTLY < 5.
                # "ISLAMABAD" is 9 -> Rejected.
                if 1 <= len(token) <= 4: 
                    letter_candidates.append(token)
            elif token.isdigit():
                if 1 <= len(token) <= 5: 
                    number_candidates.append(token)
            else:
                # Mixed token (e.g. "AJJ43Z" or "LEA-123")
                sub_letters = "".join(re.findall(r'[A-Z]+', token))
                sub_numbers = "".join(re.findall(r'[0-9]+', token))
                
                # Check noise in sub-parts? Unlikely needed if split correctly
                if sub_letters and sub_letters not in NOISE_WORDS and 1 <= len(sub_letters) <= 4:
                    letter_candidates.append(sub_letters)
                if sub_numbers and 1 <= len(sub_numbers) <= 5:
                    number_candidates.append(sub_numbers)

        best_letters = ""
        best_numbers = ""
        
        # 3. Selection Strategy
        
        if letter_candidates:
            # Pick longest one (e.g. 'LEA' > 'L')
            best_letters = max(letter_candidates, key=len)
            
        if number_candidates:
            # Pick longest number? '5855' vs '0'. Pick 5855.
            # But what about 'BR 14 0 12'? -> '14', '0', '12'. Longest is '14' or '12'.
            # Usually strict number is 3-4 digits.
            # If we have [14, 0, 12], we might want to combine? 
            # Pakistani plates: usually continuous digits. 
            # Let's stick to "Longest continuous digit block" for now.
            best_numbers = max(number_candidates, key=len)
            
        # 4. Final Validation
        if best_letters and best_numbers:
            return f"{best_letters} {best_numbers}"
            
        return "" 
