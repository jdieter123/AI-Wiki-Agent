from mcp.server import MCPServer

from pathlib import Path
import json

import ollama
import math

from datetime import datetime, timezone

# Set up filepath
MEMORY_FILE = Path(__file__).with_name("memory.json")

mcp = MCPServer("MemoryServer", instructions="A server that saves and retrives long-term memories.")

def get_timestamp() -> str:
    """Return the currrent UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()

def is_memory_expired(memory: dict) -> bool:
    """Check whether a memory has passed its expiration date."""

    expires_at = memory.get("expires_at")

    if not expires_at:
        return False

    try:
        expiration_time = datetime.fromisoformat(expires_at)

        if expiration_time.tzinfo is None:
            expiration_time = expiration_time.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) >= expiration_time

    except (ValueError, TypeError):
        return False

def calculate_status_weight(memory: dict) -> float:
    """Give memories different ranking weights based on their status."""

    status_weights = {
        "active": 1.0,
        "completed": 0.85,
        "outdated": 0.60,
        "archived": 0.40
    }

    status = memory.get("status", "active")

    return status_weights.get(status, 0.75)

def validate_memory(key: str, value: str, category: str, importance: int) -> str | None:
    """Validate memory information before saving."""

    if not key.strip():
        return "Memory key cannot be empty."

    if not value.strip():
        return "Memory value cannot be empty."

    if not category.strip():
        return "Memory category cannot be empty."

    if not isinstance(importance, int) or isinstance(importance, bool):
        return "Importance must be an integer."

    if importance < 1 or importance > 5:
        return "Importance must be between 1 and 5."

    return None

# create backups
def backup_memories() -> str:
    """Create a backup of the memory file."""

    if not MEMORY_FILE.exists():
        return "No memory file exists to back up."

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    backup_file = MEMORY_FILE.with_name(
        f"memory_backup_{timestamp}.json"
    )

    backup_file.write_text(
        MEMORY_FILE.read_text(encoding="utf-8"),
        encoding="utf-8"
    )

    return f"Backup created: {backup_file.name}"

@mcp.tool()
def create_memory_backup() -> str:
    """Create a backup of all saved memories."""
    return backup_memories()

# recency scoring memory
def calculate_recency(memory: dict) -> float:
    """Calculate how recently a memory was updated."""

    updated_at = memory.get("updated_at")

    if not updated_at:
        return 0.5

    try:
        updated_time = datetime.fromisoformat(updated_at)

        # Handle timestamps without timezone information
        if updated_time.tzinfo is None:
            updated_time = updated_time.replace(tzinfo=timezone.utc)

        age = datetime.now(timezone.utc) - updated_time

        age_days = max(0, age.total_seconds() / 86400)

        return math.exp(-age_days / 30)

    except (ValueError, TypeError):
        return 0.5

# Consolidation
CONSOLIDATION_THRESHOLD = 0.90

@mcp.tool()
def consolidate_memories(keep_key: str, delete_key: str, new_value: str) -> str:
    """Combine two similar memories into one improved memory."""

    memories = load_memories()

    if keep_key not in memories:
        return f"No memory found with key: {keep_key}"

    if delete_key not in memories:
        return f"No memory found with key: {delete_key}"

    if keep_key == delete_key:
        return "Cannot consolidate a memory with itself."

    memory_a = memories[keep_key]
    memory_b = memories[delete_key]

    if "embedding" not in memory_a or "embedding" not in memory_b:
        return "Both memories must have embeddings."

    similarity = cosine_similarity(memory_a["embedding"], memory_b["embedding"])

    if similarity < CONSOLIDATION_THRESHOLD:
        return "These memories are not similar enough to consolidate."

    if memories[keep_key].get("protected", False):
        return "Cannot modify the memory being kept: it is protected."

    if memories[delete_key].get("protected", False):
        return "Cannot delete the memory being removed: it is protected."

    # Create a new embedding for the combined information
    new_embedding = create_embedding(new_value)

    # Update the memory we want to keep
    memory_a["value"] = new_value
    memory_a["embedding"] = new_embedding

    memory_a["updated_at"] = get_timestamp()

    # Remove the other memory
    del memories[delete_key]

    save_memories(memories)

    return (
        f"Successfully consolidated memories. "
        f"Kept '{keep_key}' and deleted '{delete_key}'."
    )

@mcp.tool()
def find_similar_memories() -> list[dict]:
    """Find pairs of memories that may contain duplicate info"""

    memories = load_memories()

    results = []
    keys = list(memories.keys())

    for i in range(len(keys)):
        key_a = keys[i]
        memory_a = memories[key_a]

        if "embedding" not in memory_a:
            continue

        for j in range(i + 1, len(keys)):
            key_b = keys[j]
            memory_b = memories[key_b]

            if "embedding" not in memory_b:
                continue

            similarity = cosine_similarity(memory_a["embedding"], memory_b["embedding"])

            if similarity >= CONSOLIDATION_THRESHOLD:
                results.append({
                    "memory_a": key_a,
                    "value_a": memory_a["value"],
                    "memory_b": key_b,
                    "value_b": memory_b["value"],
                    "similarity": similarity
                })

    return results

@mcp.tool()
def remove_duplicate_memory(keep_key: str, delete_key: str) -> str:
    """Remove a duplicate memory while keeping the selected original."""

    memories = load_memories()

    if keep_key not in memories:
        return f"No memory found with key: {keep_key}"

    if delete_key not in memories:
        return f"No memory found with key: {delete_key}"

    if keep_key == delete_key:
        return "Cannot delete a memory while keeping the same memory."

    memory_a = memories[keep_key]
    memory_b = memories[delete_key]

    if "embedding" not in memory_a or "embedding" not in memory_b:
        return "Both memories must have embeddings."

    similarity = cosine_similarity(memory_a["embedding"], memory_b["embedding"])

    if similarity < CONSOLIDATION_THRESHOLD:
        return (
            f"These memories are not similar enough to consolidate. "
            f"Similarity: {similarity:.3f}"
        )

    if memories[delete_key].get("protected", False):
        return f"Cannot delete '{delete_key}': memory is protected."

    del memories[delete_key]

    save_memories(memories)

    return (
        f"Deleted '{delete_key}'. "
        f"Kept '{keep_key}'. "
        f"Similarity: {similarity:.3f}"
    )

# Memory Similarity threshold
SIMILARITY_THRESHOLD = 0.6
MAX_RESULTS = 5

# Duplicates
DUPLICATE_THRESHOLD = 0.95

def find_duplicate_memory(embedding: list[float], memories: dict) -> tuple[str, float] | None:
    """Find an existing memory that is very similar"""

    best_match = None
    highest_similarity = 0.0

    for key, memory in memories.items():
        if "embedding" not in memory:
            continue

        similarity = cosine_similarity(embedding, memory["embedding"])

        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = key

    if highest_similarity >= DUPLICATE_THRESHOLD:
        return best_match, highest_similarity

    return None

# create Embeddings for semantic search
def create_embedding(text: str) -> list[float]:
    """Convert text into an embedding vector"""

    response = ollama.embed(
        model="nomic-embed-text",
        input=text
    )
    
    return response["embeddings"][0]

# Cosine Similarity
def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate the similarity between two embedding vectors"""

    if len(a) != len(b):
        raise ValueError("Embedding vectors must have the same dimensions.")

    dot_product = sum(x * y for x, y in zip(a, b))

    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(y * y for y in b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)

