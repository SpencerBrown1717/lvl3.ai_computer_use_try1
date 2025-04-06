import requests
import json
import base64
import time
from PIL import Image
import io

class MCPClient:
    """
    Client for the Machine Control Protocol (MCP)
    Allows AI agents to easily control a computer through the MCP server
    """
    
    def __init__(self, base_url="http://localhost:5000", fallback_ports=[5001, 5002], api_key=None):
        """
        Initialize the MCP client
        
        Args:
            base_url: Base URL of the MCP server
            fallback_ports: List of ports to try if the main port fails
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.fallback_ports = fallback_ports
        self.connected = False
        self.api_key = api_key
        self.headers = {}
        
        if self.api_key:
            self.headers['X-API-Key'] = self.api_key
        
        # Try to connect to the server
        try:
            response = requests.get(f"{self.api_base}/status", timeout=2, headers=self.headers)
            if response.status_code == 200:
                self.connected = True
                
                # If no API key is provided, try to get one from the setup endpoint
                if not self.api_key:
                    try:
                        setup_response = requests.get(f"{self.api_base}/setup", timeout=2)
                        if setup_response.status_code == 200:
                            setup_data = setup_response.json()
                            if 'api_key' in setup_data:
                                self.api_key = setup_data['api_key']
                                self.headers['X-API-Key'] = self.api_key
                                print(f"Retrieved API key from server: {self.api_key}")
                    except Exception as e:
                        print(f"Warning: Could not retrieve API key: {str(e)}")
                        
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # Try fallback ports
            original_port = int(self.base_url.split(':')[-1])
            base_without_port = self.base_url.rsplit(':', 1)[0]
            
            for port in self.fallback_ports:
                if port == original_port:
                    continue
                    
                try:
                    self.base_url = f"{base_without_port}:{port}"
                    self.api_base = f"{self.base_url}/api/v1"
                    response = requests.get(f"{self.api_base}/status", timeout=2, headers=self.headers)
                    if response.status_code == 200:
                        self.connected = True
                        print(f"Connected to MCP server at {self.base_url}")
                        
                        # If no API key is provided, try to get one from the setup endpoint
                        if not self.api_key:
                            try:
                                setup_response = requests.get(f"{self.api_base}/setup", timeout=2)
                                if setup_response.status_code == 200:
                                    setup_data = setup_response.json()
                                    if 'api_key' in setup_data:
                                        self.api_key = setup_data['api_key']
                                        self.headers['X-API-Key'] = self.api_key
                                        print(f"Retrieved API key from server: {self.api_key}")
                            except Exception as e:
                                print(f"Warning: Could not retrieve API key: {str(e)}")
                                
                        break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    continue
                    
            if not self.connected:
                print("Warning: Could not connect to MCP server. Make sure it's running.")
    
    def _handle_request_errors(self, request_func):
        """
        Handle request errors for API calls
        
        Args:
            request_func: Function that makes the API call
            
        Returns:
            Response with error handling
        """
        try:
            return request_func()
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to MCP server")
            return {"success": False, "error": "Connection error"}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print("Error: Rate limit exceeded. Try again later.")
                return {"success": False, "error": "Rate limit exceeded"}
            print(f"HTTP Error: {str(e)}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print(f"Error: {str(e)}")
            return {"success": False, "error": str(e)}
        
    def _check_status(self):
        """Internal method to check server status without error handling"""
        response = requests.get(f"{self.api_base}/status", headers=self.headers)
        return response.json()
        
    def check_status(self):
        """Check if the MCP server is running"""
        return self._handle_request_errors(
            lambda: requests.get(f"{self.api_base}/status", headers=self.headers).json()
        )
        
    def take_screenshot(self, as_pil_image=False):
        """
        Take a screenshot
        
        Args:
            as_pil_image: If True, returns a PIL Image object instead of the response
            
        Returns:
            If as_pil_image is True, returns a PIL Image object
            Otherwise, returns the response JSON with base64 encoded image
        """
        def request_func():
            response = requests.get(f"{self.api_base}/screenshot", headers=self.headers)
            data = response.json()
            
            if as_pil_image and data.get('success'):
                image_data = base64.b64decode(data['screenshot'])
                return Image.open(io.BytesIO(image_data))
            
            return data
            
        return self._handle_request_errors(request_func)
        
    def move_mouse(self, x, y):
        """
        Move the mouse to specified coordinates
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Response JSON
        """
        return self._handle_request_errors(
            lambda: requests.post(
                f"{self.api_base}/mouse/move", 
                json={"x": x, "y": y},
                headers=self.headers
            ).json()
        )
        
    def click(self, x=None, y=None):
        """
        Click at the current mouse position or at specified coordinates
        
        Args:
            x: Optional X coordinate
            y: Optional Y coordinate
            
        Returns:
            Response JSON
        """
        def request_func():
            payload = {}
            if x is not None and y is not None:
                payload = {"x": x, "y": y}
                
            response = requests.post(f"{self.api_base}/mouse/click", json=payload, headers=self.headers)
            return response.json()
            
        return self._handle_request_errors(request_func)
        
    def type_text(self, text):
        """
        Type text at the current cursor position
        
        Args:
            text: Text to type
            
        Returns:
            Response JSON
        """
        return self._handle_request_errors(
            lambda: requests.post(
                f"{self.api_base}/keyboard/type", 
                json={"text": text},
                headers=self.headers
            ).json()
        )
        
    def press_key(self, key):
        """
        Press a keyboard key
        
        Args:
            key: Key to press
            
        Returns:
            Response JSON
        """
        return self._handle_request_errors(
            lambda: requests.post(
                f"{self.api_base}/keyboard/press", 
                json={"key": key},
                headers=self.headers
            ).json()
        )
        
    def open_browser(self, browser="chrome"):
        """
        Open a web browser
        
        Args:
            browser: Browser name (chrome, firefox, safari)
            
        Returns:
            Response JSON
        """
        return self._handle_request_errors(
            lambda: requests.post(
                f"{self.api_base}/browser/open", 
                json={"browser": browser},
                headers=self.headers
            ).json()
        )
        
    def navigate_to_url(self, url):
        """
        Navigate to a URL
        
        Args:
            url: URL to navigate to
            
        Returns:
            Response JSON
        """
        return self._handle_request_errors(
            lambda: requests.post(
                f"{self.api_base}/browser/navigate", 
                json={"url": url},
                headers=self.headers
            ).json()
        )
        
    def find_image(self, image_path=None, image_base64=None, confidence=0.8):
        """
        Find an image on screen
        
        Args:
            image_path: Path to the image file
            image_base64: Base64 encoded image data
            confidence: Confidence threshold (0-1)
            
        Returns:
            Response JSON
        """
        def request_func():
            payload = {"confidence": confidence}
            
            if image_path:
                payload["image_path"] = image_path
            elif image_base64:
                payload["image_base64"] = image_base64
            else:
                raise ValueError("Either image_path or image_base64 must be provided")
                
            response = requests.post(f"{self.api_base}/vision/find", json=payload, headers=self.headers)
            return response.json()
            
        return self._handle_request_errors(request_func)
        
    def click_on_image(self, image_path, confidence=0.8):
        """
        Find and click on an image
        
        Args:
            image_path: Path to the image file
            confidence: Confidence threshold (0-1)
            
        Returns:
            Response JSON
        """
        return self._handle_request_errors(
            lambda: requests.post(
                f"{self.api_base}/vision/click_image", 
                json={"image_path": image_path, "confidence": confidence},
                headers=self.headers
            ).json()
        )
        
    def execute_workflow(self, workflow):
        """
        Execute a workflow
        
        Args:
            workflow: List of workflow steps
            
        Returns:
            Response JSON
        """
        return self._handle_request_errors(
            lambda: requests.post(
                f"{self.api_base}/workflow/execute", 
                json={"workflow": workflow},
                headers=self.headers
            ).json()
        )
        
    def create_workflow_step(self, action, **params):
        """
        Create a workflow step
        
        Args:
            action: Action name
            **params: Parameters for the action
            
        Returns:
            Workflow step dict
        """
        return {"action": action, "params": params}
        
    def example_google_search_workflow(self, query):
        """
        Example workflow to search Google
        
        Args:
            query: Search query
            
        Returns:
            Response JSON
        """
        workflow = [
            self.create_workflow_step("open_browser", browser="chrome"),
            self.create_workflow_step("wait", seconds=2),
            self.create_workflow_step("navigate", url="https://www.google.com"),
            self.create_workflow_step("wait", seconds=2),
            self.create_workflow_step("type", text=query),
            self.create_workflow_step("press", key="enter"),
            self.create_workflow_step("wait", seconds=3)
        ]
        
        return self.execute_workflow(workflow)


# Example usage
if __name__ == "__main__":
    # Create a client
    client = MCPClient(api_key="your_api_key_here")
    
    # Check if the server is running
    status = client.check_status()
    print(f"Server status: {status}")
    
    # Execute a simple workflow
    result = client.example_google_search_workflow("machine control protocol")
    print(f"Workflow result: {result}")
    
    # Take a screenshot
    screenshot = client.take_screenshot(as_pil_image=True)
    if isinstance(screenshot, Image.Image):
        screenshot.show()  # Display the screenshot
