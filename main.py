#!/usr/bin/env python3
"""
🐕 DogBrowser - Terminal Browser for Bug Hunters
Open source project: dog-browser
Entry point for the DogBrowser application.
"""

import sys
import os

# DogBrowser path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import DogBrowserApp


def main():
    """Launch DogBrowser terminal browser."""
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    print("🐕 Starting DogBrowser...")
    app = DogBrowserApp()
    app.run()


if __name__ == "__main__":
    main()
