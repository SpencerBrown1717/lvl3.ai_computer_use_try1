from browser_agent import BrowserAgent
import time

def main():
    # Initialize the browser agent
    agent = BrowserAgent()
    
    print("Starting browser workflow example...")
    
    # Step 1: Open Chrome browser
    print("Opening Chrome browser...")
    agent.open_browser("chrome")
    time.sleep(2)  # Wait for browser to fully load
    
    # Step 2: Navigate to a website
    print("Navigating to Google...")
    agent.navigate_to_url("https://www.google.com")
    time.sleep(3)  # Wait for page to load
    
    # Step 3: Search for something
    print("Searching for 'python automation'...")
    agent.type_text("python automation")
    agent.press("enter")
    time.sleep(3)  # Wait for search results
    
    # Step 4: Take a screenshot of the results
    print("Taking screenshot of search results...")
    screenshot_path = agent.take_screenshot()
    print(f"Screenshot saved to: {screenshot_path}")
    
    # Step 5: Create and save a reference image for a search result
    # This would capture the first search result to use later
    print("Saving reference image of first search result...")
    # Approximate location of first result (you'd need to adjust these coordinates)
    first_result_region = (300, 300, 600, 100)  # (x, y, width, height)
    reference_image = agent.save_reference_image("first_search_result", region=first_result_region)
    
    # Step 6: Click on the saved reference image
    print("Clicking on the first search result...")
    success = agent.click_on_image(reference_image)
    if success:
        print("Successfully clicked on the first search result!")
    else:
        print("Could not find the reference image on screen.")
    
    print("Browser workflow example completed!")

if __name__ == "__main__":
    main()
