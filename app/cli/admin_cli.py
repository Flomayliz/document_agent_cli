#!/usr/bin/env python3
"""
CLI for user management operations using the Admin API.

This CLI provides functionality to manage users, tokens, and view user history
by making HTTP requests to the Admin API instead of connecting directly to the database.
Both command-line and interactive modes are supported.
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

import click
import httpx
from tabulate import tabulate

# Admin API configuration
ADMIN_API_BASE_URL = "http://127.0.0.1:8001"
ADMIN_API_PREFIX = "/admin"


class AdminAPIClient:
    """HTTP client for the Admin API."""

    def __init__(self, base_url: str = ADMIN_API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        """Make an HTTP request to the admin API."""
        url = f"{self.base_url}{ADMIN_API_PREFIX}{endpoint}"

        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            try:
                error_detail = e.response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)
            raise Exception(f"API Error ({e.response.status_code}): {error_detail}")
        except httpx.RequestError as e:
            raise Exception(
                f"Connection Error: {str(e)}. Make sure the Admin API is running on {self.base_url}"
            )

    async def create_user(
        self, email: str, name: str, token_hours: int = 24
    ) -> Dict[str, Any]:
        """Create a new user."""
        data = {"email": email, "name": name, "token_validity_hours": token_hours}
        return await self._make_request("POST", "/users/", json=data)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return await self._make_request("GET", f"/users/{user_id}")

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        return await self._make_request("GET", f"/users/by-email/{email}")

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a token."""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._make_request(
            "POST", "/users/validate-token", headers=headers
        )

    async def refresh_token(
        self, user_id: str, token_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """Refresh user's token."""
        params = {"token_validity_hours": token_hours}
        return await self._make_request(
            "POST", f"/users/{user_id}/refresh-token", params=params
        )

    async def add_qa(
        self, user_id: str, question: str, answer: str
    ) -> Optional[Dict[str, Any]]:
        """Add Q/A to user history."""
        data = {"question": question, "answer": answer}
        return await self._make_request("POST", f"/users/{user_id}/add-qa", json=data)

    async def get_user_history(
        self, user_id: str, limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """Get user's Q/A history."""
        params = {"limit": limit}
        return await self._make_request(
            "GET", f"/users/{user_id}/history", params=params
        )

    async def delete_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Delete a user."""
        return await self._make_request("DELETE", f"/users/{user_id}")

    async def list_users(
        self, limit: int = 50, skip: int = 0
    ) -> Optional[Dict[str, Any]]:
        """List all users."""
        params = {"limit": limit, "skip": skip}
        return await self._make_request("GET", "/users/list", params=params)


class UserCLI:
    """CLI interface for user management using Admin API."""

    def __init__(self):
        self.api_client = AdminAPIClient()

    async def close(self):
        """Close the API client."""
        await self.api_client.close()

    async def create_user(self, email: str, name: str, token_hours: int = 24):
        """Create a new user."""
        try:
            result = await self.api_client.create_user(email, name, token_hours)
            if result:
                click.echo("✅ User created successfully!")
                click.echo(f"   ID: {result['user_id']}")
                click.echo(f"   Email: {result['email']}")
                click.echo(f"   Name: {result['name']}")
                click.echo(f"   Token: {result['token']}")
                click.echo(f"   Expires: {result['expires_at']}")
                return result
            else:
                click.echo("❌ Failed to create user")
                return None
        except Exception as e:
            click.echo(f"❌ Error creating user: {e}")
            return None

    async def get_user(self, user_id: str):
        """Get user by ID."""
        try:
            user = await self.api_client.get_user_by_id(user_id)
            if user:
                self._display_user(user)
            else:
                click.echo(f"❌ User with ID {user_id} not found")
            return user
        except Exception as e:
            click.echo(f"❌ Error getting user: {e}")
            return None

    async def get_user_by_email(self, email: str):
        """Get user by email."""
        try:
            user = await self.api_client.get_user_by_email(email)
            if user:
                self._display_user(user)
            else:
                click.echo(f"❌ User with email {email} not found")
            return user
        except Exception as e:
            click.echo(f"❌ Error getting user: {e}")
            return None

    async def validate_token(self, token: str):
        """Validate a token."""
        try:
            result = await self.api_client.validate_token(token)
            if result and result.get("valid"):
                user = result.get("user", {})
                click.echo("✅ Token is valid")
                click.echo(f"   Belongs to: {user.get('name')} ({user.get('email')})")
                click.echo(f"   Expires: {user.get('token_expires')}")
                return True
            else:
                click.echo("❌ Token is invalid or expired")
                return False
        except Exception as e:
            click.echo(f"❌ Error validating token: {e}")
            return False

    async def refresh_token(self, user_id: str, token_hours: int = 24):
        """Refresh user's token."""
        try:
            result = await self.api_client.refresh_token(user_id, token_hours)
            if result:
                click.echo("✅ Token refreshed successfully!")
                click.echo(f"   New Token: {result['new_token']}")
                click.echo(f"   Expires: {result['expires_at']}")
                return result
            else:
                click.echo(f"❌ User with ID {user_id} not found")
                return None
        except Exception as e:
            click.echo(f"❌ Error refreshing token: {e}")
            return None

    async def add_qa(self, user_id: str, question: str, answer: str):
        """Add Q/A to user history."""
        try:
            result = await self.api_client.add_qa(user_id, question, answer)
            if result:
                click.echo("✅ Q/A added to history!")
                click.echo(f"   Total history items: {result['total_history_items']}")
                return result
            else:
                click.echo(f"❌ User with ID {user_id} not found")
                return None
        except Exception as e:
            click.echo(f"❌ Error adding Q/A: {e}")
            return None

    async def show_history(self, user_id: str):
        """Show user's Q/A history."""
        try:
            result = await self.api_client.get_user_history(user_id)
            if result and "history" in result:
                history = result["history"]
                total_count = result.get("total_count", len(history))

                if history:
                    click.echo(f"📚 User history ({total_count} items):")
                    click.echo()

                    # Prepare data for table
                    table_data = []
                    for i, qa in enumerate(history, 1):
                        # Parse timestamp if it's a string
                        timestamp = qa.get("timestamp", "")
                        if isinstance(timestamp, str):
                            try:
                                # Try to parse ISO format
                                dt = datetime.fromisoformat(
                                    timestamp.replace("Z", "+00:00")
                                )
                                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                formatted_time = timestamp
                        else:
                            formatted_time = str(timestamp)

                        table_data.append(
                            [
                                i,
                                qa.get("question", "")[:50] + "..."
                                if len(qa.get("question", "")) > 50
                                else qa.get("question", ""),
                                qa.get("answer", "")[:50] + "..."
                                if len(qa.get("answer", "")) > 50
                                else qa.get("answer", ""),
                                formatted_time,
                            ]
                        )

                    headers = ["#", "Question", "Answer", "Timestamp"]
                    click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
                else:
                    click.echo("📚 User history is empty")
                return result
            else:
                click.echo(f"❌ User with ID {user_id} not found")
                return None
        except Exception as e:
            click.echo(f"❌ Error getting history: {e}")
            return None

    async def delete_user(self, user_id: str):
        """Delete a user."""
        try:
            result = await self.api_client.delete_user(user_id)
            if result:
                click.echo("✅ User deleted successfully!")
                if "deleted_user" in result:
                    deleted = result["deleted_user"]
                    click.echo(
                        f"   Deleted: {deleted.get('name')} ({deleted.get('email')})"
                    )
                return True
            else:
                click.echo(f"❌ User with ID {user_id} not found")
                return False
        except Exception as e:
            click.echo(f"❌ Error deleting user: {e}")
            return False

    async def list_users(self, limit: int = 50, skip: int = 0):
        """List all users."""
        try:
            result = await self.api_client.list_users(limit, skip)
            if result:
                click.echo("👥 List All Users:")
                click.echo(f"   {result}")
                return result
            else:
                click.echo("❌ Error listing users")
                return None
        except Exception as e:
            click.echo(f"❌ Error listing users: {e}")
            return None

    def _display_user(self, user: Dict[str, Any]):
        """Display user information."""
        click.echo("👤 User Information:")
        click.echo(f"   ID: {user.get('user_id')}")
        click.echo(f"   Email: {user.get('email')}")
        click.echo(f"   Name: {user.get('name')}")
        click.echo(f"   Token Valid: {'✅' if user.get('token_valid') else '❌'}")
        click.echo(f"   Token Expires: {user.get('token_expires')}")
        click.echo(f"   History Items: {user.get('history_count', 0)}")
        click.echo(f"   Created: {user.get('created_at')}")
        click.echo(f"   Updated: {user.get('updated_at')}")

    async def interactive_mode(self):
        """Run the CLI in interactive mode."""
        click.echo("🚀 Welcome to the User Management CLI")
        click.echo(f"   Using Admin API: {ADMIN_API_BASE_URL}")
        click.echo("=" * 50)

        try:
            while True:
                click.echo()
                click.echo("Available commands:")
                click.echo("  1. Create user")
                click.echo("  2. Get user by ID")
                click.echo("  3. Get user by email")
                click.echo("  4. Validate token")
                click.echo("  5. Refresh token")
                click.echo("  6. Add Q/A to history")
                click.echo("  7. Show user history")
                click.echo("  8. Delete user")
                click.echo("  9. List all users")
                click.echo("  0. Exit")
                click.echo()

                choice = click.prompt("Select an option", type=int, default=0)

                try:
                    if choice == 0:
                        click.echo("👋 Goodbye!")
                        break
                    elif choice == 1:
                        await self._interactive_create_user()
                    elif choice == 2:
                        await self._interactive_get_user_by_id()
                    elif choice == 3:
                        await self._interactive_get_user_by_email()
                    elif choice == 4:
                        await self._interactive_validate_token()
                    elif choice == 5:
                        await self._interactive_refresh_token()
                    elif choice == 6:
                        await self._interactive_add_qa()
                    elif choice == 7:
                        await self._interactive_show_history()
                    elif choice == 8:
                        await self._interactive_delete_user()
                    elif choice == 9:
                        await self._interactive_list_users()
                    else:
                        click.echo("❌ Invalid option. Please try again.")
                except KeyboardInterrupt:
                    click.echo("\n👋 Goodbye!")
                    break
                except Exception as e:
                    click.echo(f"❌ Error: {e}")

                if choice != 0:
                    click.pause()
        finally:
            await self.close()

    async def _interactive_create_user(self):
        """Interactive user creation."""
        click.echo("\n📝 Create New User")
        click.echo("-" * 20)

        email = click.prompt("Email address", type=str)
        name = click.prompt("Display name", type=str)
        token_hours = click.prompt("Token validity (hours)", type=int, default=24)

        await self.create_user(email, name, token_hours)

    async def _interactive_get_user_by_id(self):
        """Interactive get user by ID."""
        click.echo("\n🔍 Get User by ID")
        click.echo("-" * 17)

        user_id = click.prompt("User ID", type=str)
        await self.get_user(user_id)

    async def _interactive_get_user_by_email(self):
        """Interactive get user by email."""
        click.echo("\n🔍 Get User by Email")
        click.echo("-" * 20)

        email = click.prompt("Email address", type=str)
        await self.get_user_by_email(email)

    async def _interactive_validate_token(self):
        """Interactive token validation."""
        click.echo("\n🔐 Validate Token")
        click.echo("-" * 16)

        token = click.prompt("Access token", type=str, hide_input=True)
        await self.validate_token(token)

    async def _interactive_refresh_token(self):
        """Interactive token refresh."""
        click.echo("\n🔄 Refresh Token")
        click.echo("-" * 16)

        user_id = click.prompt("User ID", type=str)
        token_hours = click.prompt("Token validity (hours)", type=int, default=24)
        await self.refresh_token(user_id, token_hours)

    async def _interactive_add_qa(self):
        """Interactive Q/A addition."""
        click.echo("\n💬 Add Q/A to History")
        click.echo("-" * 21)

        user_id = click.prompt("User ID", type=str)
        question = click.prompt("Question", type=str)
        answer = click.prompt("Answer", type=str)
        await self.add_qa(user_id, question, answer)

    async def _interactive_show_history(self):
        """Interactive history display."""
        click.echo("\n📚 Show User History")
        click.echo("-" * 20)

        user_id = click.prompt("User ID", type=str)
        await self.show_history(user_id)

    async def _interactive_delete_user(self):
        """Interactive user deletion."""
        click.echo("\n🗑️  Delete User")
        click.echo("-" * 14)

        user_id = click.prompt("User ID", type=str)
        if click.confirm(f"Are you sure you want to delete user {user_id}?"):
            await self.delete_user(user_id)
        else:
            click.echo("Operation cancelled.")

    async def _interactive_list_users(self):
        """Interactive list all users."""
        click.echo("\n👥 List All Users")
        click.echo("-" * 16)

        limit = click.prompt("Limit (max users to show)", type=int, default=50)
        skip = click.prompt("Skip (users to skip)", type=int, default=0)
        await self.list_users(limit, skip)


# CLI Commands


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """User Management CLI for Application (using Admin API)."""
    if ctx.invoked_subcommand is None:
        # No subcommand was provided, run interactive mode
        async def run():
            cli_instance = UserCLI()
            try:
                await cli_instance.interactive_mode()
            finally:
                await cli_instance.close()

        asyncio.run(run())


@cli.command()
def interactive():
    """Launch interactive user management mode."""

    async def run():
        cli_instance = UserCLI()
        try:
            await cli_instance.interactive_mode()
        finally:
            await cli_instance.close()

    asyncio.run(run())


@cli.command()
@click.option("--email", required=True, help="User email address")
@click.option("--name", required=True, help="User display name")
@click.option("--token-hours", default=24, help="Token validity in hours (default: 24)")
def create(email: str, name: str, token_hours: int):
    """Create a new user."""

    async def run():
        cli_instance = UserCLI()
        try:
            await cli_instance.create_user(email, name, token_hours)
        finally:
            await cli_instance.close()

    asyncio.run(run())


@cli.command()
@click.option("--user-id", help="User ID")
@click.option("--email", help="User email")
def get(user_id: Optional[str], email: Optional[str]):
    """Get user by ID or email."""
    if not user_id and not email:
        click.echo("❌ Please provide either --user-id or --email")
        return

    if user_id and email:
        click.echo("❌ Please provide either --user-id or --email, not both")
        return

    async def run():
        cli_instance = UserCLI()
        try:
            if user_id:
                await cli_instance.get_user(user_id)
            else:
                await cli_instance.get_user_by_email(email)
        finally:
            await cli_instance.close()

    asyncio.run(run())


@cli.command()
@click.option("--token", required=True, help="Access token to validate")
def validate(token: str):
    """Validate an access token."""

    async def run():
        cli_instance = UserCLI()
        try:
            await cli_instance.validate_token(token)
        finally:
            await cli_instance.close()

    asyncio.run(run())


@cli.command()
@click.option("--user-id", required=True, help="User ID")
@click.option("--token-hours", default=24, help="Token validity in hours (default: 24)")
def refresh_token(user_id: str, token_hours: int):
    """Refresh a user's access token."""

    async def run():
        cli_instance = UserCLI()
        try:
            await cli_instance.refresh_token(user_id, token_hours)
        finally:
            await cli_instance.close()

    asyncio.run(run())


@cli.command()
@click.option("--user-id", required=True, help="User ID")
@click.option("--question", required=True, help="Question text")
@click.option("--answer", required=True, help="Answer text")
def add_qa(user_id: str, question: str, answer: str):
    """Add a Q/A pair to user's history."""

    async def run():
        cli_instance = UserCLI()
        try:
            await cli_instance.add_qa(user_id, question, answer)
        finally:
            await cli_instance.close()

    asyncio.run(run())


@cli.command()
@click.option("--user-id", required=True, help="User ID")
def history(user_id: str):
    """Show user's Q/A history."""

    async def run():
        cli_instance = UserCLI()
        try:
            await cli_instance.show_history(user_id)
        finally:
            await cli_instance.close()

    asyncio.run(run())


@cli.command()
@click.option("--user-id", required=True, help="User ID")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def delete(user_id: str, confirm: bool):
    """Delete a user."""
    if not confirm:
        if not click.confirm(f"Are you sure you want to delete user {user_id}?"):
            click.echo("Operation cancelled.")
            return

    async def run():
        cli_instance = UserCLI()
        try:
            await cli_instance.delete_user(user_id)
        finally:
            await cli_instance.close()

    asyncio.run(run())


@cli.command()
@click.option(
    "--limit", default=50, help="Maximum number of users to list (default: 50)"
)
@click.option("--skip", default=0, help="Number of users to skip (default: 0)")
def list_users(limit: int, skip: int):
    """List all users."""

    async def run():
        cli_instance = UserCLI()
        try:
            await cli_instance.list_users(limit, skip)
        finally:
            await cli_instance.close()

    asyncio.run(run())


if __name__ == "__main__":
    cli()
