import pyautogui
import time
import os

class SimpleComputerAgent:
    def __init__(self):
        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        # Set up screenshot directory
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    def move(self, x, y):
        """Move mouse to absolute coordinates"""
        pyautogui.moveTo(x, y, duration=0.5)
        print(f"Moved to position ({x}, {y})")
        
    def click(self):
        """Click at current position"""
        pyautogui.click()
        print("Clicked at current position")
        
    def double_click(self):
        """Double click at current position"""
        pyautogui.doubleClick()
        print("Double-clicked at current position")
        
    def take_screenshot(self):
        """Take a screenshot and save it"""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{self.screenshot_dir}/screenshot_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        print(f"Screenshot saved as {filename}")
        return filename
        
    def type_text(self, text):
        """Type text at current position"""
        pyautogui.typewrite(text)
        print(f"Typed: {text}")
        
    def run_command(self, command):
        """Parse and run a simple command"""
        parts = command.strip().split()
        if not parts:
            return "Empty command"
            
        action = parts[0].lower()
        
        if action == "move" and len(parts) == 3:
            try:
                x, y = int(parts[1]), int(parts[2])
                self.move(x, y)
                return f"Moved to ({x}, {y})"
            except ValueError:
                return "Invalid coordinates"
                
        elif action == "click":
            self.click()
            return "Clicked"
            
        elif action == "doubleclick":
            self.double_click()
            return "Double-clicked"
            
        elif action == "screenshot":
            filename = self.take_screenshot()
            return f"Took screenshot: {filename}"
            
        elif action == "type" and len(parts) > 1:
            text = " ".join(parts[1:])
            self.type_text(text)
            return f"Typed: {text}"
            
        else:
            return f"Unknown command: {command}"
