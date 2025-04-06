import json
import flask
from flask import Flask, request, jsonify
from src.core.browser_agent import BrowserAgent
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
from src.monitoring.monitoring import MonitoringSystem, LogLevel
from src.monitoring.dashboard import Dashboard

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mcp_server')

# Initialize Flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Initialize monitoring system
monitoring = MonitoringSystem()
monitoring.start()

# Initialize dashboard
dashboard = Dashboard(monitoring)
dashboard.start()

# Configuration
API_KEY = os.getenv('MCP_API_KEY', str(uuid.uuid4()))  # Generate a random API key if not provided
RATE_LIMIT = int(os.getenv('MCP_RATE_LIMIT', 60))  # Requests per minute
BIND_HOST = os.getenv('MCP_BIND_HOST', '127.0.0.1')  # Only bind to localhost by default
PORT = int(os.getenv('MCP_PORT', 5000))
DEBUG = os.getenv('MCP_DEBUG', 'False').lower() == 'true'

# Store client request counts for rate limiting
client_requests = {}

# API key authentication decorator
def require_api_key(f):
    """Decorator to require API key for endpoints"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or provided_key != API_KEY:
            monitoring.log_activity(
                "Unauthorized API access attempt", 
                level=LogLevel.WARNING,
                details={"ip": request.remote_addr, "endpoint": request.path}
            )
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
    return decorated_function

agent = BrowserAgent()

# Define API routes
@app.route('/api/v1/status', methods=['GET'])
@require_api_key
def get_status():
    """Get the status of the MCP server"""
    start_time = time.time()
    
    try:
        # Get screen size as a basic check that pyautogui is working
        screen_width, screen_height = agent.get_screen_size()
        
        # Get mouse position
        mouse_x, mouse_y = agent.get_mouse_position()
        
        # Get system metrics
        system_metrics = monitoring.get_metrics_summary().get("system", {})
        
        response = {
            "status": "online",
            "version": "1.0.0",
            "timestamp": time.time(),
            "screen": {
                "width": screen_width,
                "height": screen_height
            },
            "mouse": {
                "x": mouse_x,
                "y": mouse_y
            },
            "system": system_metrics
        }
        
        # Log activity
        monitoring.log_activity(
            "Status check", 
            level=LogLevel.INFO,
            details={"screen_size": f"{screen_width}x{screen_height}"}
        )
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "status"}
        )
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        
        # Log error
        monitoring.log_activity(
            "Status check failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

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
    start_time = time.time()
    
    try:
        screenshot_path = agent.take_screenshot()
        
        # Convert to base64
        with open(screenshot_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Log activity
        monitoring.log_activity(
            "Screenshot taken", 
            level=LogLevel.INFO,
            details={"size": f"{agent.get_screen_size()[0]}x{agent.get_screen_size()[1]}"}
        )
        
        # Increment counter for screenshot operations
        monitoring.increment_counter("screenshot_operations")
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "screenshot"}
        )
        
        return jsonify({
            "success": True,
            "screenshot": encoded_string,
            "format": "base64",
            "path": screenshot_path
        })
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        
        # Log error
        monitoring.log_activity(
            "Screenshot failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/mouse/move', methods=['POST'])
@require_api_key
def move_mouse():
    """Move the mouse to specified coordinates"""
    start_time = time.time()
    
    try:
        data = request.json
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            monitoring.log_activity(
                "Invalid mouse move request", 
                level=LogLevel.WARNING,
                details={"data": data}
            )
            return jsonify({"success": False, "error": "Missing x or y coordinates"}), 400
            
        # Move mouse
        agent.move(x, y)
        
        # Log activity
        monitoring.log_activity(
            "Mouse moved", 
            level=LogLevel.INFO,
            details={"x": x, "y": y}
        )
        
        # Increment counter for mouse operations
        monitoring.increment_counter("mouse_operations", tags={"type": "move"})
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "mouse_move"}
        )
        
        return jsonify({"success": True, "position": {"x": x, "y": y}})
    except Exception as e:
        logger.error(f"Error moving mouse: {e}")
        
        # Log error
        monitoring.log_activity(
            "Mouse move failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/mouse/click', methods=['POST'])
@require_api_key
def click_mouse():
    """Click at the current mouse position or at specified coordinates"""
    start_time = time.time()
    
    try:
        data = request.json
        x = data.get('x')
        y = data.get('y')
        
        if x is not None and y is not None:
            agent.move(x, y)
            
        # Click mouse
        agent.click()
        
        # Log activity
        monitoring.log_activity(
            "Mouse clicked", 
            level=LogLevel.INFO,
            details={"button": "left"}
        )
        
        # Increment counter for mouse operations
        monitoring.increment_counter("mouse_operations", tags={"type": "click"})
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "mouse_click"}
        )
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error clicking mouse: {e}")
        
        # Log error
        monitoring.log_activity(
            "Mouse click failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/keyboard/type', methods=['POST'])
@require_api_key
def type_text():
    """Type text at the current cursor position"""
    start_time = time.time()
    
    try:
        data = request.json
        text = data.get('text')
        
        if not text:
            monitoring.log_activity(
                "Invalid keyboard type request", 
                level=LogLevel.WARNING,
                details={"data": data}
            )
            return jsonify({"success": False, "error": "Missing text parameter"}), 400
            
        # Type text
        agent.type_text(text)
        
        # Log activity (don't log the actual text for privacy)
        monitoring.log_activity(
            "Text typed", 
            level=LogLevel.INFO,
            details={"length": len(text)}
        )
        
        # Increment counter for keyboard operations
        monitoring.increment_counter("keyboard_operations", tags={"type": "type"})
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "keyboard_type"}
        )
        
        return jsonify({"success": True, "text": text})
    except Exception as e:
        logger.error(f"Error typing text: {e}")
        
        # Log error
        monitoring.log_activity(
            "Keyboard type failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/keyboard/press', methods=['POST'])
@require_api_key
def press_key():
    """Press a keyboard key"""
    start_time = time.time()
    
    try:
        data = request.json
        key = data.get('key')
        
        if not key:
            monitoring.log_activity(
                "Invalid keyboard press request", 
                level=LogLevel.WARNING,
                details={"data": data}
            )
            return jsonify({"success": False, "error": "Missing key parameter"}), 400
            
        # Press key
        agent.press(key)
        
        # Log activity
        monitoring.log_activity(
            "Key pressed", 
            level=LogLevel.INFO,
            details={"key": key}
        )
        
        # Increment counter for keyboard operations
        monitoring.increment_counter("keyboard_operations", tags={"type": "press"})
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "keyboard_press"}
        )
        
        return jsonify({"success": True, "key": key})
    except Exception as e:
        logger.error(f"Error pressing key: {e}")
        
        # Log error
        monitoring.log_activity(
            "Keyboard press failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/browser/open', methods=['POST'])
@require_api_key
def open_browser():
    """Open a web browser"""
    start_time = time.time()
    
    try:
        data = request.json
        browser = data.get('browser', 'chrome')
        
        success = agent.open_browser(browser)
        
        # Log activity
        monitoring.log_activity(
            "Browser opened", 
            level=LogLevel.INFO,
            details={"browser": browser}
        )
        
        # Increment counter for browser operations
        monitoring.increment_counter("browser_operations", tags={"type": "open"})
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "browser_open"}
        )
        
        return jsonify({"success": success, "browser": browser})
    except Exception as e:
        logger.error(f"Error opening browser: {e}")
        
        # Log error
        monitoring.log_activity(
            "Browser open failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/browser/navigate', methods=['POST'])
@require_api_key
def navigate_browser():
    """Navigate to a URL"""
    start_time = time.time()
    
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            monitoring.log_activity(
                "Invalid browser navigate request", 
                level=LogLevel.WARNING,
                details={"data": data}
            )
            return jsonify({"success": False, "error": "Missing url parameter"}), 400
            
        success = agent.navigate_to_url(url)
        
        # Log activity
        monitoring.log_activity(
            "Browser navigated", 
            level=LogLevel.INFO,
            details={"url": url}
        )
        
        # Increment counter for browser operations
        monitoring.increment_counter("browser_operations", tags={"type": "navigate"})
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "browser_navigate"}
        )
        
        return jsonify({"success": success, "url": url})
    except Exception as e:
        logger.error(f"Error navigating browser: {e}")
        
        # Log error
        monitoring.log_activity(
            "Browser navigate failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/vision/find', methods=['POST'])
@require_api_key
def find_on_screen():
    """Find an image on screen"""
    start_time = time.time()
    
    try:
        data = request.json
        # Check if image is provided as base64
        image_base64 = data.get('image_base64')
        image_path = data.get('image_path')
        confidence = data.get('confidence', 0.8)
        
        if not image_base64 and not image_path:
            monitoring.log_activity(
                "Invalid vision find request", 
                level=LogLevel.WARNING,
                details={"data": data}
            )
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
            # Log activity
            monitoring.log_activity(
                "Image found on screen", 
                level=LogLevel.INFO,
                details={"image_path": image_path, "confidence": confidence}
            )
            
            # Increment counter for vision operations
            monitoring.increment_counter("vision_operations", tags={"type": "find"})
            
            # Record API call timing
            monitoring.record_timer(
                "api_call_duration", 
                time.time() - start_time,
                tags={"endpoint": "vision_find"}
            )
            
            return jsonify({
                "success": True, 
                "found": True,
                "position": {"x": coords[0], "y": coords[1]}
            })
        else:
            # Log activity
            monitoring.log_activity(
                "Image not found on screen", 
                level=LogLevel.INFO,
                details={"image_path": image_path, "confidence": confidence}
            )
            
            # Increment counter for vision operations
            monitoring.increment_counter("vision_operations", tags={"type": "find"})
            
            # Record API call timing
            monitoring.record_timer(
                "api_call_duration", 
                time.time() - start_time,
                tags={"endpoint": "vision_find"}
            )
            
            return jsonify({"success": True, "found": False})
            
    except Exception as e:
        logger.error(f"Error finding image on screen: {e}")
        
        # Log error
        monitoring.log_activity(
            "Vision find failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/vision/click_image', methods=['POST'])
@require_api_key
def click_on_image():
    """Find and click on an image"""
    start_time = time.time()
    
    try:
        data = request.json
        image_path = data.get('image_path')
        confidence = data.get('confidence', 0.8)
        
        if not image_path:
            monitoring.log_activity(
                "Invalid vision click request", 
                level=LogLevel.WARNING,
                details={"data": data}
            )
            return jsonify({"success": False, "error": "Missing image_path parameter"}), 400
            
        success = agent.click_on_image(image_path, confidence)
        
        # Log activity
        monitoring.log_activity(
            "Image clicked", 
            level=LogLevel.INFO,
            details={"image_path": image_path, "confidence": confidence}
        )
        
        # Increment counter for vision operations
        monitoring.increment_counter("vision_operations", tags={"type": "click"})
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "vision_click"}
        )
        
        return jsonify({"success": True, "clicked": success})
    except Exception as e:
        logger.error(f"Error clicking image: {e}")
        
        # Log error
        monitoring.log_activity(
            "Vision click failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/workflow/execute', methods=['POST'])
@require_api_key
def execute_workflow():
    """Execute a predefined workflow"""
    start_time = time.time()
    
    try:
        data = request.json
        workflow = data.get('workflow')
        
        if not workflow or not isinstance(workflow, list):
            monitoring.log_activity(
                "Invalid workflow request", 
                level=LogLevel.WARNING,
                details={"data": data}
            )
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
        
        # Log activity
        monitoring.log_activity(
            "Workflow executed", 
            level=LogLevel.INFO,
            details={"workflow": workflow}
        )
        
        # Increment counter for workflow operations
        monitoring.increment_counter("workflow_operations")
        
        # Record API call timing
        monitoring.record_timer(
            "api_call_duration", 
            time.time() - start_time,
            tags={"endpoint": "workflow_execute"}
        )
        
        return jsonify({"success": True, "results": results})
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        
        # Log error
        monitoring.log_activity(
            "Workflow execution failed", 
            level=LogLevel.ERROR,
            details={"error": str(e)}
        )
        
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/metrics', methods=['GET'])
@require_api_key
def get_metrics():
    """Get monitoring metrics"""
    try:
        metrics = monitoring.get_metrics_summary()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/logs', methods=['GET'])
@require_api_key
def get_logs():
    """Get activity logs"""
    try:
        count = request.args.get('count', default=100, type=int)
        logs = monitoring.get_recent_activity(count)
        return jsonify(logs)
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    try:
        # Log startup
        logger.info(f"Starting MCP server on {BIND_HOST}:{PORT}")
        monitoring.log_activity(
            "MCP server started", 
            level=LogLevel.INFO,
            details={"host": BIND_HOST, "port": PORT}
        )
        
        # Run the Flask app
        app.run(host=BIND_HOST, port=PORT, debug=DEBUG)
    except KeyboardInterrupt:
        # Log shutdown
        logger.info("MCP server shutting down")
        monitoring.log_activity(
            "MCP server stopped", 
            level=LogLevel.INFO
        )
        
        # Stop monitoring and dashboard
        monitoring.stop()
        dashboard.stop()
