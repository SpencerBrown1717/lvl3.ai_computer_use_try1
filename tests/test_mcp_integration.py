"""
Integration tests for the MCP server and client
"""
import unittest
import os
import sys
import time
import subprocess
import signal
import requests
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.api.mcp_client import MCPClient

class TestMCPIntegration(unittest.TestCase):
    """Integration tests for MCP server and client"""
    
    @classmethod
    def setUpClass(cls):
        """Start the MCP server for testing"""
        # Set test API key
        os.environ['MCP_API_KEY'] = 'test_api_key'
        os.environ['MCP_PORT'] = '5050'  # Use a different port for testing
        
        # Start MCP server as a subprocess
        cls.server_process = subprocess.Popen(
            [sys.executable, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'api', 'simple_mcp_server.py')],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy()
        )
        
        # Wait for server to start
        time.sleep(1)
        
        # Check if server is running
        try:
            response = requests.get("http://127.0.0.1:5050/api/v1/status")
            if response.status_code != 200:
                raise Exception("Server not responding correctly")
        except Exception as e:
            cls.tearDownClass()
            raise Exception(f"Failed to start MCP server: {e}")
            
        print("MCP server started for testing")
        
    @classmethod
    def tearDownClass(cls):
        """Stop the MCP server after testing"""
        # Terminate the server process
        cls.server_process.terminate()
        cls.server_process.wait(timeout=5)
        
    def setUp(self):
        """Set up test client"""
        self.client = MCPClient(
            base_url="http://localhost:5050",
            api_key="test_api_key"
        )
        
    def test_server_status(self):
        """Test that the server is running and responding"""
        try:
            response = requests.get("http://localhost:5050/api/v1/status")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get('status'), 'online')
        except requests.RequestException as e:
            self.fail(f"Server is not responding: {e}")
            
    def test_client_connection(self):
        """Test that the client can connect to the server"""
        self.assertTrue(self.client.connected)
        
    @patch('src.api.mcp_client.requests.post')
    def test_move_mouse(self, mock_post):
        """Test mouse movement via MCP"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        # Test move mouse
        result = self.client.move_mouse(500, 300)
        self.assertTrue(result)
        
        # Verify the request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("/mouse/move", args[0])
        self.assertEqual(kwargs['json'], {"x": 500, "y": 300})
        self.assertEqual(kwargs['headers']['X-API-Key'], "test_api_key")
        
    @patch('src.api.mcp_client.requests.post')
    def test_click_mouse(self, mock_post):
        """Test mouse clicking via MCP"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        # Test click mouse
        result = self.client.click()
        self.assertTrue(result)
        
        # Verify the request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("/mouse/click", args[0])
        
    @patch('src.api.mcp_client.requests.post')
    def test_type_text(self, mock_post):
        """Test typing text via MCP"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        # Test type text
        result = self.client.type_text("Hello, world!")
        self.assertTrue(result)
        
        # Verify the request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("/keyboard/type", args[0])
        self.assertEqual(kwargs['json'], {"text": "Hello, world!"})

if __name__ == '__main__':
    unittest.main()
