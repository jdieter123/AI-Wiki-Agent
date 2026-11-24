
import anyio
import sys
import json

from pathlib import Path
from mcp import Client, StdioServerParameters
from mcp.types import TextContent

from ollama import AsyncClient


# -------------------------
# CONFIGURATION
# -------------------------

MODEL = "qwen3:4b"

WIKI_SERVER_PATH = Path(__file__).with_name("wikipedia_server.py")
CALC_SERVER_PATH = Path(__file__).with_name("calculator_server.py")
SEARCH_NOTES_SERVER_PATH = Path(__file__).with_name("search_notes_server.py")
MEMORY_SERVER_PATH = Path(__file__).with_name("memory_server.py")

MAX_AGENT_TURNS = 8

# Temp info for the current task
working_memory = {}

# creates a new working memory dictionary
def start_task(goal):
    global working_memory

    working_memory = {
        "goal": goal,
        "result": [],
        "completed": False
    }

# clears temp info
def finish_task():
    global working_memory

    working_memory = {}

def add_task_result(tool_name, result):
    working_memory["result"].append({
        "tool": tool_name,
        "result": result
    })

# Convert mcp tools to ollama tools
def convert_mcp_tools_to_ollama(mcp_tools):
    ollama_tools = []

    for tool in mcp_tools:

        ollama_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema
            }
        }

        ollama_tools.append(ollama_tool)

    return ollama_tools


# summarize history context so history doesnt get too big
async def summarize_history(ollama, history):
    result = await ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarize this conversation."
                    "Preserve important facts, user preferences,"
                    "project details, and unfinished tasks."
                    "Ignore unnecessary details."
                )
            },
            {
                "role": "user",
                "content": json.dumps(history, default=str)
            }
        ], think=False
    )

    return result.message.content

async def manage_history(ollama, history):
    if len(history) <= 30:
        return history

    print("\nConversation is getting long. Summarizing...")

    # summarize everything after ther system prompt
    summary = await summarize_history(ollama, history[1:])

    # keep the system prompt
    system_message = history[0]

    history = [
        system_message,
        {
            "role": "system",
            "content": "Previous conversation summary: " + summary
        }
    ]

    print("Conversation Summarized!")

    return history

# -------------------------
# CREATE AGENT
# -------------------------

