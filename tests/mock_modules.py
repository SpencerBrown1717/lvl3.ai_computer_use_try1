"""
Mock modules for testing without requiring actual dependencies
"""

import unittest.mock as mock

# Create mock classes for PyAutoGUI-dependent modules
class MockPyAutoGUI:
    """Mock implementation of PyAutoGUI for testing"""
    
    def __init__(self):
        self.position = (0, 0)
    
    def moveTo(self, x, y, duration=0.25):
        self.position = (x, y)
        return True
    
    def click(self, x=None, y=None, clicks=1, interval=0.0, button='left', duration=0.0):
        if x is not None and y is not None:
            self.position = (x, y)
        return True
    
    def doubleClick(self, x=None, y=None, interval=0.0, button='left', duration=0.0):
        return self.click(x, y, clicks=2, interval=interval, button=button, duration=duration)
    
    def typewrite(self, text, interval=0.0):
        return True
    
    def screenshot(self, region=None):
        # Return a mock PIL Image
        return mock.MagicMock()
    
    def locateOnScreen(self, image, confidence=0.9):
        # Return a mock location
        return (100, 100, 50, 50)
    
    def locateCenterOnScreen(self, image, confidence=0.9):
        # Return a mock center point
        return (125, 125)

# Create a patch function to use in tests
def patch_dependencies():
    """
    Patch dependencies for testing
    Returns a dictionary of patches that should be used as context managers
    """
    patches = {
        'pyautogui': mock.patch('pyautogui.PyAutoGUI', MockPyAutoGUI),
    }
    return patches
