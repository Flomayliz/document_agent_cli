#!/usr/bin/env python3
"""
CLI app to interact with the LLM Document PoC API.

This CLI provides an interactive interface to communicate with the QA endpoint.
On startup, it sends a greeting and asks about capabilities.
"""

import asyncio
import os
import sys
from typing import Optional
import httpx
import click


class APIClient:
    """Client for interacting with the LLM Document PoC API."""

    def __init__(
        self, base_url: str = "http://localhost:8000", token: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.session_id = "cli-session"
        self.token = token

    def _get_headers(self) -> dict:
        """Get headers with authentication if token is provided."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def health_check(self) -> bool:
        """Check if the API is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False

    async def ask_question(self, question: str, doc_id: Optional[str] = None) -> dict:
        """Send a question to the QA endpoint."""
        payload = {"question": question, "session_id": self.session_id}
        if doc_id:
            payload["doc_id"] = doc_id

        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/agent/qa", json=payload, headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def list_documents(self) -> dict:
        """List available documents."""
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/docs", headers=headers)
            response.raise_for_status()
            return response.json()

    async def upload_document(self, file_path: str) -> dict:
        """Upload a document to the API."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        with open(file_path, "rb") as f:
            files = {"file": (file_path.split("/")[-1], f, "application/octet-stream")}
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/agent/docs", files=files, headers=headers
                )
                response.raise_for_status()
                return response.json()

    async def delete_document(self, filename: str) -> dict:
        """Delete a document from the watch folder."""
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/agent/docs/{filename}", headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def get_document_summary(self, doc_id: str, length: int = 150) -> dict:
        """Get a summary of a document."""
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/agent/docs/{doc_id}/summary",
                params={"length": length},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_document_topics(self, doc_id: str) -> dict:
        """Get topics for a document."""
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/agent/docs/{doc_id}/topics", headers=headers
            )
            response.raise_for_status()
            return response.json()


def print_header():
    """Print a nice header for the CLI."""
    print("=" * 60)
    print("🤖  LLM Document PoC CLI  🤖")
    print("=" * 60)
    print()


def print_separator():
    """Print a separator line."""
    print("-" * 40)


def display_response(response_data: dict):
    """Display the API response in a nice format."""
    answer = response_data.get("answer", "No answer received")
    doc_id = response_data.get("doc_id")
    session_id = response_data.get("session_id")

    print_separator()
    print("🤖 Agent Response:")
    if doc_id:
        print(f"📄 Document: {doc_id}")
    if session_id:
        print(f"🔗 Session: {session_id}")
    print()
    print(answer)
    print_separator()
    print()


async def startup_greeting(client: APIClient):
    """Send startup greeting and ask about capabilities."""
    print("🚀 Initializing connection...")

    # Check API health
    print("⏳ Checking API connection...")
    is_healthy = await client.health_check()

    if not is_healthy:
        print("❌ Could not connect to API. Please ensure the server is running.")
        print("Expected API at: http://localhost:8000")
        sys.exit(1)

    print("✅ Connected to API successfully!")

    # Check authentication if token is provided
    if client.token:
        print("🔑 Checking authentication...")
        try:
            # Try a simple authenticated request to verify token
            await client.ask_question(
                "Hello! Please tell me what capabilities do you have?"
            )
            print("✅ Authentication successful!")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("❌ Authentication failed. Please check your token.")
                sys.exit(1)
            else:
                print(f"❌ Unexpected error during authentication: {e}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error during authentication check: {e}")
            sys.exit(1)
    else:
        print("⚠️  No authentication token provided.")
        print("    Set APP_API_TOKEN environment variable or use --token argument.")
        print("    Some features may not work without authentication.")

    print()

    # Send greeting and capability question
    print("⏳ Asking about capabilities...")
    try:
        response = await client.ask_question(
            "Hello! Please tell me what capabilities do you have?"
        )
        display_response(response)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print(
                "❌ Authentication required for this operation. Please provide a valid token."
            )
        else:
            print(f"❌ Error during startup greeting: {e}")
        print()
    except Exception as e:
        print(f"❌ Error during startup greeting: {e}")
        print()


async def interactive_loop(client: APIClient):
    """Main interactive loop for the CLI."""
    print("💡 Type your questions below. Use 'help' for commands or 'quit' to exit.")
    print()

    while True:
        try:
            # Get user input
            question = input("🤔 Your question: ").strip()

            if not question:
                continue

            # Handle special commands
            if question.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break
            elif question.lower() in ["help", "h"]:
                show_help()
                continue
            elif question.lower() in ["docs", "documents"]:
                await show_documents(client)
                continue
            elif question.lower().startswith("upload:"):
                # Handle file upload: upload:/path/to/file
                file_path = question[7:].strip()
                if file_path:
                    await handle_upload(client, file_path)
                else:
                    print("❌ Please provide a file path. Use: upload:/path/to/file")
                continue
            elif question.lower().startswith("summary:"):
                # Handle summary request: summary:DOC_ID or summary:DOC_ID:LENGTH
                parts = question[8:].strip().split(":")
                if len(parts) >= 1 and parts[0]:
                    doc_id = parts[0]
                    length = (
                        int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 150
                    )
                    await handle_summary(client, doc_id, length)
                else:
                    print(
                        "❌ Please provide a document ID. Use: summary:DOC_ID or summary:DOC_ID:LENGTH"
                    )
                continue
            elif question.lower().startswith("topics:"):
                # Handle topics request: topics:DOC_ID
                doc_id = question[7:].strip()
                if doc_id:
                    await handle_topics(client, doc_id)
                else:
                    print("❌ Please provide a document ID. Use: topics:DOC_ID")
                continue
            elif question.lower().startswith("delete:"):
                # Handle file deletion: delete:filename.pdf
                filename = question[7:].strip()
                if filename:
                    await handle_delete(client, filename)
                else:
                    print("❌ Please provide a filename. Use: delete:filename.pdf")
                continue
            elif question.lower().startswith("clear"):
                # Clear screen (works on most terminals)
                print("\033[2J\033[H")
                print_header()
                continue

            # Check if it's a document-specific question
            doc_id = None
            if question.lower().startswith("doc:"):
                parts = question.split(":", 1)
                if len(parts) == 2:
                    doc_parts = parts[1].strip().split(" ", 1)
                    if len(doc_parts) >= 2:
                        doc_id = doc_parts[0]
                        question = doc_parts[1]
                    else:
                        print("❌ Invalid format. Use: doc:DOC_ID your question")
                        continue

            # Send question to API
            print("⏳ Thinking...")
            response = await client.ask_question(question, doc_id)
            display_response(response)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("❌ Authentication required. Please provide a valid token.")
            else:
                print(f"❌ HTTP Error: {e}")
            print()
        except Exception as e:
            print(f"❌ Error: {e}")
            print()


async def handle_upload(client: APIClient, file_path: str):
    """Handle file upload."""
    try:
        if not client.token:
            print("❌ Authentication required for file upload. Please provide a token.")
            return

        print(f"⏳ Uploading file: {file_path}")
        result = await client.upload_document(file_path)
        file_path = result.get("file_path", "Unknown")
        status = result.get("status", "Unknown")
        print(f"✅ File uploaded successfully! Path: {file_path}, Status: {status}")
        print("⌛ The file will be automatically ingested by the document watcher")
        print_separator()
        print()
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        print()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed. Please check your token.")
        elif e.response.status_code == 413:
            print("❌ File too large (max 2 MiB).")
        else:
            print(f"❌ Upload failed: {e}")
        print()
    except Exception as e:
        print(f"❌ Upload error: {e}")
        print()


async def handle_summary(client: APIClient, doc_id: str, length: int = 150):
    """Handle document summary request."""
    try:
        if not client.token:
            print(
                "❌ Authentication required for document summary. Please provide a token."
            )
            return

        print(f"⏳ Generating summary for document {doc_id} ({length} words)...")
        result = await client.get_document_summary(doc_id, length)
        summary = result.get("summary", "No summary available")

        print_separator()
        print(f"📄 Summary for Document: {doc_id}")
        print(f"📏 Length: {length} words")
        print()
        print(summary)
        print_separator()
        print()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed. Please check your token.")
        elif e.response.status_code == 404:
            print(f"❌ Document not found: {doc_id}")
        else:
            print(f"❌ Summary request failed: {e}")
        print()
    except Exception as e:
        print(f"❌ Summary error: {e}")
        print()


async def handle_topics(client: APIClient, doc_id: str):
    """Handle document topics request."""
    try:
        if not client.token:
            print(
                "❌ Authentication required for document topics. Please provide a token."
            )
            return

        print(f"⏳ Fetching topics for document {doc_id}...")
        result = await client.get_document_topics(doc_id)
        topics = result.get("topics", [])

        print_separator()
        print(f"🏷️  Topics for Document: {doc_id}")
        print()
        if topics:
            for topic in topics:
                print(f"  • {topic}")
        else:
            print("  No topics found")
        print_separator()
        print()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed. Please check your token.")
        elif e.response.status_code == 404:
            print(f"❌ Document not found: {doc_id}")
        else:
            print(f"❌ Topics request failed: {e}")
        print()
    except Exception as e:
        print(f"❌ Topics error: {e}")
        print()


async def handle_delete(client: APIClient, filename: str):
    """Handle document deletion."""
    try:
        if not client.token:
            print(
                "❌ Authentication required for document deletion. Please provide a token."
            )
            return

        print(f"⏳ Deleting document: {filename}...")
        result = await client.delete_document(filename)

        print_separator()
        print(f"🗑️  Document deleted: {filename}")
        print(f"Status: {result.get('status', 'completed')}")
        print_separator()
        print()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed. Please check your token.")
        elif e.response.status_code == 404:
            print(f"❌ File not found: {filename}")
        else:
            print(f"❌ Deletion failed: {e}")
        print()
    except Exception as e:
        print(f"❌ Deletion error: {e}")
        print()


def show_help():
    """Display help information."""
    print_separator()
    print("📖 Help - Available Commands:")
    print()
    print("• help, h                    - Show this help message")
    print("• docs, documents            - List available documents")
    print("• doc:DOC_ID your question   - Ask a question about a specific document")
    print("• upload:/path/to/file       - Upload a document")
    print("• delete:filename            - Delete a document from the watch folder")
    print("• summary:DOC_ID             - Get document summary (150 words)")
    print("• summary:DOC_ID:LENGTH      - Get document summary (custom length)")
    print("• topics:DOC_ID              - Get document topics")
    print("• clear                      - Clear the screen")
    print("• quit, exit, q              - Exit the CLI")
    print()
    print("Examples:")
    print("• What can you do?")
    print("• doc:12345 What is this document about?")
    print("• upload:/home/user/document.pdf")
    print("• delete:document.pdf")
    print("• summary:12345")
    print("• summary:12345:300")
    print("• topics:12345")
    print("• Summarize the latest research on AI")
    print()
    print("Authentication:")
    print("• Use --token argument or set APP_API_TOKEN environment variable")
    print(
        "• Document operations (upload, delete, summary, topics) require authentication"
    )
    print_separator()
    print()


async def show_documents(client: APIClient):
    """Show available documents."""
    try:
        if not client.token:
            print(
                "❌ Authentication required to list documents. Please provide a token."
            )
            print()
            return

        print("⏳ Fetching documents...")
        docs = await client.list_documents()

        print_separator()
        if not docs or not docs.get("documents"):
            print("📄 No documents available")
        else:
            print("📚 Available Documents:")
            print()
            for doc in docs["documents"]:
                doc_id = doc.get("id", "Unknown")
                filename = doc.get("filename", "Unknown")
                print(f"  • {doc_id}: {filename}")
        print_separator()
        print()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed. Please check your token.")
        else:
            print(f"❌ Error fetching documents: {e}")
        print()
    except Exception as e:
        print(f"❌ Error fetching documents: {e}")
        print()


@click.command()
@click.option("--url", default="http://localhost:8000", help="API base URL")
@click.option("--token", "-t", help="Authentication token for API access")
@click.option("--no-greeting", is_flag=True, help="Skip startup greeting")
def main(url: str, token: Optional[str], no_greeting: bool):
    """
    Interactive CLI for the LLM Document PoC API.

    This CLI allows you to interact with the QA endpoint through a conversational interface.
    On startup, it will greet the agent and ask about its capabilities.

    Authentication is required for certain operations like document upload,
    summary generation, and topics extraction.

    If no token is provided via --token, the CLI will check the
    APP_API_TOKEN environment variable.
    """
    print_header()

    # Get token from environment if not provided as argument
    if not token:
        token = os.getenv("APP_API_TOKEN")
        if token:
            print("🔑 Using token from APP_API_TOKEN environment variable")

    client = APIClient(base_url=url, token=token)

    async def run_cli():
        if not no_greeting:
            await startup_greeting(client)
        await interactive_loop(client)

    try:
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
