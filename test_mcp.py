"""
Test script for the Machine Control Protocol (MCP)
This script tests the MCP server and client to ensure they work correctly
"""

import time
import sys
import os
import subprocess
import signal
from mcp_client import MCPClient

def start_server():
    """Start the MCP server in a separate process"""
    print("Starting MCP server...")
    # Start the server in a new process
    server_process = subprocess.Popen(
        [sys.executable, "mcp_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give the server time to start
    time.sleep(3)
    return server_process

def test_client_connection():
    """Test that the client can connect to the server"""
    print("\nTesting client connection...")
    client = MCPClient()
    
    if client.connected:
        print("✅ Client connected to server successfully")
        return client
    else:
        print("❌ Client failed to connect to server")
        return None

def test_status_endpoint(client):
    """Test the status endpoint"""
    print("\nTesting status endpoint...")
    status = client.check_status()
    
    if status and status.get('status') == 'online':
        print(f"✅ Status endpoint working: {status}")
        return True
    else:
        print(f"❌ Status endpoint failed: {status}")
        return False

def test_mouse_movement(client):
    """Test mouse movement"""
    print("\nTesting mouse movement...")
    try:
        # Get current screen size
        import pyautogui
        screen_width, screen_height = pyautogui.size()
        
        # Move to center of screen
        center_x, center_y = screen_width // 2, screen_height // 2
        result = client.move_mouse(center_x, center_y)
        
        if result and result.get('success'):
            print(f"✅ Mouse movement working: {result}")
            return True
        else:
            print(f"❌ Mouse movement failed: {result}")
            return False
    except Exception as e:
        print(f"❌ Mouse movement test error: {str(e)}")
        return False

def test_keyboard_typing(client):
    """Test keyboard typing in a safe way"""
    print("\nTesting keyboard functionality...")
    try:
        # We'll just test the API call without actually typing
        # to avoid interfering with the user's system
        result = client.press_key('escape')
        
        if result and result.get('success'):
            print(f"✅ Keyboard functionality working: {result}")
            return True
        else:
            print(f"❌ Keyboard functionality failed: {result}")
            return False
    except Exception as e:
        print(f"❌ Keyboard test error: {str(e)}")
        return False

def run_tests():
    """Run all tests"""
    # Start the server
    server_process = start_server()
    
    try:
        # Test client connection
        client = test_client_connection()
        if not client:
            print("\n❌ Cannot proceed with tests: Client connection failed")
            return False
        
        # Test status endpoint
        status_test = test_status_endpoint(client)
        if not status_test:
            print("\n❌ Cannot proceed with tests: Status endpoint failed")
            return False
        
        # Test mouse movement
        mouse_test = test_mouse_movement(client)
        
        # Test keyboard typing
        keyboard_test = test_keyboard_typing(client)
        
        # Overall test result
        if mouse_test and keyboard_test:
            print("\n✅ All tests passed! The MCP is working correctly.")
            return True
        else:
            print("\n❌ Some tests failed. Please check the logs above.")
            return False
            
    except Exception as e:
        print(f"\n❌ Test suite error: {str(e)}")
        return False
    finally:
        # Stop the server
        print("\nStopping MCP server...")
        try:
            server_process.terminate()
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            print("Had to forcefully kill the server process")

if __name__ == "__main__":
    print("=== MCP Test Suite ===")
    success = run_tests()
    
    if success:
        print("\nThe Machine Control Protocol is ready to use!")
        print("AI agents can now connect to your Computer Control Agent.")
    else:
        print("\nSome issues were detected with the MCP implementation.")
        print("Please fix the issues before using the MCP.")
    
    sys.exit(0 if success else 1)
