#!/bin/bash
"""
Simple launcher script for the CLI.
"""

# Navigate to the project root
cd "$(dirname "$0")/.."

# Check if APP_API_TOKEN is set, if not provide helpful message
if [ -z "$APP_API_TOKEN" ] && [[ ! "$*" == *"--token"* ]] && [[ ! "$*" == *"-t"* ]]; then
    echo "💡 Tip: Set APP_API_TOKEN environment variable for authentication"
    echo "   Example: export APP_API_TOKEN=your_token_here"
    echo ""
fi

# Run the CLI
python -m app.cli.agent_cli "$@"
