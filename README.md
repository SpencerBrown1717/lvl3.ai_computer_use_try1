# Simple Computer Control Agent MVP

A minimal implementation of an agent that can control a computer through basic operations like moving the cursor, clicking, and taking screenshots.

## Core Features

The simplest implementation focuses on:
1. Mouse movement and clicking
2. Taking screenshots
3. Basic command execution
4. Text typing

## Installation

1. Clone this repository
   ```
   git clone https://github.com/SpencerBrown1717/lvl3.ai_computer_use_try1.git
   cd lvl3.ai_computer_use_try1
   ```
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. (Optional) Create and configure your environment variables:
   ```
   cp .env.example .env
   # Edit .env file with your preferred settings
   ```

## How to Use

### Command Line Interface

Run the interactive command-line interface:

```
python main.py
```

Enter commands like:
- `move 500 300` (moves cursor to x=500, y=300)
- `click` (performs a click)
- `doubleclick` (performs a double-click)
- `screenshot` (captures the screen)
- `type Hello world` (types the text)
- `exit` (quits the program)

### Programmatic Usage

You can also use the agent programmatically in your own scripts:

```python
from agent import SimpleComputerAgent

agent = SimpleComputerAgent()

# Move mouse to coordinates
agent.move(500, 300)

# Click
agent.click()

# Type text
agent.type_text("Hello, world!")

# Take a screenshot
screenshot_path = agent.take_screenshot()
```

See the `examples/basic_usage.py` file for a simple example.

## Project Structure

```
simple_agent/
├── agent.py           # Main agent class implementation
├── requirements.txt   # Dependencies (pyautogui, etc.)
├── README.md          # Usage instructions
├── main.py            # Command-line interface
├── screenshots/       # Directory for storing screenshots (created at runtime)
└── examples/
    └── basic_usage.py # Example automation script
```

## Extension Ideas

This MVP could be extended with:
- Image recognition to find and click on UI elements
- Simple decision-making based on screenshots
- Reading text from screen (OCR)
- Recording sequences of actions for replay
- Custom command scripting

## Dependencies

- PyAutoGUI: For controlling mouse and keyboard
- Pillow: For handling screenshots

## Limitations

- The agent has no awareness of what's on screen - it blindly follows commands
- No error recovery if actions fail
- Limited to basic mouse/keyboard operations
- No complex decision making
