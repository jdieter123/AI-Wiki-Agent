from mcp.server import MCPServer

from pathlib import Path

# Set up filepath
KNOWLEDGE_DIR = Path(__file__).with_name("knowledge")

mcp = MCPServer("SearchNotesServer", instructions="A server for searching a file folders different notes")

# file search
@mcp.tool()
def search_notes(query: str) -> list[dict]:
    """Search through text and markdown files for knowledge on different subjects"""

    results = []

    if not KNOWLEDGE_DIR.exists():
        return []

    for file in KNOWLEDGE_DIR.iterdir():
        if file.suffix.lower() not in [".txt", ".md"]: # only search text and markdown files
            continue
        if not file.is_file() or file.is_symlink():
            continue
        if file.stat().st_size > 1_000_000: # avoid reading unusually large files
            continue

        try:
            contents = file.read_text(encoding="utf-8")

            for line_number, line in enumerate(contents.splitlines(), start=1):
                if query.lower() in line.lower():
                    results.append({
                        "file": file.name,
                        "line": line_number,
                        "match": line.strip()
                    })

                if len(results) >= 10: # limit number of matches
                    return results
        except (OSError, UnicodeDecodeError):
            continue

    return results

if __name__ == "__main__":
    mcp.run()