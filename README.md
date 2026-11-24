# Python MCP AI Agent

A tool-using AI agent built with Python, Ollama, and the Model Context Protocol (MCP). The agent connects to multiple MCP servers, allowing an LLM to perform research, calculations, search local notes, and manage persistent memory.

## Features

- **Local LLM:** Uses Ollama to run a locally hosted language model.
- **MCP Integration:** Connects to multiple independent MCP servers.
- **Wikipedia Search:** Retrieves information for research and factual questions.
- **Calculator:** Performs addition, subtraction, multiplication, and division.
- **Notes Search:** Searches a local knowledge folder for relevant information.
- **Persistent Memory:** Saves, searches, updates, and deletes information across sessions.
- **Automatic Tool Execution:** The agent identifies and executes tools based on the model's decisions.
- **Multi-Step Reasoning:** Supports multiple tool calls to complete more complex requests.
- **Conversation History:** Maintains conversation context and summarizes longer conversations.
- **Working Memory:** Tracks the current task, tool results, and completion status.
- **Error Handling:** Handles unknown tools, invalid arguments, tool failures, and Ollama errors.
- **Tool-Call Limit:** Prevents the agent from entering an unlimited tool-execution loop.

## Technologies

- Python
- Ollama
- Qwen 3 4B
- Model Context Protocol (MCP)
- AnyIO

## Project Structure

```text
project/
│
├── main.py
├── wikipedia_server.py
├── calculator_server.py
├── search_notes_server.py
├── memory_server.py
├── memory.json
└── knowledge/
    └── (your knowledge files)
```

*Your actual filenames and folder structure may vary.*

## Requirements

- Python 3.10 or newer
- Ollama installed and running
- An Ollama model downloaded locally
- Required Python packages

## Installation

1. Clone or download this project.
2. Install the required Python dependencies:

```bash
pip install anyio ollama mcp
```

3. Install Ollama from [https://ollama.com](https://ollama.com).
4. Download the model:

```bash
ollama pull qwen3:4b
```

5. Make sure Ollama is running.
6. Start the agent:

```bash
python main.py
```

## Usage

Once started, the agent connects to its MCP servers and displays the available tools.

Enter a question or task in the terminal.

Example prompts:

```text
What is the capital of France?

What is 125 multiplied by 48?

Search Wikipedia for the history of Python.

Find information about a topic in my notes.

Remember that my favorite programming language is C++.

What do you remember about my programming preferences?
```

### Commands

| Command | Description |
|---|---|
| `/reset` | Clears the current conversation history |
| `exit` | Closes the agent |
| `quit` | Closes the agent |

## Architecture

The project uses a central AI agent that communicates with multiple MCP servers.

Each MCP server provides specialized functionality. The main agent discovers available tools, converts their definitions into Ollama-compatible tool descriptions, and executes tool calls requested by the model.

Tool results are added to the conversation history so the model can use them to continue reasoning and complete the user's request.

### Memory Systems

The agent uses two different memory systems:

- **Long-Term Memory:** Stores information persistently using the memory MCP server and `memory.json`.
- **Working Memory:** Tracks the active task, successful tool results, and task completion during the current session.

## Configuration

The model can be changed in `main.py`:

```python
MODEL = "qwen3:4b"
```

The maximum number of agent iterations can also be adjusted:

```python
MAX_AGENT_TURNS = 8
```

## Future Improvements

Potential future development includes:

- More specialized MCP tools.
- Improved task planning and tracking.
- Better context and memory management.
- Additional safety and validation mechanisms.
- More advanced autonomous task execution.
- Improved logging and debugging.

## Purpose

This project is a hands-on exploration of AI agents, LLM tool calling, MCP server architecture, persistent memory, and multi-step task execution using Python and locally hosted language models.
