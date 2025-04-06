"""
Enhanced Computer Vision module for Computer Control Agent
Provides advanced image recognition, OCR, and UI element detection
"""

import cv2
import numpy as np
import pyautogui
import os
import logging
import pytesseract
from PIL import Image
import time
from typing import Tuple, List, Dict, Optional, Union, Any
from src.utils.resilience import retry, fallback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('computer_vision')

# Configure pytesseract path - may need to be adjusted based on installation
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# For macOS, Linux: Make sure tesseract is installed and in PATH

class ComputerVision:
    """
    Enhanced computer vision capabilities for the Computer Control Agent
    Provides advanced image recognition, OCR, and UI element detection
    """
    
    def __init__(self, reference_dir: str = "reference_images"):
        """
        Initialize the computer vision module
        
        Args:
            reference_dir: Directory to store reference images
        """
        self.reference_dir = reference_dir
        os.makedirs(reference_dir, exist_ok=True)
        logger.info(f"Reference image directory: {reference_dir}")
        
        # Initialize adaptive confidence threshold
        self.default_confidence = 0.8
        self.confidence_history = []
        self.adaptive_confidence = self.default_confidence
        
    def take_screenshot(self) -> Optional[np.ndarray]:
        """
        Take a screenshot and convert to OpenCV format
        
        Returns:
            Screenshot as numpy array in BGR format, or None if failed
        """
        try:
            # Take screenshot using PyAutoGUI
            screenshot = pyautogui.screenshot()
            
            # Convert PIL image to numpy array
            screenshot_np = np.array(screenshot)
            
            # Convert RGB to BGR (OpenCV format)
            screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            return screenshot_bgr
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
            
    @retry(max_attempts=2, delay=0.5)
    def find_template(
        self, 
        template_path: str, 
        screenshot: Optional[np.ndarray] = None,
        confidence: float = None
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Find a template image on the screen using template matching
        
        Args:
            template_path: Path to the template image
            screenshot: Optional screenshot to search in (takes new screenshot if None)
            confidence: Confidence threshold (0-1), uses adaptive if None
            
        Returns:
            Tuple of (x, y, width, height) if found, None otherwise
        """
        try:
            # Use provided confidence or adaptive confidence
            if confidence is None:
                confidence = self.adaptive_confidence
                
            # Load the template
            template = cv2.imread(template_path)
            if template is None:
                logger.error(f"Failed to load template: {template_path}")
                return None
                
            # Get screenshot if not provided
            if screenshot is None:
                screenshot = self.take_screenshot()
                if screenshot is None:
                    return None
                    
            # Get template dimensions
            template_height, template_width = template.shape[:2]
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            
            # Find locations where the matching exceeds the threshold
            locations = np.where(result >= confidence)
            
            # Check if any matches were found
            if len(locations[0]) == 0:
                logger.warning(f"Template not found: {template_path} (confidence: {confidence:.2f})")
                
                # Update confidence history for adaptive threshold
                self.confidence_history.append(0)
                if len(self.confidence_history) > 10:
                    self.confidence_history.pop(0)
                self._update_adaptive_confidence()
                
                return None
                
            # Get the best match
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            top_left = max_loc
            
            # Update confidence history for adaptive threshold
            self.confidence_history.append(max_val)
            if len(self.confidence_history) > 10:
                self.confidence_history.pop(0)
            self._update_adaptive_confidence()
            
            # Calculate bottom right point
            bottom_right = (top_left[0] + template_width, top_left[1] + template_height)
            
            # Return as (x, y, width, height)
            x, y = top_left
            width, height = template_width, template_height
            
            logger.info(f"Found template: {template_path} at ({x}, {y}) with confidence {max_val:.2f}")
            return (x, y, width, height)
            
        except Exception as e:
            logger.error(f"Error finding template: {e}")
            return None
            
    def _update_adaptive_confidence(self):
        """Update the adaptive confidence threshold based on recent history"""
        if not self.confidence_history:
            self.adaptive_confidence = self.default_confidence
            return
            
        # Calculate new adaptive confidence
        if all(c == 0 for c in self.confidence_history):
            # If recent attempts all failed, lower the threshold
            self.adaptive_confidence = max(0.6, self.adaptive_confidence - 0.05)
        elif sum(1 for c in self.confidence_history if c > 0) / len(self.confidence_history) > 0.7:
            # If most recent attempts succeeded, gradually increase threshold
            self.adaptive_confidence = min(0.9, self.adaptive_confidence + 0.02)
            
        logger.debug(f"Adaptive confidence updated to {self.adaptive_confidence:.2f}")
            
    @retry(max_attempts=2, delay=0.5)
    def find_text(
        self, 
        text: str, 
        screenshot: Optional[np.ndarray] = None,
        case_sensitive: bool = False
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Find text on the screen using OCR
        
        Args:
            text: Text to find
            screenshot: Optional screenshot to search in (takes new screenshot if None)
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            Tuple of (x, y, width, height) if found, None otherwise
        """
        try:
            # Get screenshot if not provided
            if screenshot is None:
                screenshot = self.take_screenshot()
                if screenshot is None:
                    return None
                    
            # Convert to grayscale for OCR
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            
            # Apply some preprocessing to improve OCR accuracy
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert numpy array to PIL Image for pytesseract
            pil_img = Image.fromarray(binary)
            
            # Perform OCR with detailed output
            ocr_data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
            
            # Search for the text in OCR results
            search_text = text if case_sensitive else text.lower()
            
            for i, word in enumerate(ocr_data['text']):
                word_to_compare = word if case_sensitive else word.lower()
                
                if search_text in word_to_compare:
                    # Get bounding box
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    width = ocr_data['width'][i]
                    height = ocr_data['height'][i]
                    
                    logger.info(f"Found text '{text}' at ({x}, {y})")
                    return (x, y, width, height)
                    
            logger.warning(f"Text not found: '{text}'")
            return None
            
        except Exception as e:
            logger.error(f"Error finding text: {e}")
            return None
            
    def detect_ui_elements(
        self, 
        screenshot: Optional[np.ndarray] = None
    ) -> Dict[str, List[Tuple[int, int, int, int]]]:
        """
        Detect common UI elements on the screen
        
        Args:
            screenshot: Optional screenshot to search in (takes new screenshot if None)
            
        Returns:
            Dictionary mapping element types to lists of bounding boxes
        """
        try:
            # Get screenshot if not provided
            if screenshot is None:
                screenshot = self.take_screenshot()
                if screenshot is None:
                    return {}
                    
            # Convert to grayscale
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            
            # Dictionary to store detected elements
            elements = {
                'buttons': [],
                'text_fields': [],
                'checkboxes': [],
                'dropdowns': []
            }
            
            # Detect buttons (look for rectangular shapes with consistent color)
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Approximate the contour to a polygon
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(approx)
                
                # Filter by size (avoid tiny elements)
                if w < 20 or h < 10:
                    continue
                    
                # Calculate aspect ratio
                aspect_ratio = float(w) / h
                
                # Buttons typically have aspect ratios between 1.5 and 5
                if 1.5 <= aspect_ratio <= 5 and 20 <= w <= 300 and 10 <= h <= 100:
                    # Check if it has a consistent fill color (potential button)
                    roi = screenshot[y:y+h, x:x+w]
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    
                    # Calculate color histogram
                    hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
                    
                    # If the histogram has peaks (consistent colors), it's likely a button
                    if np.max(hist) > (w * h * 0.5):
                        elements['buttons'].append((x, y, w, h))
                        
            # Simple heuristic for text fields (rectangles with high width/height ratio)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size
                if w < 50 or h < 15:
                    continue
                    
                aspect_ratio = float(w) / h
                
                # Text fields typically have higher aspect ratios
                if aspect_ratio > 3 and 100 <= w <= 500 and 15 <= h <= 40:
                    elements['text_fields'].append((x, y, w, h))
                    
            # Note: More sophisticated detection would require ML-based approaches
            # This is a simplified version using basic computer vision techniques
            
            logger.info(f"Detected UI elements: {sum(len(v) for v in elements.values())}")
            return elements
            
        except Exception as e:
            logger.error(f"Error detecting UI elements: {e}")
            return {}
            
    def save_reference_image(
        self, 
        name: str, 
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[str]:
        """
        Save a reference image for later use
        
        Args:
            name: Name to save the image as
            region: Optional region to capture (x, y, width, height)
            
        Returns:
            Path to the saved image, or None if failed
        """
        try:
            # Take screenshot
            screenshot = self.take_screenshot()
            if screenshot is None:
                return None
                
            # Crop if region specified
            if region:
                x, y, width, height = region
                screenshot = screenshot[y:y+height, x:x+width]
                
            # Ensure filename has .png extension
            if not name.lower().endswith('.png'):
                name = f"{name}.png"
                
            # Create full path
            path = os.path.join(self.reference_dir, name)
            
            # Save image
            cv2.imwrite(path, screenshot)
            logger.info(f"Saved reference image: {path}")
            
            return path
            
        except Exception as e:
            logger.error(f"Error saving reference image: {e}")
            return None
            
    @fallback(default_value=[])
    def extract_all_text(
        self, 
        screenshot: Optional[np.ndarray] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract all text from the screen with position information
        
        Args:
            screenshot: Optional screenshot to search in (takes new screenshot if None)
            
        Returns:
            List of dictionaries with text and position information
        """
        try:
            # Get screenshot if not provided
            if screenshot is None:
                screenshot = self.take_screenshot()
                if screenshot is None:
                    return []
                    
            # Convert to grayscale for OCR
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing to improve OCR accuracy
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert numpy array to PIL Image for pytesseract
            pil_img = Image.fromarray(binary)
            
            # Perform OCR with detailed output
            ocr_data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
            
            # Process OCR results
            results = []
            for i, text in enumerate(ocr_data['text']):
                # Skip empty text
                if not text.strip():
                    continue
                    
                # Create result dictionary
                result = {
                    'text': text,
                    'confidence': ocr_data['conf'][i],
                    'x': ocr_data['left'][i],
                    'y': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                    'block_num': ocr_data['block_num'][i],
                    'line_num': ocr_data['line_num'][i]
                }
                
                results.append(result)
                
            logger.info(f"Extracted {len(results)} text elements")
            return results
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return []
