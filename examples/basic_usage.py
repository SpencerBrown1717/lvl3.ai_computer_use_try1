#!/usr/bin/env python3
"""
Basic Usage Example for Computer Control Agent
This example demonstrates how to use the SimpleComputerAgent with proper error handling
"""

import logging
import time
from agent import SimpleComputerAgent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('basic_example')

def main():
    """Main function demonstrating basic agent usage"""
    try:
        logger.info("Initializing SimpleComputerAgent")
        agent = SimpleComputerAgent()
        
        # Example 1: Move and click with error handling
        logger.info("Example 1: Move and click")
        if agent.move(500, 300):
            logger.info("Successfully moved to coordinates")
            
            if agent.click():
                logger.info("Successfully clicked")
            else:
                logger.error("Failed to click")
        else:
            logger.error("Failed to move to coordinates")
        
        # Example 2: Type text with error handling
        logger.info("Example 2: Type text")
        if agent.type_text("Hello, this is an automated test"):
            logger.info("Successfully typed text")
        else:
            logger.error("Failed to type text")
        
        # Example 3: Take a screenshot with error handling
        logger.info("Example 3: Take screenshot")
        screenshot_path = agent.take_screenshot()
        if screenshot_path:
            logger.info(f"Screenshot saved to: {screenshot_path}")
        else:
            logger.error("Failed to take screenshot")
        
        # Example 4: Using the run_command interface
        logger.info("Example 4: Using run_command")
        commands = [
            "move 100 100",
            "click",
            "type This text was typed using run_command",
            "screenshot"
        ]
        
        for cmd in commands:
            logger.info(f"Running command: {cmd}")
            result = agent.run_command(cmd)
            logger.info(f"Result: {result}")
            time.sleep(1)  # Small delay between commands
            
        logger.info("Basic usage example completed successfully")
        
    except Exception as e:
        logger.error(f"Error in basic usage example: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())
