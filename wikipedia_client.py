
import anyio
import sys

from pathlib import Path
from mcp import Client, StdioServerParameters
from mcp.types import TextContent, TextResourceContents


# Find the server in the same directory as this client
SERVER_PATH = Path(__file__).with_name("wikipedia_server.py")


async def main():

    # Tell the client how to launch the server
    server_params = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])

    # Connect to the server
    async with Client(server_params) as client:

        print("Connected to Wikipedia MCP Server!")

        # Display server information
        print("\nServer:", client.server_info)
        print("Protocol:", client.protocol_version)

        # Discover tools
        tools = await client.list_tools()

        print("\nAvailable Tools:")
        for tool in tools.tools:
            print("-", tool.name, ":", tool.description)


        # Discover prompts
        prompts = await client.list_prompts()

        print("\nAvailable Prompts:")
        for prompt in prompts.prompts:
            print("-", prompt.name, ":", prompt.description)


        # Discover resources
        resources = await client.list_resources()

        print("\nAvailable Resources:")
        for resource in resources.resources:
            print("-", resource.uri)


        # User interaction
        while True:

            print("\n1. Search Wikipedia")
            print("2. Generate research prompt")
            print("3. Read server resource")
            print("4. Quit")

            choice = input("\nChoose an option: ")

            if choice == "1": # Search

                query = input("Enter a topic: ")

                result = await client.call_tool("search_wikipedia", {"query": query})

                print("\nWikipedia Result:")

                if result.is_error:
                    print("The tool reported an error.")

                for content in result.content:
                    if isinstance(content, TextContent):
                        print(content.text)

                print("\nStructured Data:")
                print(result.structured_content)

            elif choice == "2": # Generate research prompt

                topic = input("Enter a topic: ")

                result = await client.get_prompt("prioritize_sections", {"topic": topic})

                print("\nGenerated Prompt:")

                for message in result.messages:
                    if isinstance(message.content, TextContent):
                        print(message.content.text)

            elif choice == "3": # Read server resource

                result = await client.read_resource("info://server")

                print("\nServer Resource:")

                for content in result.contents:
                    if isinstance(content, TextResourceContents):
                        print(content.text)

            elif choice == "4": # Quit
                break

            else:
                print("Invalid option.")


if __name__ == "__main__":
    anyio.run(main)
