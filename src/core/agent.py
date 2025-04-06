import pyautogui
import time
import os
import logging
from src.utils.resilience import retry, CircuitBreaker, fallback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SimpleComputerAgent')

class SimpleComputerAgent:
    def __init__(self):
        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen size detected: {self.screen_width}x{self.screen_height}")
        
        # Set up screenshot directory
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        logger.info(f"Screenshot directory: {self.screenshot_dir}")
        
        # Initialize circuit breakers for critical operations
        self.mouse_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
        self.keyboard_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
        self.screenshot_circuit = CircuitBreaker(failure_threshold=2, recovery_timeout=15.0)
        
    @retry(max_attempts=3, delay=0.5, exceptions=(Exception,))
    def move(self, x, y):
        """Move mouse to absolute coordinates with retry mechanism"""
        try:
            # Validate coordinates
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                logger.error(f"Invalid coordinates: x={x}, y={y} - must be numbers")
                return False
                
            # Ensure coordinates are within screen bounds
            x = max(0, min(x, self.screen_width))
            y = max(0, min(y, self.screen_height))
            
            # Use circuit breaker for mouse operations
            @self.mouse_circuit
            def _move_mouse(x, y):
                pyautogui.moveTo(x, y, duration=0.5)
                return True
                
            result = _move_mouse(x, y)
            if result is None:  # Circuit is open
                logger.warning("Mouse movement circuit is open, operation skipped")
                return False
                
            logger.info(f"Moved to position ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"Error moving mouse: {e}")
            return False
        
    @retry(max_attempts=2, delay=0.3, exceptions=(Exception,))
    def click(self):
        """Click at current position with retry mechanism"""
        try:
            # Use circuit breaker for mouse operations
            @self.mouse_circuit
            def _click_mouse():
                pyautogui.click()
                return True
                
            result = _click_mouse()
            if result is None:  # Circuit is open
                logger.warning("Mouse click circuit is open, operation skipped")
                return False
                
            logger.info("Clicked at current position")
            return True
        except Exception as e:
            logger.error(f"Error clicking: {e}")
            return False
        
    @retry(max_attempts=2, delay=0.3, exceptions=(Exception,))
    def double_click(self):
        """Double click at current position with retry mechanism"""
        try:
            # Use circuit breaker for mouse operations
            @self.mouse_circuit
            def _double_click_mouse():
                pyautogui.doubleClick()
                return True
                
            result = _double_click_mouse()
            if result is None:  # Circuit is open
                logger.warning("Mouse double-click circuit is open, operation skipped")
                return False
                
            logger.info("Double-clicked at current position")
            return True
        except Exception as e:
            logger.error(f"Error double-clicking: {e}")
            return False
            
    @retry(max_attempts=2, delay=0.5, exceptions=(Exception,))
    def right_click(self):
        """Right click at current position with retry mechanism"""
        try:
            # Use circuit breaker for mouse operations
            @self.mouse_circuit
            def _right_click_mouse():
                pyautogui.rightClick()
                return True
                
            result = _right_click_mouse()
            if result is None:  # Circuit is open
                logger.warning("Mouse right-click circuit is open, operation skipped")
                return False
                
            logger.info("Right-clicked at current position")
            return True
        except Exception as e:
            logger.error(f"Error right-clicking: {e}")
            return False
            
    @retry(max_attempts=3, delay=0.3, backoff_factor=1.5, exceptions=(Exception,))
    def type_text(self, text):
        """Type text at current position with retry mechanism"""
        try:
            # Validate text
            if not isinstance(text, str):
                logger.error(f"Invalid text: {text} - must be a string")
                return False
                
            # Use circuit breaker for keyboard operations
            @self.keyboard_circuit
            def _type_text(text):
                pyautogui.write(text, interval=0.05)
                return True
                
            result = _type_text(text)
            if result is None:  # Circuit is open
                logger.warning("Keyboard circuit is open, operation skipped")
                return False
                
            logger.info(f"Typed text: {text[:20]}{'...' if len(text) > 20 else ''}")
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
            
    @retry(max_attempts=2, delay=0.3, exceptions=(Exception,))
    def press_key(self, key):
        """Press a keyboard key with retry mechanism"""
        try:
            # Validate key
            if not isinstance(key, str):
                logger.error(f"Invalid key: {key} - must be a string")
                return False
                
            # Use circuit breaker for keyboard operations
            @self.keyboard_circuit
            def _press_key(key):
                pyautogui.press(key)
                return True
                
            result = _press_key(key)
            if result is None:  # Circuit is open
                logger.warning("Keyboard circuit is open, operation skipped")
                return False
                
            logger.info(f"Pressed key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return False
            
    @fallback(default_value=None)
    @retry(max_attempts=2, delay=1.0, exceptions=(Exception,))
    def take_screenshot(self, filename=None):
        """Take a screenshot with retry mechanism and fallback"""
        try:
            # Use circuit breaker for screenshot operations
            @self.screenshot_circuit
            def _take_screenshot():
                screenshot = pyautogui.screenshot()
                return screenshot
                
            screenshot = _take_screenshot()
            if screenshot is None:  # Circuit is open
                logger.warning("Screenshot circuit is open, operation skipped")
                return None
                
            # Generate filename if not provided
            if filename is None:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"{self.screenshot_dir}/screenshot_{timestamp}.png"
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Save screenshot
            screenshot.save(filename)
            logger.info(f"Screenshot saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
            
    def self_heal(self):
        """Attempt to recover from common failure scenarios"""
        logger.info("Attempting self-healing procedures...")
        
        # Reset PyAutoGUI fail-safe
        pyautogui.FAILSAFE = True
        
        # Move mouse to a safe position (center of screen)
        try:
            pyautogui.moveTo(self.screen_width // 2, self.screen_height // 2, duration=1.0)
            logger.info("Moved mouse to center of screen")
        except Exception as e:
            logger.error(f"Failed to move mouse during self-healing: {e}")
            
        # Reset circuit breakers
        self.mouse_circuit.state = CircuitBreaker.CLOSED
        self.mouse_circuit.failure_count = 0
        self.keyboard_circuit.state = CircuitBreaker.CLOSED
        self.keyboard_circuit.failure_count = 0
        self.screenshot_circuit.state = CircuitBreaker.CLOSED
        self.screenshot_circuit.failure_count = 0
        logger.info("Reset all circuit breakers")
        
        # Small delay to let system stabilize
        time.sleep(1.0)
        
        return True

    def run_command(self, command):
        """Parse and run a simple command"""
        if not isinstance(command, str):
            return "Invalid command: must be a string"
            
        parts = command.strip().split()
        if not parts:
            return "Empty command"
            
        action = parts[0].lower()
        
        try:
            if action == "move" and len(parts) == 3:
                try:
                    x, y = int(parts[1]), int(parts[2])
                    if self.move(x, y):
                        return f"Moved to ({x}, {y})"
                    else:
                        return "Failed to move mouse"
                except ValueError:
                    return "Invalid coordinates: must be integers"
                    
            elif action == "click":
                if self.click():
                    return "Clicked"
                else:
                    return "Failed to click"
                
            elif action == "doubleclick":
                if self.double_click():
                    return "Double-clicked"
                else:
                    return "Failed to double-click"
                
            elif action == "screenshot":
                filename = self.take_screenshot()
                if filename:
                    return f"Took screenshot: {filename}"
                else:
                    return "Failed to take screenshot"
                
            elif action == "type" and len(parts) > 1:
                text = " ".join(parts[1:])
                if self.type_text(text):
                    return f"Typed: {text}"
                else:
                    return "Failed to type text"
                
            else:
                return f"Unknown command: {command}"
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            return f"Error executing command: {str(e)}"
