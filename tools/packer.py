#!/usr/bin/env python3
"""
DogBrowser Source Code Packer & Obfuscator
Symmetrically packs and unpacks core files in-place to protect from simple theft/rebranding.
"""

import os
import sys
import zlib
import base64

TARGET_FILES = [
    "app.py",
    "browser/engine.py",
    "browser/parser.py",
    "browser/history.py",
    "tools/security.py",
    "tools/media.py",
    "tools/exporter.py",
    "config/settings.py",
    "config/keybindings.py",
]

HEADER = "# PACKED BY DOGBROWSER PACKER"

def pack_file(filepath):
    if not os.path.exists(filepath):
        print(f"[-] File not found: {filepath}")
        return False
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    if content.startswith(HEADER):
        print(f"[!] Already packed: {filepath}")
        return False
        
    # Compress and encode
    compressed = zlib.compress(content.encode("utf-8"), level=9)
    encoded = base64.b64encode(compressed).decode("utf-8")
    
    packed_content = f"{HEADER}\nimport zlib, base64\nexec(zlib.decompress(base64.b64decode(b'{encoded}')))\n"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(packed_content)
    print(f"[+] Packed: {filepath}")
    return True

def unpack_file(filepath):
    if not os.path.exists(filepath):
        print(f"[-] File not found: {filepath}")
        return False
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    if not content.startswith(HEADER):
        print(f"[!] Not packed: {filepath}")
        return False
        
    # Find the base64 string
    try:
        start_idx = content.find("b'") + 2
        end_idx = content.rfind("'")
        encoded_str = content[start_idx:end_idx]
        
        compressed = base64.b64decode(encoded_str.encode("utf-8"))
        original_content = zlib.decompress(compressed).decode("utf-8")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(original_content)
        print(f"[+] Unpacked: {filepath}")
        return True
    except Exception as e:
        print(f"[-] Failed to unpack {filepath}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("DogBrowser Packer")
        print("Usage: python tools/packer.py [pack|unpack]")
        sys.exit(1)
        
    action = sys.argv[1].lower()
    if action == "pack":
        print("[*] Packing core files...")
        for filepath in TARGET_FILES:
            pack_file(filepath)
    elif action == "unpack":
        print("[*] Unpacking core files...")
        for filepath in TARGET_FILES:
            unpack_file(filepath)
    else:
        print(f"[-] Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
