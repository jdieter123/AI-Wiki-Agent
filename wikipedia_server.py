
import wikipedia
from mcp.server import MCPServer

# Create the MCP server
mcp = MCPServer("WikipediaServer", instructions="A server for researching Wikipedia articles.")

# -------------------------
# TOOL
# -------------------------

# wikipedia
@mcp.tool()
def search_wikipedia(query: str) -> dict:
    """Search Wikipedia and return the title, summary, and URL.""" #Seen by AI

    try:
        results = wikipedia.search(query)

        if not results:
            return {"error": "No results found."}

        page = wikipedia.page(results[0])

        return {
            "title": page.title,
            "summary": page.summary,
            "url": page.url
        }

    except wikipedia.DisambiguationError as e:
        return {
            "error": f"Ambiguous topic: {e.options[:5]}"
        }

    except wikipedia.PageError:
        return {
            "error": "Wikipedia page could not be loaded."
        }

# -------------------------
# PROMPT
# -------------------------

@mcp.prompt()
def prioritize_sections(topic: str) -> str:
    """Generate instructions for identifying important article sections."""

    return f"""
    You are a research assistant.

    Analyze the Wikipedia article about {topic}.

    Identify the five most important sections.

    For each section:
    1. Explain what it covers.
    2. Explain why it is important.
    3. Explain what a beginner should learn from it.

    Prioritize foundational knowledge.
    """


# -------------------------
# RESOURCE
# -------------------------

@mcp.resource("info://server")
def server_info() -> str:
    """Provide information about this Wikipedia MCP server."""

    return """
    Wikipedia MCP Server

    Available capabilities:

    - Search Wikipedia articles
    - Generate research prompts
    - Provide server information
    """


# -------------------------
# START SERVER
# -------------------------

if __name__ == "__main__":
    mcp.run()