async def main():

    # Connect to our local Ollama server
    ollama = AsyncClient(
        host="http://localhost:11434"
    )

    # Configure how to launch our MCP server
    wiki_server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(WIKI_SERVER_PATH)]
    )

    calc_server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(CALC_SERVER_PATH)]
    )

    search_notes_server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SEARCH_NOTES_SERVER_PATH)]
    )

    memory_server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(MEMORY_SERVER_PATH)]
    )

    # Connect to All MCP server
    async with (
        Client(wiki_server_params) as wiki_client,
        Client(calc_server_params) as calculator_client,
        Client(search_notes_server_params) as search_notes_client,
        Client(memory_server_params) as memory_server_client
        ):  # THIS becomes our new client, instead of wikipedia_client.py

        print("Connected to All MCP Server!")

        # keep track of who owns what tool
        tool_clients = {}

        # Convert MCP tools into Ollama tool definitions
        ollama_tools = []

        # Our MCP server connections
        servers = [
            wiki_client,
            calculator_client,
            search_notes_client,
            memory_server_client
        ]

        for server in servers:

            # get tools
            mcp_tools = await server.list_tools()

            # remember which server owns which tools
            for tool in mcp_tools.tools:
                tool_clients[tool.name] = server

            # convert mcp tools into ollama usable tools
            ollama_tools.extend(convert_mcp_tools_to_ollama(mcp_tools.tools))

        print("\nAvailable tools:")
        for tool in ollama_tools:
            print("-", tool["function"]["name"])

        print("\nAI Agent is ready!")

        # Store conversation history
        history = [
            {
                "role": "system",
                "content": (
                    "You are a helpful research assistant. "
                    "You have access to a Wikipedia search tool. "
                    "You also have access to a calculator tool that supports addition, subtraction, multiplication, and division."
                    "You also have access to a knowledge folder containing useful information."
                    "Wikipedia can help answer, use the search "
                    "tool instead of guessing. After receiving "
                    "the search results, explain them clearly."
                    "Memory management rules:"
                        "- Use save_memory when storing a new fact."
                        "- Use update_memory when the user explicitly changes"
                        "or corrects an existing fact."
                        "- Use delete_memory only when the user explicitly asks"
                        "to delete a memory."
                        "- Do not create a new memory when updating an existing one."
                        "- Never claim a memory was updated unless the tool"
                        "confirms success."
                    "Memory retrieval rules:"
                        "- Use semantic_search to find relevant memories."
                        "- Use category filtering when the user's question clearly relates to a specific category."
                        "- Use an empty category when searching across all memories."
                        "- Do not assume a memory exists if the search returns no results."
                        "- Use the retrieved memory values as context when answering."
                    "Memory source rules:"
                        "- Use source='explicit' when the user directly states a fact or preference."
                        "- Use source='inferred' when information is an AI-generated assumption."
                        "- Use source='imported' when information comes from an external file or source."
                        "- Never present inferred information as something the user explicitly confirmed."
                        "- Prefer explicit memories when answering questions about the user's preferences."
                    "MEMORY IMPORTANCE RULES:"
                        "When saving information to long-term memory, choose an importance"
                        "score between 1 and 5."

                        "Use these guidelines:"

                        "1 = Temporary information that will soon become irrelevant."
                        "2 = Low-value information that probably won't matter often."
                        "3 = Generally useful information."
                        "4 = Important ongoing projects, goals, or preferences."
                        "5 = Very important lasting preferences or explicit instructions."

                        "Before calling save_memory:"
                        "- Evaluate how useful the information will be in future conversations."
                        "- Choose an appropriate importance score."
                        "- Pass that score using the importance parameter."
                        "- Do not automatically assign importance 5 to everything."
                        "- Never invent personal information."
                        "- If the user explicitly requests that something be remembered,"
                        "prioritize preserving that information."
                    """MEMORY CATEGORIZATION RULES:
                        When saving information to long-term memory, select the most
                        appropriate category.

                        Available categories:

                        preference
                        project
                        instruction
                        goal
                        skill
                        general

                        Rules:
                        - Use preference for likes and dislikes.
                        - Use project for ongoing projects.
                        - Use instruction for explicit behavioral instructions.
                        - Use goal for long-term objectives.
                        - Use skill for abilities and technical knowledge.
                        - Use general when no other category fits.

                        Always pass the selected category to save_memory().
                        Do not automatically use general.
                        Choose only one category."""
                )
            }
        ]

        # User interaction
        while True:

            question = input("\nYou: ")

            if question.lower() in ["quit", "exit"]:
                break

            if question.lower() == "/reset":
                history = history[:1]
                print("Conversation history cleared!")
                continue

            # start task
            start_task(question)

            # Add user question to history
            history.append({
                "role": "user",
                "content": question
            })

            # MANAGE HISTORY SIZE
            history = await manage_history(ollama, history)

            # Agent loop
            for turn in range(MAX_AGENT_TURNS):

                print("\nThinking...")

                try:

                    # Ask Ollama what to do
                    response = await ollama.chat(
                        model=MODEL,
                        messages=history,
                        tools=ollama_tools,
                        think=True
                    )

                except Exception as e:

                    print("\nOllama error:", e)

                    if history and history[-1].get("role") == "user":
                        history.pop()

                    finish_task()
                    break

                # Get the model's response
                model_message = response.message

                # Save model response
                history.append(model_message)

                # Check for tool requests
                function_calls = model_message.tool_calls or []

                # If no tools were requested, we're finished
                if not function_calls:

                    print("\nAI:", model_message.content)

                    working_memory["completed"] = True
                    working_memory["final_answer"] = model_message.content

                    break

                # Execute requested MCP tools
                for function_call in function_calls:

                    tool_name = function_call.function.name

                    try:
                        arguments = dict(function_call.function.arguments)
                    except (TypeError, ValueError):
                        arguments = None

                    if arguments is None:
                        tool_response = {
                            "result": None,
                            "is_error": True,
                            "error": "Invalid tool arguments"
                        }

                    print(f"\nAgent is using tool: {tool_name}")
                    print("Arguments:", arguments)

                    if tool_name not in tool_clients:
                        tool_response = {
                            "result": None,
                            "is_error": True,
                            "error": f"Unknown tool: {tool_name}"
                        }
                    else:

                        try:

                            # Execute the tool through MCP
                            result = await tool_clients[tool_name].call_tool(
                                tool_name,
                                arguments
                            )

                            # Extract returned information
                            if result.structured_content is not None:

                                tool_data = result.structured_content

                            else:

                                tool_data = []

                                for block in result.content:
                                    if isinstance(block, TextContent):
                                        tool_data.append(block.text)

                            tool_response = {
                                "result": tool_data,
                                "is_error": result.is_error
                            }

                        except Exception as e:

                            tool_response = {
                                "result": None,
                                "is_error": True,
                                "error": str(e)
                            }

                    # Send the tool result back to Ollama
                    history.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": json.dumps(
                            tool_response,
                            ensure_ascii=False,
                            default=str
                        )
                    })

                    if not tool_response["is_error"]:
                        add_task_result(tool_name, tool_response["result"])

            else:
                print("\nAgent reached its maximum tool-call turns.")


if __name__ == "__main__":
    anyio.run(main)
