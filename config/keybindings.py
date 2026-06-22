"""
DogBrowser - Keybindings Configuration
Zellij-style keyboard shortcuts for DogBrowser terminal browser.
Part of the DogBrowser open source project.
"""

# DogBrowser Keybindings - Zellij-style shortcuts
KEYBINDINGS = {
    "navigation": {
        "ctrl+l": ("Focus URL / Search Bar", "focus_url"),
        "ctrl+r": ("Reload Page", "reload"),
        "ctrl+left": ("Go Back", "go_back"),
        "ctrl+right": ("Go Forward", "go_forward"),
        "enter": ("Follow Link / Navigate", "follow_link"),
        "escape": ("Cancel / Close Panel", "cancel"),
    },
    "scrolling": {
        "ctrl+down": ("Scroll Down", "scroll_down"),
        "ctrl+up": ("Scroll Up", "scroll_up"),
        "home": ("Go to Top", "scroll_top"),
        "end": ("Go to Bottom", "scroll_bottom"),
        "pagedown": ("Page Down", "page_down"),
        "pageup": ("Page Up", "page_up"),
    },
    "tabs": {
        "ctrl+t": ("New Tab", "new_tab"),
        "ctrl+w": ("Close Tab", "close_tab"),
    },
    "panels": {
        "f1": ("Help / Keybindings", "panel_help"),
        "f2": ("Headers Inspector", "panel_headers"),
        "f3": ("Cookies Inspector", "panel_cookies"),
        "f4": ("Forms Detector", "panel_forms"),
        "f5": ("Links Extractor", "panel_links"),
        "f6": ("JavaScript Files", "panel_js"),
        "f7": ("Page Source", "panel_source"),
        "f8": ("Tech Detection", "panel_tech"),
        "f9": ("SSL/TLS Info", "panel_ssl"),
        "f10": ("Parameters", "panel_params"),
        "f11": ("HTML Comments", "panel_comments"),
        "f12": ("Recon Tools", "panel_recon"),
    },
    "tools": {
        "ctrl+f": ("Search in Page", "search"),
        "ctrl+e": ("Export Findings", "export"),
        "ctrl+s": ("Save Page Source", "save_source"),
        "ctrl+b": ("Toggle Sidebar", "toggle_sidebar"),
        "ctrl+u": ("Cycle User-Agent", "toggle_ua"),
        "ctrl+y": ("HTTP Request Repeater", "panel_repeater"),
    },
    "application": {
        "ctrl+q": ("Quit DogBrowser", "quit_app"),
    },
}


def get_all_bindings():
    """Get flat dict of all DogBrowser keybindings."""
    result = {}
    for category, bindings in KEYBINDINGS.items():
        for key, (description, action) in bindings.items():
            result[key] = {
                "category": category,
                "description": description,
                "action": action,
            }
    return result


def get_help_text():
    """Generate formatted help text for DogBrowser keybindings."""
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║         🐕 DogBrowser - Keybindings Reference           ║")
    lines.append("║         Open Source Terminal Browser for Bug Hunters     ║")
    lines.append("╚══════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append("  DogBrowser uses Zellij-style keyboard shortcuts.")
    lines.append("  All panels toggle with F-keys (F1-F12).")
    lines.append("  Right-click on any text block, link, input, or panel to copy to clipboard.")
    lines.append("")

    for category, bindings in KEYBINDINGS.items():
        lines.append(f"  ▸ {category.upper()}")
        lines.append(f"  {'─' * 50}")
        for key, (description, _action) in bindings.items():
            key_display = key.replace("ctrl+", "Ctrl+").replace("alt+", "Alt+")
            key_display = key_display.replace("shift+", "Shift+")
            lines.append(f"    {key_display:<20} {description}")
        lines.append("")

    lines.append("  ▸ SEARCH")
    lines.append(f"  {'─' * 50}")
    lines.append("    Type a URL to navigate, or type any text to")
    lines.append("    search with Google. DogBrowser auto-detects.")
    lines.append("")
    lines.append("  Powered by DogBrowser 🐕 | Follow the developer: https://github.com/Prekarshamaxx123")
    return "\n".join(lines)