def load_memories():
    """Load existing memories from the JSON file"""
    if not MEMORY_FILE.exists():
        return {}

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {}

        memories = data.get("memories", {})

        if not isinstance(memories, dict):
            return {}

        # adds a category to old memory without
        for key, value in memories.items():
            if isinstance(value, dict):
                value.setdefault("importance", 3)
    
            if isinstance(value, str):

                memories[key] = {
                    "category": "general",
                    "value": value,
                    "importance": 3
                }

        return memories
        
    except (OSError, json.JSONDecodeError):
        return {}

def save_memories(memories):
    """Safely save memories to the JSON file."""

    temp_file = MEMORY_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(
            {"memories": memories},
            file,
            indent=4
        )

    temp_file.replace(MEMORY_FILE)

@mcp.tool()
def update_memory(key: str, new_value: str, category: str | None = None, importance: int | None = None, source: str | None = None, status: str | None = None, force: bool = False) -> str:
    """Update an existing memory and regenerate its embedding."""

    memories = load_memories()

    if key not in memories:
        return f"No memory found with key: {key}"

    old_memory = memories[key]

    new_category = category if category is not None else old_memory.get("category", "general")
    new_importance = importance if importance is not None else old_memory.get("importance", 3)

    error = validate_memory(key, new_value, new_category, new_importance)

    if error:
        return error

    if old_memory.get("protected", False) and not force:
        return f"Memory '{key}' is protected from modification."

    if importance is not None and not 1 <= importance <= 5:
        return "Importance must be between 1 and 5."

    valid_sources = ["explicit", "inferred", "imported"]

    if source is not None and source not in valid_sources:
        return "Invalid memory source."

    valid_statuses = ["active", "completed", "outdated", "archived"]
    
    if status is not None and status not in valid_statuses:
        return "Invalid memory status."

    embedding = create_embedding(new_value)

    updated_memory = {
        "category": new_category,
        "value": new_value,
        "embedding": embedding,
        "importance": new_importance,
        "source": source if source is not None else old_memory.get("source", "unknown"),
        "updated_at": get_timestamp(),
        "expires_at": old_memory.get("expires_at"),
        "status": status if status is not None else old_memory.get("status", "active"),
        "protected": old_memory.get("protected", False)
    }

    if "created_at" in memories[key]:
        updated_memory["created_at"] = old_memory["created_at"]

    memories[key] = updated_memory

    save_memories(memories)

    return f"Successfully updated memory: {key}"

