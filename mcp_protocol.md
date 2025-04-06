# Machine Control Protocol (MCP) Specification

## Overview

The Machine Control Protocol (MCP) is a standardized interface that allows AI agents to control computer systems through a REST API. It provides a bridge between AI decision-making systems and physical computer interaction, enabling agentic workflows to execute real-world tasks.

## Core Principles

1. **Simplicity**: The protocol uses standard HTTP methods and JSON for maximum compatibility
2. **Statelessness**: Each request contains all information needed to complete the operation
3. **Composability**: Complex operations can be built from simple primitives
4. **Visual Grounding**: The protocol provides mechanisms for visual perception and interaction
5. **Security**: The protocol implements authentication and rate limiting to protect the system

## API Endpoints

The MCP API is organized into logical groups:

### System

- `GET /api/v1/status` - Check if the MCP server is running
- `GET /api/v1/setup` - Get setup information for new clients, including API key if available

### Perception

- `GET /api/v1/screenshot` - Take a screenshot and return it as base64 encoded image

### Mouse Control

- `POST /api/v1/mouse/move` - Move the mouse to specified coordinates
- `POST /api/v1/mouse/click` - Click at the current mouse position or at specified coordinates

### Keyboard Control

- `POST /api/v1/keyboard/type` - Type text at the current cursor position
- `POST /api/v1/keyboard/press` - Press a keyboard key

### Browser Control

- `POST /api/v1/browser/open` - Open a web browser
- `POST /api/v1/browser/navigate` - Navigate to a URL

### Vision

- `POST /api/v1/vision/find` - Find an image on screen
- `POST /api/v1/vision/click_image` - Find and click on an image

### Workflow

- `POST /api/v1/workflow/execute` - Execute a predefined workflow

## Data Formats

### Screenshot Response

```json
{
  "success": true,
  "screenshot": "base64_encoded_image_data",
  "format": "base64",
  "path": "/path/to/saved/screenshot.png"
}
```

### Workflow Format

```json
{
  "workflow": [
    {
      "action": "open_browser",
      "params": {
        "browser": "chrome"
      }
    },
    {
      "action": "navigate",
      "params": {
        "url": "https://www.example.com"
      }
    },
    {
      "action": "type",
      "params": {
        "text": "search query"
      }
    }
  ]
}
```

## Security Considerations

1. **Authentication**: The MCP server implements API key authentication. All requests (except `/status` and `/setup`) require a valid API key in the `X-API-Key` header.

2. **Rate Limiting**: To prevent abuse, the server implements rate limiting based on client IP address. The default limit is 60 requests per minute.

3. **Local Binding**: By default, the server only binds to localhost (127.0.0.1), making it inaccessible from other machines. This can be changed in the configuration if needed.

4. **Environment Variables**: Security settings can be configured via environment variables:
   - `MCP_API_KEY`: API key for authentication
   - `MCP_RATE_LIMIT`: Number of requests allowed per minute
   - `MCP_BIND_HOST`: Host to bind the server to
   - `MCP_PORT`: Port to run the server on
   - `MCP_DEBUG`: Whether to run in debug mode

5. **Secure Deployment**: For production use, consider:
   - Using HTTPS with a valid certificate
   - Implementing proper user authentication
   - Running behind a reverse proxy
   - Setting up network-level security

## Integration Examples

### Python Example with Authentication

```python
from mcp_client import MCPClient

# Create a client with API key
client = MCPClient("http://localhost:5000", api_key="your_api_key_here")

# Check server status
status = client.check_status()
print(f"Server status: {status}")

# Take a screenshot
screenshot = client.take_screenshot()

# Execute a Google search
client.open_browser("chrome")
client.navigate_to_url("https://www.google.com")
client.type_text("machine control protocol")
client.press_key("enter")
```

### JavaScript Example with Authentication

```javascript
async function searchGoogle(query) {
  const baseUrl = "http://localhost:5000/api/v1";
  const apiKey = "your_api_key_here";
  const headers = {
    "Content-Type": "application/json",
    "X-API-Key": apiKey
  };
  
  // Open browser
  await fetch(`${baseUrl}/browser/open`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ browser: "chrome" })
  });
  
  // Navigate to Google
  await fetch(`${baseUrl}/browser/navigate`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ url: "https://www.google.com" })
  });
  
  // Type search query
  await fetch(`${baseUrl}/keyboard/type`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ text: query })
  });
  
  // Press Enter
  await fetch(`${baseUrl}/keyboard/press`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ key: "enter" })
  });
}
```

## Future Extensions

1. **Event Streams**: Subscribe to events like screen changes
2. **OCR Integration**: Extract text from screen regions
3. **Semantic Understanding**: Higher-level understanding of UI elements
4. **Multi-modal Interaction**: Support for audio and other interaction modes
