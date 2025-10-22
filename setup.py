"""
Setup script to initialize environment and dependencies
"""
import os
import subprocess
import sys
from pathlib import Path


def create_env_file():
    """Create .env file from example"""
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if env_example.exists() and not env_file.exists():
        print("Creating .env file from .env.example...")
        with open(env_example, 'r') as example, open(env_file, 'w') as env:
            env.write(example.read())
        print("✅ .env file created. Please update it with your API keys and settings.")
        return True
    elif env_file.exists():
        print("✅ .env file already exists.")
        return False
    else:
        print("⚠️  .env.example not found.")
        return False


def install_dependencies():
    """Install Python dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✅ Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False


def setup_git():
    """Initialize git repository"""
    if not Path('.git').exists():
        print("Initializing git repository...")
        try:
            subprocess.run(['git', 'init'], check=True)
            subprocess.run(['git', 'add', '.'], check=True)
            print("✅ Git repository initialized.")
            print("💡 Run 'git commit -m \"Initial commit\"' to create your first commit.")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  Git not found or failed to initialize.")
            return False
    else:
        print("✅ Git repository already exists.")
        return False


def create_directories():
    """Create necessary directories"""
    directories = ['output', 'logs', 'templates', 'config']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Directories created.")


def main():
    """Main setup process"""
    print("🚀 Setting up News Llama...")
    print("=" * 50)
    
    # Create directories first
    create_directories()
    
    # Create .env file
    env_created = create_env_file()
    
    # Install dependencies
    deps_installed = install_dependencies()
    
    # Setup git
    git_setup = setup_git()
    
    print("\n" + "=" * 50)
    print("📋 Setup Summary:")
    print(f"   ✅ Directories created")
    print(f"   {'✅' if env_created else '📁'} .env file {'created' if env_created else 'exists'}")
    print(f"   {'✅' if deps_installed else '❌'} Dependencies {'installed' if deps_installed else 'failed'}")
    print(f"   {'✅' if git_setup else '📁'} Git repository {'initialized' if git_setup else 'exists/skipped'}")
    
    if not deps_installed:
        print("\n❌ Setup incomplete. Please install dependencies manually:")
        print("   pip install -r requirements.txt")
        return
    
    print("\n🎉 Setup complete!")
    print("\n📝 Next steps:")
    print("   1. Edit .env file with your API keys and settings")
    print("   2. Run: python main.py")
    print("   3. Or use the dev script: ./dev.sh run")
    
    if env_created:
        print("\n🔑 Don't forget to update your .env file with:")
        print("   - LLM_API_URL and LLM_MODEL")
        print("   - Twitter API keys (optional)")
        print("   - Reddit API keys (optional)")
        print("   - Web search API key (optional)")


if __name__ == "__main__":
    main()