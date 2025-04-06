#!/usr/bin/env python3
"""
MCP Client Example for Computer Control Agent
This example demonstrates how to use the MCPClient with proper security and error handling
"""

import logging
import os
import sys
import time
from mcp_client import MCPClient
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mcp_client_example')

# Load environment variables
load_dotenv()

def main():
    """Main function demonstrating MCP client usage with proper security and error handling"""
    try:
        # Get API key from environment variables
        api_key = os.getenv('MCP_API_KEY')
        if not api_key:
            logger.error("No API key found. Set MCP_API_KEY in your .env file")
            return 1
            
        # Initialize the MCP client with security
        logger.info("Initializing MCP client")
        client = MCPClient(
            base_url="http://localhost:5000/api/v1",
            api_key=api_key
        )
        
        # Check if the server is running
        logger.info("Checking MCP server status")
        try:
            status = client.get_status()
            logger.info(f"MCP Server is running: {status}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            logger.error("Make sure the MCP server is running (python mcp_server.py)")
            return 1
            
        # Example 1: Take a screenshot
        logger.info("Example 1: Taking a screenshot")
        try:
            screenshot_path = client.take_screenshot()
            logger.info(f"Screenshot saved to: {screenshot_path}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            
        # Example 2: Move and click with error handling
        logger.info("Example 2: Move and click")
        try:
            # Move to coordinates
            client.move_mouse(500, 300)
            logger.info("Successfully moved mouse")
            
            # Click
            client.click()
            logger.info("Successfully clicked")
        except Exception as e:
            logger.error(f"Error during move and click: {e}")
            
        # Example 3: Type text with error handling
        logger.info("Example 3: Type text")
        try:
            client.type_text("Hello from MCP client!")
            logger.info("Successfully typed text")
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            
        # Example 4: Press keys
        logger.info("Example 4: Press keys")
        try:
            client.press_key("enter")
            logger.info("Successfully pressed Enter key")
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            
        logger.info("MCP client example completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
