#!/usr/bin/env python3
"""
🐕 DogBrowser Installer and Setup Utility
Sets up virtual environment, installs dependencies, creates global command path wrappers,
and handles automated updates via Git.
"""

import os
import sys
import subprocess
import shutil
import platform
import argparse

def print_banner():
    print(r"""
    ================================================
          🐕 DogBrowser Installer & Updater
    ================================================
    """)

def check_git():
    """Check if git is installed and if the directory is a git repository."""
    if not shutil.which("git"):
        return False, "Git is not installed on this system."
    if not os.path.exists(".git"):
        return False, "Not a Git repository (no .git folder found)."
    return True, ""

def run_update():
    """Pull latest updates from Git."""
    print("[*] Checking for updates...")
    git_ok, err = check_git()
    if not git_ok:
        print(f"[-] Cannot update via Git: {err}")
        return False
        
    try:
        print("[*] Running 'git pull'...")
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, check=True)
        print("[+] Git output:")
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[-] Git pull failed: {e.stderr}")
        return False

def setup_venv():
    """Create virtual environment and install requirements."""
    venv_dir = ".venv"
    print(f"[*] Setting up virtual environment in {venv_dir}...")
    
    if not os.path.exists(venv_dir):
        try:
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            print("[+] Virtual environment created successfully.")
        except Exception as e:
            print(f"[-] Failed to create virtual environment: {e}")
            return None
    else:
        print("[+] Virtual environment already exists.")
        
    # Determine pip path
    is_windows = platform.system() == "Windows"
    if is_windows:
        pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip_path = os.path.join(venv_dir, "bin", "pip")
        python_path = os.path.join(venv_dir, "bin", "python")
        
    if not os.path.exists(pip_path):
        print(f"[-] Pip not found in virtual environment at: {pip_path}")
        return None
        
    # Upgrade pip and install requirements
    try:
        print("[*] Upgrading pip...")
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        
        requirements = "requirements.txt"
        if os.path.exists(requirements):
            print(f"[*] Installing dependencies from {requirements}...")
            subprocess.run([pip_path, "install", "-r", requirements], check=True)
            print("[+] Dependencies installed successfully.")
        else:
            print(f"[-] {requirements} not found! Cannot install dependencies.")
            return None
    except Exception as e:
        print(f"[-] Dependency installation failed: {e}")
        return None
        
    return python_path

def setup_command_shortcut():
    """Set up the 'DogBrowser' global shell/cmd command wrapper."""
    is_windows = platform.system() == "Windows"
    workspace_dir = os.path.abspath(os.getcwd())
    
    if is_windows:
        bat_path = os.path.join(workspace_dir, "DogBrowser.bat")
        print(f"[*] Creating Windows command wrapper at: {bat_path}")
        
        bat_content = f"""@echo off
setlocal
cd /d "{workspace_dir}"
call .venv\\Scripts\\activate.bat
python main.py %*
endlocal
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
            
        print("[*] Adding DogBrowser directory to User PATH environment variable...")
        try:
            # Get current User PATH
            get_cmd = '[Environment]::GetEnvironmentVariable("Path", "User")'
            res = subprocess.run(["powershell", "-Command", get_cmd], capture_output=True, text=True)
            current_path = res.stdout.strip()
            
            if workspace_dir not in current_path:
                new_path = current_path + ";" + workspace_dir
                set_cmd = f'[Environment]::SetEnvironmentVariable("Path", "{new_path}", "User")'
                subprocess.run(["powershell", "-Command", set_cmd], check=True)
                print("[+] Successfully added workspace directory to PATH.")
                print("[!] NOTE: You might need to restart your terminal for the changes to take effect.")
            else:
                print("[+] Workspace directory is already in User PATH.")
        except Exception as e:
            print(f"[-] Failed to update User PATH: {e}")
            print(f"[!] Please add {workspace_dir} to your environment PATH manually.")
            
    else:
        # Linux / macOS
        dog_bin = os.path.expanduser("~/.dogbrowser/bin")
        os.makedirs(dog_bin, exist_ok=True)
        
        wrapper_path = os.path.join(dog_bin, "DogBrowser")
        print(f"[*] Creating Unix command wrapper at: {wrapper_path}")
        
        wrapper_content = f"""#!/bin/bash
cd "{workspace_dir}"
source .venv/bin/activate
python main.py "$@"
"""
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(wrapper_content)
            
        os.chmod(wrapper_path, 0o755)
        print("[+] Created command wrapper and made it executable.")
        
        # Append to shell config files
        home = os.path.expanduser("~")
        shell_configs = [
            os.path.join(home, ".zshrc"),
            os.path.join(home, ".bashrc"),
        ]
        
        path_export = 'export PATH="$HOME/.dogbrowser/bin:$PATH"'
        
        for config_path in shell_configs:
            if os.path.exists(config_path):
                # Check if path export already exists
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if path_export not in content:
                    print(f"[*] Appending PATH export to: {config_path}")
                    with open(config_path, "a", encoding="utf-8") as f:
                        f.write(f"\n{path_export}\n")
                    print(f"[+] Appended to {os.path.basename(config_path)}")
                else:
                    print(f"[+] PATH export already exists in {os.path.basename(config_path)}")
            else:
                # Create file and write
                print(f"[*] Creating and setting PATH export in: {config_path}")
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(f"\n{path_export}\n")

def run_installation():
    """Execute complete installation flow."""
    python_path = setup_venv()
    if python_path:
        setup_command_shortcut()
        print("\n[+] DogBrowser setup completed successfully!")
        print("[+] You can now run the browser globally by typing: DogBrowser")
        return True
    else:
        print("\n[-] Installation failed. Please check errors above.")
        return False

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="DogBrowser Installer & Updater Utility")
    parser.add_argument("--install", action="store_true", help="Run full installation silently")
    parser.add_argument("--update", action="store_true", help="Update repository and dependencies")
    args = parser.parse_args()
    
    if args.install:
        run_installation()
        return
        
    if args.update:
        if run_update():
            run_installation()
        return
        
    # Interactive Menu
    print("Please select an option:")
    print("1) Install DogBrowser (Setup VirtualEnv & Commands)")
    print("2) Update DogBrowser (Git Pull & Re-install Dependencies)")
    print("3) Run DogBrowser")
    print("4) Exit")
    
    try:
        choice = input("\nEnter choice [1-4]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        sys.exit(0)
        
    if choice == "1":
        run_installation()
    elif choice == "2":
        if run_update():
            run_installation()
    elif choice == "3":
        venv_dir = ".venv"
        is_windows = platform.system() == "Windows"
        if is_windows:
            python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            python_exe = os.path.join(venv_dir, "bin", "python")
            
        if os.path.exists(python_exe):
            subprocess.run([python_exe, "main.py"])
        else:
            print("[-] Virtual environment not found. Please run installer first.")
    elif choice == "4" or not choice:
        print("Goodbye!")
    else:
        print("[-] Invalid choice.")

if __name__ == "__main__":
    main()