@mcp.tool()
def save_memory(key: str, value: str, category: str = "general", importance: int = 3, source: str = "explicit", expires_at: str | None = None, status: str = "active", protected: bool = False) -> str:
    """Save a piece of info to long-term memory. 
    Categories include preference, project, instruction, and general."""

    error = validate_memory(key, value, category, importance)

    if error:
        return error

    if importance < 1 or importance > 5:
        return "Importance must be between 1 and 5."

    valid_sources = ["explicit", "inferred", "imported"]

    if source not in valid_sources:
        return "Source must be explicit, inferred, or imported"

    valid_statuses = ["active", "completed", "outdated", "archived"]

    if status not in valid_statuses:
        return "Invalid memory status."

    memories = load_memories()

    if key in memories:
        return f"Memory key '{key}' already exists. Use update_memory instead."

    embedding = create_embedding(value)

    duplicate = find_duplicate_memory(embedding, memories)

    if duplicate is not None:
        existing_key, similarity = duplicate

        return (
            f"Possible duplicate found: {existing_key}."
            f"Similarity: {similarity:.3f}."
            "No new memory saved."
        )

    memories[key] = {
        "category": category,
        "value": value,
        "embedding": embedding,
        "importance": importance,
        "source": source,
        "created_at": get_timestamp(),
        "expires_at": expires_at,
        "updated_at": get_timestamp(),
        "status": status,
        "protected": protected
    }

    save_memories(memories)

    return f"Successfully saved memory: {key}"

@mcp.tool()
def read_memories() -> dict:
    """Retrieves all saved long-term memories"""
    return load_memories()

@mcp.tool()
def delete_memory(key: str, force: bool = False) -> str:
    """Delete a saved memory using its key."""
    memories = load_memories()

    if key not in memories:
        return f"No memory found with key: {key}"

    memory = memories[key]
    importance = memory.get("importance", 3)

    if memory.get("protected", False) and not force:
        return f"Memory '{key}' is protected from deletion."

    if importance >= 4 and not force:
        return (
            f"Memory '{key}' has importance {importance}/5. "
            "Deletion blocked. Set force=True to override."
        )

    del memories[key]

    save_memories(memories)

    return f"Successfully deleted memory: {key}"

@mcp.tool()
def search_memory(category: str) -> dict:
    """Retrieve memories belonging to a specific category."""

    memories = load_memories()

    results = {}

    for key, memory in memories.items():
        if memory.get("category", "general").lower() == category.lower():
            results[key] = memory

    return results

@mcp.tool()
def semantic_search(query: str, category: str = "", limit: int=5) -> list[dict]:
    """Find memories that are semantically similar to a question. Returns the most relevant memories."""
    
    memories = load_memories()
    query_embedding = create_embedding(query)

    results = []

    for key, memory in memories.items():
        if is_memory_expired(memory):
            continue

        if "embedding" not in memory:
            continue

        memory_category = memory.get("category", "general")

        # optional category filter
        if category and memory_category.lower() != category.lower():
            continue
        
        similarity = cosine_similarity(query_embedding, memory["embedding"])

        if similarity < SIMILARITY_THRESHOLD:
            continue

        importance = memory.get("importance", 3) / 5

        recency = calculate_recency(memory)

        base_relevance = (similarity * 0.7 + importance * 0.2 + recency * 0.1)
        status_weight = calculate_status_weight(memory)

        relevance_score = base_relevance * status_weight

        results.append({
            "key": key,
            "category": memory_category,
            "value": memory["value"],
            "similarity": similarity,
            "importance": importance,
            "source": memory.get("source", "unknown"),
            "recency": recency,
            "relevance_score": relevance_score,
            "status": memory.get("status", "active"),
            "status_weight": status_weight,
            "explanation": (
                f"Similarity: {similarity:.2f}. "
                f"Importance: {memory.get('importance', 3)}/5. "
                f"Recency: {recency:.2f}. "
                f"Status: {memory.get('status', 'active')}."
            )
        })

    results.sort(
        key=lambda item: item["relevance_score"],
        reverse=True
    )

    result_limit = min(max(1, limit), MAX_RESULTS)

    return results[:result_limit]

