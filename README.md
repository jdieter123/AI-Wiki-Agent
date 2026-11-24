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
