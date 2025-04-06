import pyautogui
import time
import os
import cv2
import numpy as np
from src.core.agent import SimpleComputerAgent
import subprocess
import logging
from src.core.computer_vision import ComputerVision
from src.utils.resilience import retry, CircuitBreaker, fallback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BrowserAgent')

class BrowserAgent(SimpleComputerAgent):
    def __init__(self):
        super().__init__()
        # Directory for reference images
        self.images_dir = "reference_images"
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Initialize computer vision module
        self.vision = ComputerVision(reference_dir=self.images_dir)
        
        # Initialize circuit breaker for browser operations
        self.browser_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=15.0)
        
    def find_on_screen(self, image_path, confidence=0.8):
        """
        Find an image on the screen and return its position
        
        Args:
            image_path: Path to the image to find
            confidence: Confidence threshold (0-1)
            
        Returns:
            (x, y) coordinates of the center of the image if found, None otherwise
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return None
            
            # Use enhanced computer vision to find the template    
            result = self.vision.find_template(image_path, confidence=confidence)
            if result:
                x, y, width, height = result
                # Return center coordinates
                return (x + width // 2, y + height // 2)
            return None
        except Exception as e:
            logger.error(f"Error finding image: {e}")
            return None
    
    def save_reference_image(self, name, region=None):
        """
        Save a reference image for later use
        
        Args:
            name: Name to save the image as
            region: Optional region to capture (x, y, width, height)
            
        Returns:
            Path to the saved image
        """
        try:
            # Use enhanced computer vision to save the reference image
            path = self.vision.save_reference_image(name, region)
            if path:
                logger.info(f"Saved reference image: {path}")
                return path
            return None
        except Exception as e:
            logger.error(f"Error saving reference image: {e}")
            return None
    
    @retry(max_attempts=3, delay=1.0, backoff_factor=1.5)
    def find_text_on_screen(self, text, case_sensitive=False):
        """
        Find text on the screen using OCR
        
        Args:
            text: Text to find
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            (x, y) coordinates of the center of the text if found, None otherwise
        """
        try:
            # Use enhanced computer vision to find text
            result = self.vision.find_text(text, case_sensitive=case_sensitive)
            if result:
                x, y, width, height = result
                # Return center coordinates
                return (x + width // 2, y + height // 2)
            return None
        except Exception as e:
            logger.error(f"Error finding text: {e}")
            return None
    
    @retry(max_attempts=2, delay=0.5)
    def click_on_text(self, text, case_sensitive=False):
        """
        Find and click on text
        
        Args:
            text: Text to find and click on
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            True if successful, False otherwise
        """
        try:
            position = self.find_text_on_screen(text, case_sensitive)
            if position:
                x, y = position
                return self.move_and_click(x, y)
            logger.warning(f"Text not found: {text}")
            return False
        except Exception as e:
            logger.error(f"Error clicking on text: {e}")
            return False
    
    def move_and_click(self, x, y):
        """
        Move to coordinates and click
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful, False otherwise
        """
        if self.move(x, y):
            return self.click()
        return False
    
    @retry(max_attempts=3, delay=1.0)
    def click_on_image(self, image_path, confidence=0.8):
        """
        Find and click on an image
        
        Args:
            image_path: Path to the image to find and click on
            confidence: Confidence threshold (0-1)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            position = self.find_on_screen(image_path, confidence)
            if position:
                x, y = position
                return self.move_and_click(x, y)
            logger.warning(f"Image not found: {image_path}")
            return False
        except Exception as e:
            logger.error(f"Error clicking on image: {e}")
            return False
    
    @fallback(default_value=[])
    def extract_all_text(self):
        """
        Extract all text from the screen
        
        Returns:
            List of dictionaries with text and position information
        """
        try:
            return self.vision.extract_all_text()
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return []
    
    def detect_ui_elements(self):
        """
        Detect UI elements on the screen
        
        Returns:
            Dictionary mapping element types to lists of bounding boxes
        """
        try:
            return self.vision.detect_ui_elements()
        except Exception as e:
            logger.error(f"Error detecting UI elements: {e}")
            return {}
    
    @retry(max_attempts=2, delay=1.0)
    def open_browser(self, browser="chrome"):
        """
        Open a web browser
        
        Args:
            browser: Browser to open (chrome, firefox, safari, edge)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use circuit breaker for browser operations
            @self.browser_circuit
            def _open_browser(browser):
                if browser.lower() == "chrome":
                    if os.name == "nt":  # Windows
                        subprocess.Popen(["start", "chrome"], shell=True)
                    elif os.name == "posix":  # macOS or Linux
                        if os.path.exists("/Applications/Google Chrome.app"):  # macOS
                            subprocess.Popen(["open", "-a", "Google Chrome"])
                        else:  # Linux
                            subprocess.Popen(["google-chrome"])
                elif browser.lower() == "firefox":
                    if os.name == "nt":  # Windows
                        subprocess.Popen(["start", "firefox"], shell=True)
                    elif os.name == "posix":  # macOS or Linux
                        if os.path.exists("/Applications/Firefox.app"):  # macOS
                            subprocess.Popen(["open", "-a", "Firefox"])
                        else:  # Linux
                            subprocess.Popen(["firefox"])
                elif browser.lower() == "safari" and os.name == "posix" and os.path.exists("/Applications/Safari.app"):
                    subprocess.Popen(["open", "-a", "Safari"])
                elif browser.lower() == "edge":
                    if os.name == "nt":  # Windows
                        subprocess.Popen(["start", "msedge"], shell=True)
                    elif os.name == "posix" and os.path.exists("/Applications/Microsoft Edge.app"):  # macOS
                        subprocess.Popen(["open", "-a", "Microsoft Edge"])
                else:
                    logger.error(f"Unsupported browser: {browser}")
                    return False
                
                # Wait for browser to open
                time.sleep(3)
                return True
            
            result = _open_browser(browser)
            if result is None:  # Circuit is open
                logger.warning("Browser circuit is open, operation skipped")
                return False
                
            logger.info(f"Opened browser: {browser}")
            return True
        except Exception as e:
            logger.error(f"Error opening browser: {e}")
            return False
    
    @retry(max_attempts=3, delay=1.0, backoff_factor=1.5)
    def navigate_to(self, url):
        """
        Navigate to a URL
        
        Args:
            url: URL to navigate to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use circuit breaker for browser operations
            @self.browser_circuit
            def _navigate_to(url):
                # Click in the address bar (common keyboard shortcut)
                if os.name == "nt":  # Windows
                    pyautogui.hotkey("ctrl", "l")
                else:  # macOS or Linux
                    pyautogui.hotkey("command", "l")
                
                # Wait for address bar to be selected
                time.sleep(0.5)
                
                # Clear the address bar
                pyautogui.hotkey("delete")
                
                # Type the URL
                self.type_text(url)
                
                # Press Enter to navigate
                pyautogui.press("enter")
                
                # Wait for page to load
                time.sleep(3)
                return True
            
            result = _navigate_to(url)
            if result is None:  # Circuit is open
                logger.warning("Browser circuit is open, operation skipped")
                return False
                
            logger.info(f"Navigated to: {url}")
            return True
        except Exception as e:
            logger.error(f"Error navigating to URL: {e}")
            return False
    
    def wait_for_element(self, image_path=None, text=None, timeout=30, interval=1.0):
        """
        Wait for an element to appear on the screen
        
        Args:
            image_path: Path to the image to wait for
            text: Text to wait for
            timeout: Maximum time to wait in seconds
            interval: Check interval in seconds
            
        Returns:
            (x, y) coordinates of the element if found, None otherwise
        """
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if image_path:
                    position = self.find_on_screen(image_path)
                    if position:
                        logger.info(f"Found image: {image_path}")
                        return position
                elif text:
                    position = self.find_text_on_screen(text)
                    if position:
                        logger.info(f"Found text: {text}")
                        return position
                
                time.sleep(interval)
            
            logger.warning(f"Timed out waiting for element: {image_path or text}")
            return None
        except Exception as e:
            logger.error(f"Error waiting for element: {e}")
            return None
    
    def execute_workflow(self, workflow):
        """
        Execute a predefined workflow
        
        Args:
            workflow: List of actions to execute
            
        Returns:
            True if all actions succeeded, False otherwise
        """
        try:
            for action in workflow:
                action_type = action.get("type")
                
                if action_type == "open_browser":
                    browser = action.get("browser", "chrome")
                    if not self.open_browser(browser):
                        return False
                        
                elif action_type == "navigate":
                    url = action.get("url")
                    if not self.navigate_to(url):
                        return False
                        
                elif action_type == "click_image":
                    image_path = action.get("image")
                    confidence = action.get("confidence", 0.8)
                    if not self.click_on_image(image_path, confidence):
                        return False
                        
                elif action_type == "click_text":
                    text = action.get("text")
                    case_sensitive = action.get("case_sensitive", False)
                    if not self.click_on_text(text, case_sensitive):
                        return False
                        
                elif action_type == "type":
                    text = action.get("text")
                    if not self.type_text(text):
                        return False
                        
                elif action_type == "press":
                    key = action.get("key")
                    if not self.press_key(key):
                        return False
                        
                elif action_type == "wait":
                    seconds = action.get("seconds", 1)
                    time.sleep(seconds)
                    
                elif action_type == "wait_for":
                    image_path = action.get("image")
                    text = action.get("text")
                    timeout = action.get("timeout", 30)
                    if not self.wait_for_element(image_path, text, timeout):
                        return False
                        
                elif action_type == "screenshot":
                    filename = action.get("filename")
                    if not self.take_screenshot(filename):
                        return False
                        
                else:
                    logger.error(f"Unknown action type: {action_type}")
                    return False
                    
            logger.info("Workflow executed successfully")
            return True
        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return False

# Example usage
if __name__ == "__main__":
    agent = BrowserAgent()
    
    # Example: Create a workflow to open Google and search for something
    google_search_workflow = agent.create_workflow("Google Search", [
        ("open_browser", "chrome"),
        ("navigate_to_url", "https://www.google.com"),
        ("wait", 2),
        ("type", "python automation"),
        ("press", "enter"),
        ("wait", 3)
    ])
    
    # Run the workflow
    google_search_workflow()
    
    # Or record a new workflow
    # steps = agent.record_workflow("Custom Workflow")
    # custom_workflow = agent.create_workflow("Custom Workflow", steps)
    # custom_workflow()
