import pyautogui
import time
import os
import cv2
import numpy as np
from agent import SimpleComputerAgent

class BrowserAgent(SimpleComputerAgent):
    def __init__(self):
        super().__init__()
        # Directory for reference images
        self.images_dir = "reference_images"
        os.makedirs(self.images_dir, exist_ok=True)
        
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
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                point = pyautogui.center(location)
                return (point.x, point.y)
            return None
        except Exception as e:
            print(f"Error finding image: {e}")
            return None
    
    def save_reference_image(self, name, region=None):
        """
        Save a reference image for later use
        
        Args:
            name: Name to save the image as
            region: (x, y, width, height) region to capture, or None for full screen
            
        Returns:
            Path to the saved image
        """
        image_path = f"{self.images_dir}/{name}.png"
        screenshot = pyautogui.screenshot(region=region)
        screenshot.save(image_path)
        print(f"Saved reference image: {image_path}")
        return image_path
    
    def click_on_image(self, image_path, confidence=0.8):
        """
        Find and click on an image
        
        Args:
            image_path: Path to the image to find and click
            confidence: Confidence threshold (0-1)
            
        Returns:
            True if successful, False otherwise
        """
        coords = self.find_on_screen(image_path, confidence)
        if coords:
            self.move(*coords)
            self.click()
            return True
        else:
            print(f"Could not find image: {image_path}")
            return False
    
    def open_browser(self, browser_name="chrome"):
        """
        Open a web browser
        
        Args:
            browser_name: Name of the browser (chrome, firefox, safari)
            
        Returns:
            True if successful, False otherwise
        """
        browser_commands = {
            "chrome": "open -a 'Google Chrome'",
            "firefox": "open -a Firefox",
            "safari": "open -a Safari"
        }
        
        if browser_name.lower() in browser_commands:
            os.system(browser_commands[browser_name.lower()])
            time.sleep(2)  # Wait for browser to open
            return True
        else:
            print(f"Unknown browser: {browser_name}")
            return False
    
    def navigate_to_url(self, url):
        """
        Navigate to a URL in the current browser
        
        Args:
            url: URL to navigate to
            
        Returns:
            True if successful, False otherwise
        """
        # Press Command+L to focus on address bar
        pyautogui.hotkey('command', 'l')
        time.sleep(0.5)
        
        # Type the URL
        self.type_text(url)
        time.sleep(0.5)
        
        # Press Enter
        pyautogui.press('enter')
        time.sleep(2)  # Wait for page to load
        return True
    
    def press(self, key):
        """
        Press a keyboard key
        
        Args:
            key: Key to press (e.g., 'enter', 'tab', 'esc')
            
        Returns:
            None
        """
        pyautogui.press(key)
        print(f"Pressed key: {key}")
    
    def create_workflow(self, name, steps):
        """
        Create a workflow with multiple steps
        
        Args:
            name: Name of the workflow
            steps: List of (action, params) tuples
            
        Returns:
            Workflow function that executes all steps
        """
        def workflow():
            print(f"Running workflow: {name}")
            for step in steps:
                action, params = step
                if action == "open_browser":
                    self.open_browser(params)
                elif action == "navigate_to_url":
                    self.navigate_to_url(params)
                elif action == "click_on_image":
                    self.click_on_image(params)
                elif action == "wait":
                    time.sleep(params)
                elif action == "type":
                    self.type_text(params)
                elif action == "press":
                    pyautogui.press(params)
                elif action == "hotkey":
                    pyautogui.hotkey(*params.split('+'))
                elif action == "move":
                    x, y = params
                    self.move(x, y)
                elif action == "click":
                    self.click()
                else:
                    print(f"Unknown action: {action}")
            print(f"Workflow {name} completed")
        
        return workflow
    
    def record_workflow(self, name):
        """
        Record a workflow by capturing user actions
        
        Args:
            name: Name of the workflow
            
        Returns:
            List of recorded steps
        """
        print(f"Recording workflow: {name}")
        print("Press 'Esc' to stop recording")
        
        steps = []
        recording = True
        
        # Simple recording mechanism - this is just a placeholder
        # A real implementation would need to monitor mouse/keyboard events
        while recording:
            user_input = input("Enter action (browser/url/click/type/wait/done): ")
            
            if user_input == "done" or user_input.lower() == "esc":
                recording = False
            elif user_input == "browser":
                browser = input("Enter browser name: ")
                steps.append(("open_browser", browser))
            elif user_input == "url":
                url = input("Enter URL: ")
                steps.append(("navigate_to_url", url))
            elif user_input == "click":
                image_name = input("Enter reference image name: ")
                self.save_reference_image(image_name)
                steps.append(("click_on_image", f"{self.images_dir}/{image_name}.png"))
            elif user_input == "type":
                text = input("Enter text: ")
                steps.append(("type", text))
            elif user_input == "wait":
                seconds = float(input("Enter seconds to wait: "))
                steps.append(("wait", seconds))
        
        print(f"Recorded {len(steps)} steps for workflow: {name}")
        return steps

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
