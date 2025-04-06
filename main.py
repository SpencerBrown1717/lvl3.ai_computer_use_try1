#!/usr/bin/env python3
"""
Computer Control Agent - Main CLI Interface
This provides a simple command-line interface to control the computer
"""

import os
import sys
import time
import logging
import requests
from agent import SimpleComputerAgent
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Load environment variables
load_dotenv()

def check_mcp_server():
    """Check if the MCP server is running"""
    mcp_port = os.getenv('MCP_PORT', '5000')
    mcp_host = os.getenv('MCP_BIND_HOST', '127.0.0.1')
    
    try:
        response = requests.get(f"http://{mcp_host}:{mcp_port}/api/v1/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return True, data
        return False, None
    except requests.exceptions.RequestException:
        return False, None

def print_help():
    """Print help information"""
    print("\nAvailable commands:")
    print("  move X Y       - Move mouse to coordinates X,Y")
    print("  click          - Click at current position")
    print("  doubleclick    - Double-click at current position")
    print("  screenshot     - Take a screenshot")
    print("  type TEXT      - Type the specified text")
    print("  help           - Show this help message")
    print("  exit           - Exit the program")
    print("\nExample: move 100 200")

def main():
    """Main function"""
    try:
        # Check if MCP server is running
        mcp_running, mcp_data = check_mcp_server()
        
        # Initialize agent
        agent = SimpleComputerAgent()
        
        # Print welcome message
        print("\n===== Computer Control Agent =====")
        print("A tool for AI agents to control computer systems")
        
        if mcp_running:
            print("\n✅ MCP Server is running!")
            print(f"   Version: {mcp_data.get('version', 'unknown')}")
            print("   AI agents can connect via HTTP to control this computer")
        else:
            print("\n⚠️  MCP Server is not running")
            print("   To enable remote control, start the MCP server with:")
            print("   python mcp_server.py")
        
        print("\nEnter commands to control the computer directly.")
        print("Type 'help' for available commands or 'exit' to quit.")
        
        # Main command loop
        while True:
            try:
                user_input = input("\n> ")
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() == "exit":
                    print("Exiting...")
                    break
                    
                if user_input.lower() == "help":
                    print_help()
                    continue
                    
                # Execute the command
                result = agent.run_command(user_input)
                print(result)
                
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                print(f"Error: {str(e)}")
                
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
