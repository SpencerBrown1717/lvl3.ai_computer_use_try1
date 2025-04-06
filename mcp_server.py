import json
import flask
from flask import Flask, request, jsonify
from browser_agent import BrowserAgent
import base64
import io
from PIL import Image
import os
import time
import uuid
import hashlib
import functools
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('MCP_API_KEY', str(uuid.uuid4()))  # Generate a random API key if not provided
RATE_LIMIT = int(os.getenv('MCP_RATE_LIMIT', 60))  # Requests per minute
BIND_HOST = os.getenv('MCP_BIND_HOST', '127.0.0.1')  # Only bind to localhost by default
PORT = int(os.getenv('MCP_PORT', 5000))
DEBUG = os.getenv('MCP_DEBUG', 'False').lower() == 'true'

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
agent = BrowserAgent()

# Store client request counts for rate limiting
client_requests = {}

def require_api_key(f):
    """Decorator to require API key for endpoints"""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != API_KEY:
            return jsonify({"success": False, "error": "Invalid or missing API key"}), 401
        
        # Rate limiting
        client_ip = request.remote_addr
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Clean up old requests
        for ip in list(client_requests.keys()):
            client_requests[ip] = [t for t in client_requests[ip] if t > minute_ago]
            if not client_requests[ip]:
                del client_requests[ip]
        
        # Check rate limit
        if client_ip not in client_requests:
            client_requests[client_ip] = []
        
        if len(client_requests[client_ip]) >= RATE_LIMIT:
            return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
        
        client_requests[client_ip].append(current_time)
        
        return f(*args, **kwargs)
    return decorated

# Define API routes
@app.route('/api/v1/status', methods=['GET'])
def get_status():
    """Get the status of the MCP server"""
    return jsonify({
        "status": "online",
        "version": "1.0.0",
        "timestamp": time.time()
    })

@app.route('/api/v1/setup', methods=['GET'])
def get_setup_info():
    """Get setup information for new clients"""
    if API_KEY == str(uuid.uuid4()):
        # This is a generated API key, so it's safe to show
        return jsonify({
            "message": "Please use this API key for all requests",
            "api_key": API_KEY,
            "rate_limit": RATE_LIMIT,
            "note": "This key was auto-generated and will change on server restart. Set MCP_API_KEY in .env for a persistent key."
        })
    else:
        return jsonify({
            "message": "API key is configured. Please use the correct API key in the X-API-Key header.",
            "rate_limit": RATE_LIMIT
        })

