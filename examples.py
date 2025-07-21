#!/usr/bin/env python3
"""
Example usage scripts for the Jira to GitHub migration tool
"""

import os
import subprocess
import sys
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
PYTHON_PATH = SCRIPT_DIR / ".venv" / "bin" / "python"
MAIN_SCRIPT = SCRIPT_DIR / "main.py"

def run_command(cmd):
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode

def example_test_connection():
    """Test the connection to Jira and GitHub"""
    print("=" * 50)
    print("Testing connections...")
    print("=" * 50)
    return run_command([str(PYTHON_PATH), str(MAIN_SCRIPT), "test-connection"])

def example_preview_issues():
    """Preview migration of specific issues"""
    print("=" * 50)
    print("Previewing issue migration...")
    print("=" * 50)
    
    # You'll need to replace these with actual Jira issue keys
    issues = ["PROJ-123", "PROJ-124"]
    return run_command([str(PYTHON_PATH), str(MAIN_SCRIPT), "preview"] + issues)

def example_preview_with_urls():
    """Preview migration using Jira URLs"""
    print("=" * 50)
    print("Previewing issue migration using URLs...")
    print("=" * 50)
    
    # You can use full Jira URLs - issue keys will be extracted automatically
    urls = [
        "https://company.atlassian.net/browse/PROJ-123",
        "https://company.atlassian.net/browse/PROJ-124"
    ]
    return run_command([str(PYTHON_PATH), str(MAIN_SCRIPT), "preview"] + urls)

def example_dry_run_migration():
    """Run a dry-run migration"""
    print("=" * 50)
    print("Dry run migration...")
    print("=" * 50)
    
    # You'll need to replace these with actual Jira issue keys
    issues = ["PROJ-123", "PROJ-124"]
    return run_command([str(PYTHON_PATH), str(MAIN_SCRIPT), "--dry-run", "migrate"] + issues)

def example_migrate_by_jql():
    """Migrate issues using JQL"""
    print("=" * 50)
    print("Migrating by JQL (dry run)...")
    print("=" * 50)
    
    # Example JQL - replace with your own
    jql = "project = PROJ AND status = 'Done' AND created >= -30d"
    return run_command([
        str(PYTHON_PATH), str(MAIN_SCRIPT), 
        "--dry-run", "migrate-jql", jql, "--max-results", "5"
    ])

def example_migrate_project():
    """Migrate entire project"""
    print("=" * 50)
    print("Migrating entire project (dry run)...")
    print("=" * 50)
    
    # Replace with your project key
    project_key = "PROJ"
    return run_command([
        str(PYTHON_PATH), str(MAIN_SCRIPT), 
        "--dry-run", "migrate-project", project_key, "--status", "Done"
    ])

def show_config():
    """Show current configuration"""
    print("=" * 50)
    print("Current configuration...")
    print("=" * 50)
    return run_command([str(PYTHON_PATH), str(MAIN_SCRIPT), "info"])

def main():
    """Main example runner"""
    print("Jira to GitHub Migration Tool - Examples")
    print("=" * 60)
    
    # Check if .env file exists
    env_file = SCRIPT_DIR / ".env"
    if not env_file.exists():
        print("❌ No .env file found!")
        print("📝 Please copy .env.example to .env and configure your credentials")
        print("   cp .env.example .env")
        print("   # Then edit .env with your actual credentials")
        return 1
    
    # Show configuration
    if show_config() != 0:
        print("❌ Configuration error - please check your .env file")
        return 1
    
    # Test connections
    if example_test_connection() != 0:
        print("❌ Connection test failed - please check your credentials")
        return 1
    
    print("\n✅ All examples completed successfully!")
    print("\nNext steps:")
    print("1. Replace example issue keys with your actual Jira issues")
    print("2. Run preview commands first to see what would be migrated")
    print("3. Remove --dry-run flag when ready to actually migrate")
    print("\nExample commands:")
    print(f"  {PYTHON_PATH} {MAIN_SCRIPT} preview PROJ-123 PROJ-124")
    print(f"  {PYTHON_PATH} {MAIN_SCRIPT} preview https://company.atlassian.net/browse/PROJ-123")
    print(f"  {PYTHON_PATH} {MAIN_SCRIPT} --dry-run migrate PROJ-123")
    print(f"  {PYTHON_PATH} {MAIN_SCRIPT} migrate PROJ-123  # Actually migrate")
    print(f"  {PYTHON_PATH} {MAIN_SCRIPT} migrate https://company.atlassian.net/browse/PROJ-123  # Using URL")
    print(f"  {PYTHON_PATH} {MAIN_SCRIPT} --no-attachments migrate PROJ-123  # Skip attachments")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
