"""
Simple MCP Server for testing
This is a minimal implementation of the MCP server to verify functionality
"""

from flask import Flask, jsonify, request
import time
import os
import uuid
import functools
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('MCP_API_KEY', str(uuid.uuid4()))  # Generate a random API key if not provided
RATE_LIMIT = int(os.getenv('MCP_RATE_LIMIT', 60))  # Requests per minute
BIND_HOST = os.getenv('MCP_BIND_HOST', '127.0.0.1')  # Only bind to localhost by default
PORT = int(os.getenv('MCP_PORT', 5001))
DEBUG = os.getenv('MCP_DEBUG', 'False').lower() == 'true'

app = Flask(__name__)

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

@app.route('/api/v1/mouse/move', methods=['POST'])
@require_api_key
def move_mouse():
    """Mock mouse movement endpoint"""
    try:
        data = request.json
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            return jsonify({"success": False, "error": "Missing x or y coordinates"}), 400
            
        return jsonify({"success": True, "message": "Mouse moved (mock)", "position": {"x": x, "y": y}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/keyboard/press', methods=['POST'])
@require_api_key
def press_key():
    """Mock key press endpoint"""
    try:
        data = request.json
        key = data.get('key')
        
        if not key:
            return jsonify({"success": False, "error": "Missing key parameter"}), 400
            
        return jsonify({"success": True, "message": "Key pressed (mock)", "key": key})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print(f"Starting Simple MCP Server on port {PORT}...")
    print(f"API Key: {API_KEY}")
    print(f"Binding to: {BIND_HOST}")
    try:
        app.run(host=BIND_HOST, port=PORT, debug=DEBUG)
    except Exception as e:
        print(f"Error starting server: {e}")
