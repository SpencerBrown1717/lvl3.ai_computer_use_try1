from agent import SimpleComputerAgent

def main():
    agent = SimpleComputerAgent()
    
    print("Simple Computer Agent started.")
    print("Enter commands like: move 100 200, click, screenshot, type hello")
    print("Type 'exit' to quit")
    
    while True:
        user_input = input("> ")
        if user_input.lower() == "exit":
            break
            
        result = agent.run_command(user_input)
        print(result)

if __name__ == "__main__":
    main()
