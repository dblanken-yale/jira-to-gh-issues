#!/usr/bin/env python3
"""
Setup script for the Jira to GitHub migration tool
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success/failure"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def setup_virtual_environment():
    """Set up virtual environment"""
    print("Setting up virtual environment...")
    
    venv_path = Path(".venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    success, output = run_command(f"{sys.executable} -m venv .venv")
    if success:
        print("✅ Virtual environment created")
        return True
    else:
        print(f"❌ Failed to create virtual environment: {output}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    
    # Get the Python executable path for the virtual environment
    if os.name == 'nt':  # Windows
        python_path = Path(".venv") / "Scripts" / "python.exe"
        pip_path = Path(".venv") / "Scripts" / "pip.exe"
    else:  # Unix/macOS
        python_path = Path(".venv") / "bin" / "python"
        pip_path = Path(".venv") / "bin" / "pip"
    
    # Upgrade pip first
    success, output = run_command(f"{pip_path} install --upgrade pip")
    if not success:
        print(f"❌ Failed to upgrade pip: {output}")
        return False
    
    # Install requirements
    success, output = run_command(f"{pip_path} install -r requirements.txt")
    if success:
        print("✅ Dependencies installed successfully")
        return True
    else:
        print(f"❌ Failed to install dependencies: {output}")
        return False

def setup_environment_file():
    """Set up environment configuration file"""
    print("Setting up environment configuration...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_example.exists():
        print("❌ .env.example file not found")
        return False
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    # Copy example file
    try:
        import shutil
        shutil.copy(env_example, env_file)
        print("✅ .env file created from template")
        print("📝 Please edit .env file with your actual credentials")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def test_tool():
    """Test that the tool works"""
    print("Testing tool installation...")
    
    if os.name == 'nt':  # Windows
        python_path = Path(".venv") / "Scripts" / "python.exe"
    else:  # Unix/macOS
        python_path = Path(".venv") / "bin" / "python"
    
    success, output = run_command(f"{python_path} main.py --help")
    if success:
        print("✅ Tool is working correctly")
        return True
    else:
        print(f"❌ Tool test failed: {output}")
        return False

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 Setup completed successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Edit the .env file with your actual credentials:")
    print("   - Jira server URL, email, and API token")
    print("   - GitHub personal access token and repository details")
    print("\n2. Test your configuration:")
    
    if os.name == 'nt':  # Windows
        python_cmd = ".venv\\Scripts\\python.exe"
    else:  # Unix/macOS
        python_cmd = ".venv/bin/python"
    
    print(f"   {python_cmd} main.py test-connection")
    print("\n3. Preview a migration:")
    print(f"   {python_cmd} main.py preview JIRA-123")
    print("\n4. Run your first migration:")
    print(f"   {python_cmd} main.py --dry-run migrate JIRA-123")
    print(f"   {python_cmd} main.py migrate JIRA-123")
    print("\n5. See all available commands:")
    print(f"   {python_cmd} main.py --help")
    print("\n📚 Check README.md for detailed usage instructions")

def main():
    """Main setup function"""
    print("Jira to GitHub Issues Migration Tool - Setup")
    print("="*50)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Setup virtual environment
    if not setup_virtual_environment():
        return 1
    
    # Install dependencies
    if not install_dependencies():
        return 1
    
    # Setup environment file
    if not setup_environment_file():
        return 1
    
    # Test the tool
    if not test_tool():
        return 1
    
    # Print next steps
    print_next_steps()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
