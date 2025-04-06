"""
Unit tests for the SimpleComputerAgent class
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import tempfile
from PIL import Image

# Add parent directory to path to import agent module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent import SimpleComputerAgent

class TestSimpleComputerAgent(unittest.TestCase):
    """Test cases for SimpleComputerAgent"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a mock for pyautogui
        self.pyautogui_patcher = patch('agent.pyautogui')
        self.mock_pyautogui = self.pyautogui_patcher.start()
        
        # Mock screen size
        self.mock_pyautogui.size.return_value = (1920, 1080)
        
        # Create a temporary directory for screenshots
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Mock os.makedirs to avoid creating directories
        self.makedirs_patcher = patch('os.makedirs')
        self.mock_makedirs = self.makedirs_patcher.start()
        
        # Create the agent
        self.agent = SimpleComputerAgent()
        self.agent.screenshot_dir = self.temp_dir.name
        
    def tearDown(self):
        """Clean up after tests"""
        self.pyautogui_patcher.stop()
        self.makedirs_patcher.stop()
        self.temp_dir.cleanup()
        
    def test_move(self):
        """Test mouse movement"""
        # Test valid movement
        result = self.agent.move(500, 300)
        self.assertTrue(result)
        self.mock_pyautogui.moveTo.assert_called_once_with(500, 300, duration=0.5)
        
        # Reset mock
        self.mock_pyautogui.reset_mock()
        
        # Test boundary checking (beyond screen size)
        result = self.agent.move(2000, 1500)
        self.assertTrue(result)
        self.mock_pyautogui.moveTo.assert_called_once_with(1920, 1080, duration=0.5)
        
        # Reset mock
        self.mock_pyautogui.reset_mock()
        
        # Test invalid input
        result = self.agent.move("invalid", 300)
        self.assertFalse(result)
        self.mock_pyautogui.moveTo.assert_not_called()
        
    def test_click(self):
        """Test mouse clicking"""
        result = self.agent.click()
        self.assertTrue(result)
        self.mock_pyautogui.click.assert_called_once()
        
        # Test exception handling
        self.mock_pyautogui.click.side_effect = Exception("Test exception")
        result = self.agent.click()
        self.assertFalse(result)
        
    def test_double_click(self):
        """Test double clicking"""
        result = self.agent.double_click()
        self.assertTrue(result)
        self.mock_pyautogui.doubleClick.assert_called_once()
        
    def test_type_text(self):
        """Test typing text"""
        result = self.agent.type_text("Hello, world!")
        self.assertTrue(result)
        self.mock_pyautogui.write.assert_called_once_with("Hello, world!", interval=0.05)
        
        # Test invalid input
        result = self.agent.type_text(None)
        self.assertFalse(result)
        
    def test_take_screenshot(self):
        """Test taking screenshots"""
        # Mock screenshot
        mock_screenshot = MagicMock()
        self.mock_pyautogui.screenshot.return_value = mock_screenshot
        
        # Mock save method
        mock_screenshot.save = MagicMock()
        
        # Test taking screenshot
        result = self.agent.take_screenshot()
        self.assertIsNotNone(result)
        self.mock_pyautogui.screenshot.assert_called_once()
        mock_screenshot.save.assert_called_once()
        
        # Test exception handling
        self.mock_pyautogui.screenshot.side_effect = Exception("Test exception")
        result = self.agent.take_screenshot()
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
