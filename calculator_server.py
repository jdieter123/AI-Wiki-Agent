from mcp.server import MCPServer

mcp = MCPServer("CalculatorServer", instructions="A server for mathmatical calculations")

# calculator
@mcp.tool()
def calculator(a: float, b: float, operator: str) -> float:
    """Perform math calculations.
        Supported operation: add, sub, multiply, divide""" #Seen by AI, helps make decision on what to do
    if operator == "add":
        return a+b
    elif operator == "sub":
        return a-b
    elif operator == "multiply":
        return a*b
    elif operator == "divide":
        if b == 0:
            raise ValueError("cannot divide by 0")
        return a/b
    else:
        raise ValueError("Unsupported operation.")

if __name__ == "__main__":
    mcp.run()