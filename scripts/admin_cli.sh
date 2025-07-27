#!/bin/bash

# Navigate to the project root
cd "$(dirname "$0")/.."

# Check if the Admin API is running
if ! curl -s http://127.0.0.1:8001/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Admin API doesn't seem to be running on port 8001"
    echo "   Please start the Admin API first:"
    echo "   python -m app.api.admin_app"
    echo ""
    echo "   Continuing anyway in case the API is running on a different port..."
    echo ""
fi

# Run the User Management CLI
python3 -m app.cli.admin_cli "$@"
