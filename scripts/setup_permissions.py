#!/usr/bin/env python3
"""
Script to set executable permissions on shell scripts.
Used as a PDM post-install hook.
"""

import os
import stat


def chmod_plus_x(file_path):
    """Add executable permissions to a file."""
    current = os.stat(file_path)
    os.chmod(file_path, current.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Added executable permission to {file_path}")


def setup_permissions():
    """Setup executable permissions for all script files."""
    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Define script paths
    scripts = [
        os.path.join(script_dir, "user_cli.sh"),
        os.path.join(script_dir, "admin_cli.sh"),
        os.path.join(script_dir, "setup_admin_env.sh"),
    ]

    # Set permissions
    for script in scripts:
        if os.path.exists(script):
            chmod_plus_x(script)
        else:
            print(f"Warning: Script not found: {script}")


if __name__ == "__main__":
    setup_permissions()