@app.route('/api/v1/screenshot', methods=['GET'])
@require_api_key
def take_screenshot():
    """Take a screenshot and return it as base64 encoded image"""
    try:
        screenshot_path = agent.take_screenshot()
        
        # Convert to base64
        with open(screenshot_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        return jsonify({
            "success": True,
            "screenshot": encoded_string,
            "format": "base64",
            "path": screenshot_path
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/v1/mouse/move', methods=['POST'])
@require_api_key
def move_mouse():
    """Move the mouse to specified coordinates"""
    data = request.json
    try:
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            return jsonify({"success": False, "error": "Missing x or y coordinates"}), 400
            
        agent.move(x, y)
        return jsonify({"success": True, "position": {"x": x, "y": y}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/mouse/click', methods=['POST'])
@require_api_key
def click_mouse():
    """Click at the current mouse position or at specified coordinates"""
    data = request.json
    try:
        x = data.get('x')
        y = data.get('y')
        
        if x is not None and y is not None:
            agent.move(x, y)
            
        agent.click()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/keyboard/type', methods=['POST'])
@require_api_key
def type_text():
    """Type text at the current cursor position"""
    data = request.json
    try:
        text = data.get('text')
        
        if not text:
            return jsonify({"success": False, "error": "Missing text parameter"}), 400
            
        agent.type_text(text)
        return jsonify({"success": True, "text": text})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/keyboard/press', methods=['POST'])
@require_api_key
def press_key():
    """Press a keyboard key"""
    data = request.json
    try:
        key = data.get('key')
        
        if not key:
            return jsonify({"success": False, "error": "Missing key parameter"}), 400
            
        agent.press(key)
        return jsonify({"success": True, "key": key})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/browser/open', methods=['POST'])
@require_api_key
def open_browser():
    """Open a web browser"""
    data = request.json
    try:
        browser = data.get('browser', 'chrome')
        
        success = agent.open_browser(browser)
        return jsonify({"success": success, "browser": browser})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/browser/navigate', methods=['POST'])
@require_api_key
def navigate_browser():
    """Navigate to a URL"""
    data = request.json
    try:
        url = data.get('url')
        
        if not url:
            return jsonify({"success": False, "error": "Missing url parameter"}), 400
            
        success = agent.navigate_to_url(url)
        return jsonify({"success": success, "url": url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/vision/find', methods=['POST'])
@require_api_key
def find_on_screen():
    """Find an image on screen"""
    data = request.json
    try:
        # Check if image is provided as base64
        image_base64 = data.get('image_base64')
        image_path = data.get('image_path')
        confidence = data.get('confidence', 0.8)
        
        if not image_base64 and not image_path:
            return jsonify({"success": False, "error": "Missing image data"}), 400
            
        # If base64 image is provided, save it temporarily
        if image_base64:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            
            # Create temp directory if it doesn't exist
            os.makedirs("temp", exist_ok=True)
            
            # Save with timestamp to avoid conflicts
            timestamp = int(time.time())
            temp_path = f"temp/temp_image_{timestamp}.png"
            image.save(temp_path)
            image_path = temp_path
        
        # Find the image on screen
        coords = agent.find_on_screen(image_path, confidence)
        
        if coords:
            return jsonify({
                "success": True, 
                "found": True,
                "position": {"x": coords[0], "y": coords[1]}
            })
        else:
            return jsonify({"success": True, "found": False})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/vision/click_image', methods=['POST'])
@require_api_key
def click_on_image():
    """Find and click on an image"""
    data = request.json
    try:
        image_path = data.get('image_path')
        confidence = data.get('confidence', 0.8)
        
        if not image_path:
            return jsonify({"success": False, "error": "Missing image_path parameter"}), 400
            
        success = agent.click_on_image(image_path, confidence)
        return jsonify({"success": True, "clicked": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/workflow/execute', methods=['POST'])
@require_api_key
def execute_workflow():
    """Execute a predefined workflow"""
    data = request.json
    try:
        workflow = data.get('workflow')
        
        if not workflow or not isinstance(workflow, list):
            return jsonify({"success": False, "error": "Invalid workflow format"}), 400
            
        results = []
        
        for step in workflow:
            action = step.get('action')
            params = step.get('params', {})
            
            if action == 'move':
                agent.move(params.get('x'), params.get('y'))
                results.append({"action": "move", "success": True})
            elif action == 'click':
                agent.click()
                results.append({"action": "click", "success": True})
            elif action == 'type':
                agent.type_text(params.get('text', ''))
                results.append({"action": "type", "success": True})
            elif action == 'press':
                agent.press(params.get('key', ''))
                results.append({"action": "press", "success": True})
            elif action == 'open_browser':
                success = agent.open_browser(params.get('browser', 'chrome'))
                results.append({"action": "open_browser", "success": success})
            elif action == 'navigate':
                success = agent.navigate_to_url(params.get('url', ''))
                results.append({"action": "navigate", "success": success})
            elif action == 'click_image':
                success = agent.click_on_image(params.get('image_path', ''), params.get('confidence', 0.8))
                results.append({"action": "click_image", "success": success})
            elif action == 'wait':
                time.sleep(params.get('seconds', 1))
                results.append({"action": "wait", "success": True})
            else:
                results.append({"action": action, "success": False, "error": "Unknown action"})
        
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    try:
        # Try port 5000 first
        port = 5000
        try:
            app.run(host=BIND_HOST, port=port, debug=DEBUG)
        except OSError:
            # If port 5000 is in use, try port 5001
            port = 5001
            print(f"Port 5000 is in use, trying port {port}...")
            app.run(host=BIND_HOST, port=port, debug=DEBUG)
    except Exception as e:
        print(f"Error starting MCP server: {e}")
        print("Please make sure you have the necessary permissions and dependencies installed.")