@mcp.tool()
def cleanup_expired_memories() -> str:
    """Delete all memories that have expired."""

    memories = load_memories()

    expired_keys = []

    for key, memory in memories.items():
        if is_memory_expired(memory) and not memory.get("protected", False):
            expired_keys.append(key)

    for key in expired_keys:
        del memories[key]

    save_memories(memories)

    return f"Deleted {len(expired_keys)} expired memories."

@mcp.tool()
def migrate_memories() -> str:
    """Generate embeddings for memories that don't have them."""

    memories = load_memories()

    migrated = 0

    for key, memory in memories.items():

        if "embedding" in memory:
            continue

        embedding = create_embedding(memory["value"])

        memory["embedding"] = embedding

        migrated += 1

    save_memories(memories)

    return f"Successfully generated {migrated} embeddings."

# MCP PROMPTS
@mcp.prompt()
def classify_memory_importance(value: str) -> str:
    """Help the agent decide how important a memory is. """

    return f"""
        Decide how important this memory is for future conversations.

        Memory:
        {value}

        Choose an importance score from 1 to 5.

        1 = Very temporary or unlikely to matter again.
        2 = Low importance.
        3 = Normal useful information.
        4 = Important ongoing information.
        5 = Very important lasting preference or instruction.

        Return:
        - Importance score
        - Short explanation

        Do not invent information that is not present in the memory.
    """

@mcp.prompt()
def classify_memory_category(value: str) -> str:
    """Determine the best category for a memory."""

    return f"""
        Choose the best category for this memory:

        Memory:
        {value}

        Available categories:

        preference = Likes, dislikes, and personal preferences.
        project = Ongoing projects and their details.
        instruction = Instructions for how the agent should behave.
        goal = Long-term goals and ambitions.
        skill = Programming languages and other abilities.
        general = Information that doesn't fit elsewhere.

        Return:
        - The selected category
        - A short explanation

        Choose only one category.
        Do not invent information.
    """

@mcp.prompt()
def check_memory_contradiction(existing_memory: str, new_memory: str) -> str:
    """Determine whether new information contradicts an existing memory."""

    return f"""
        Compare these two memories.

        Existing memory:
        {existing_memory}

        New memory:
        {new_memory}

        Determine whether they are:

        1. DUPLICATE:
        Both memories communicate essentially the same information.

        2. CONTRADICTION:
        The new information conflicts with the existing information.

        3. UNRELATED:
        The memories describe different information.

        Important rules:
        - Do not assume that different wording means contradiction.
        - Consider whether the new information represents a change over time.
        - Do not invent missing details.
        - If the relationship is unclear, choose UNRELATED.

        Return:
        Classification: DUPLICATE, CONTRADICTION, or UNRELATED
        Explanation: A short explanation.
        Recommended action: What the memory system should do.
    """

@mcp.prompt()
def resolve_memory_conflict(existing_memory: str, new_memory: str) -> str:
    """Recommend how to resolve conflicting memories."""

    return f"""
        You are managing an AI agent's long-term memory.

        Existing memory:
        {existing_memory}

        New information:
        {new_memory}

        Determine the best way to handle this information.

        Available strategies:

        1. REPLACE:
        The new information makes the old information outdated.
        Recommend updating the existing memory.

        2. PRESERVE_HISTORY:
        The new information represents a change over time.
        Recommend preserving the old information as historical
        context and saving the new information separately.

        3. KEEP_BOTH:
        Both memories are valid and describe different situations.

        4. ASK_USER:
        There is not enough information to safely resolve the conflict.

        Rules:
        - Never invent information.
        - Do not delete important historical information unnecessarily.
        - Prefer the user's explicitly stated current information.
        - Do not assume that every contradiction means the old memory
        should be deleted.

        Return:
        Strategy: One of the four strategies.
        Explanation: Why you selected it.
        Recommended action: What the memory system should do.
    """

if __name__ == "__main__":
    mcp.run()