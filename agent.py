import pyautogui
import time
import os
import logging

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
        
    def move(self, x, y):
        """Move mouse to absolute coordinates"""
        try:
            # Validate coordinates
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                logger.error(f"Invalid coordinates: x={x}, y={y} - must be numbers")
                return False
                
            # Ensure coordinates are within screen bounds
            x = max(0, min(x, self.screen_width))
            y = max(0, min(y, self.screen_height))
            
            pyautogui.moveTo(x, y, duration=0.5)
            logger.info(f"Moved to position ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"Error moving mouse: {e}")
            return False
        
    def click(self):
        """Click at current position"""
        try:
            pyautogui.click()
            logger.info("Clicked at current position")
            return True
        except Exception as e:
            logger.error(f"Error clicking: {e}")
            return False
        
    def double_click(self):
        """Double click at current position"""
        try:
            pyautogui.doubleClick()
            logger.info("Double-clicked at current position")
            return True
        except Exception as e:
            logger.error(f"Error double-clicking: {e}")
            return False
        
    def take_screenshot(self):
        """Take a screenshot and save it"""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{self.screenshot_dir}/screenshot_{timestamp}.png"
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            logger.info(f"Screenshot saved as {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
        
    def type_text(self, text):
        """Type text at current position"""
        try:
            if not isinstance(text, str):
                logger.error(f"Invalid text: {text} - must be a string")
                return False
                
            pyautogui.typewrite(text)
            logger.info(f"Typed: {text}")
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
        
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
