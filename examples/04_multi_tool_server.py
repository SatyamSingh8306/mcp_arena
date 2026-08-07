"""
04_multi_tool_server.py — MCP Server with Multiple Tools and Structured Data

A slightly more advanced example showing how to build a server with
multiple tools that return structured data. This pattern is common
in real-world MCP servers (e.g., GitHub, Jira, Slack presets).

Usage:
    python 04_multi_tool_server.py

What it demonstrates:
    - Registering multiple tools in one server
    - Returning structured (dict) responses from tools
    - Using type hints for tool parameters
    - Organizing tools with clear docstrings
"""

from typing import Optional
from mcp_arena import BaseMCPServer


# ─── In-Memory Data Store (simulates a database) ────────────────────────────

CONTACTS = {
    "alice": {"name": "Alice", "email": "alice@example.com", "role": "Engineer"},
    "bob": {"name": "Bob", "email": "bob@example.com", "role": "Designer"},
    "carol": {"name": "Carol", "email": "carol@example.com", "role": "Manager"},
}


# ─── Server Definition ──────────────────────────────────────────────────────

class ContactServer(BaseMCPServer):
    """MCP server for managing a simple contact list."""

    def __init__(self):
        super().__init__(
            name="contact-server",
            description="Manage a simple contact directory",
            transport="stdio",
        )

    def _register_tools(self) -> None:
        """Register contact management tools."""

        @self.mcp_server.tool()
        def list_contacts() -> dict:
            """List all contacts in the directory.

            Returns:
                A dictionary with the total count and list of contacts.
            """
            return {
                "total": len(CONTACTS),
                "contacts": list(CONTACTS.values()),
            }

        @self.mcp_server.tool()
        def get_contact(username: str) -> dict:
            """Look up a contact by username.

            Args:
                username: The username to look up (e.g., 'alice').

            Returns:
                The contact details, or an error message if not found.
            """
            contact = CONTACTS.get(username.lower())
            if contact:
                return {"found": True, **contact}
            return {"found": False, "error": f"No contact found for '{username}'"}

        @self.mcp_server.tool()
        def add_contact(
            username: str,
            name: str,
            email: str,
            role: Optional[str] = "Member",
        ) -> dict:
            """Add a new contact to the directory.

            Args:
                username: Unique username for the contact.
                name: Full name of the contact.
                email: Email address.
                role: Role or title (defaults to 'Member').

            Returns:
                Confirmation with the created contact details.
            """
            if username.lower() in CONTACTS:
                return {"success": False, "error": f"'{username}' already exists"}

            CONTACTS[username.lower()] = {
                "name": name,
                "email": email,
                "role": role,
            }
            return {
                "success": True,
                "message": f"Contact '{username}' added",
                "contact": CONTACTS[username.lower()],
            }

        @self.mcp_server.tool()
        def search_contacts(query: str) -> dict:
            """Search contacts by name, email, or role.

            Args:
                query: Search term to match against contact fields.

            Returns:
                Matching contacts.
            """
            query_lower = query.lower()
            matches = [
                contact
                for contact in CONTACTS.values()
                if query_lower in contact["name"].lower()
                or query_lower in contact["email"].lower()
                or query_lower in contact["role"].lower()
            ]
            return {"query": query, "results": matches, "count": len(matches)}

        self._registered_tools.extend([
            "list_contacts",
            "get_contact",
            "add_contact",
            "search_contacts",
        ])

        # --- Prompt: Contact lookup template ---
        @self.mcp_server.prompt()
        def lookup_prompt(username: str) -> str:
            """Generate a prompt for looking up a contact.

            Args:
                username: The username to look up.

            Returns:
                A formatted prompt string.
            """
            return f"Look up the contact details for username '{username}' and summarize their information."


# --- Entry Point ---
if __name__ == "__main__":
    server = ContactServer()

    print(f"Server: {server.name}")
    print(f"Tools:  {server.get_registered_tools()}")
    print("Starting server on stdio transport...")

    server.run()
