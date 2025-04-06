#!/usr/bin/env python3
"""
Browser Workflow Example for Computer Control Agent
This example demonstrates how to use the BrowserAgent with proper error handling
"""

import logging
import time
import os
import sys
from browser_agent import BrowserAgent
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('browser_example')

# Load environment variables
load_dotenv()

def main():
    """Main function demonstrating browser agent usage with proper error handling"""
    try:
        # Initialize the browser agent
        logger.info("Initializing BrowserAgent")
        agent = BrowserAgent()
        
        # Step 1: Open Chrome browser
        logger.info("Opening Chrome browser")
        if not agent.open_browser("chrome"):
            logger.error("Failed to open Chrome browser")
            return 1
        time.sleep(2)  # Wait for browser to fully load
        
        # Step 2: Navigate to a website
        logger.info("Navigating to Google")
        if not agent.navigate_to_url("https://www.google.com"):
            logger.error("Failed to navigate to Google")
            return 1
        time.sleep(3)  # Wait for page to load
        
        # Step 3: Search for something
        logger.info("Searching for 'python automation'")
        if not agent.type_text("python automation"):
            logger.error("Failed to type search query")
            return 1
            
        if not agent.press("enter"):
            logger.error("Failed to press Enter key")
            return 1
            
        logger.info("Waiting for search results")
        time.sleep(3)  # Wait for search results
        
        # Step 4: Take a screenshot of the results
        logger.info("Taking screenshot of search results")
        screenshot_path = agent.take_screenshot()
        if screenshot_path:
            logger.info(f"Screenshot saved to: {screenshot_path}")
        else:
            logger.error("Failed to take screenshot")
            return 1
        
        # Step 5: Create and save a reference image for a search result
        logger.info("Saving reference image of first search result")
        try:
            # Approximate location of first result (you'd need to adjust these coordinates)
            first_result_region = (300, 300, 600, 100)  # (x, y, width, height)
            reference_image = agent.save_reference_image("first_search_result", region=first_result_region)
            if not reference_image:
                logger.error("Failed to save reference image")
                return 1
            logger.info(f"Reference image saved: {reference_image}")
        except Exception as e:
            logger.error(f"Error saving reference image: {e}")
            return 1
        
        # Step 6: Click on the saved reference image
        logger.info("Clicking on the first search result")
        success = agent.click_on_image(reference_image)
        if success:
            logger.info("Successfully clicked on the first search result!")
        else:
            logger.warning("Could not find the reference image on screen")
            # Continue execution even if this step fails
        
        # Wait for the page to load
        logger.info("Waiting for page to load")
        time.sleep(3)
        
        # Take a final screenshot
        final_screenshot = agent.take_screenshot()
        if final_screenshot:
            logger.info(f"Final screenshot saved to: {final_screenshot}")
            
        logger.info("Browser workflow example completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error in browser workflow: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
