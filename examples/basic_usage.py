from agent import SimpleComputerAgent

# Example automation script
agent = SimpleComputerAgent()

# Open a text editor
agent.move(500, 300)
agent.click()
agent.type_text("Hello, this is an automated test")
agent.take_screenshot()
