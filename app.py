"""
DogBrowser - Main Application (dog-browser)
Interactive terminal browser with clickable links, mouse support, and side-panel media rendering.
Part of the DogBrowser open source project (dog-browser).
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Label, Button, TextArea
from textual.containers import Horizontal, Vertical, ScrollableContainer, VerticalScroll
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from textual import work, events
from rich.text import Text
from rich.syntax import Syntax
from rich.style import Style

from browser.engine import DogBrowserEngine, DogBrowserResponse
from browser.parser import DogBrowserParser, DogBrowserPage
from browser.history import DogBrowserHistory
from tools.security import (
    dogbrowser_analyze_security_headers, dogbrowser_detect_technology,
    dogbrowser_find_interesting_headers, dogbrowser_analyze_cookies,
    dogbrowser_get_recon_paths,
)
from tools.exporter import dogbrowser_export
from tools.media import (
    is_image_url, is_video_url,
    dogbrowser_fetch_image_ansi, dogbrowser_get_video_info,
    IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
)
from config.keybindings import get_help_text
from config.settings import APP_NAME, APP_VERSION, APP_SIGNATURE


class DogLinkActivated(Message):
    def __init__(self, url, sender=None, ctrl=False):
        super().__init__()
        self.url = url
        self.sender = sender
        self.ctrl = ctrl

class DogLinkContext(Message):
    def __init__(self, url, text): super().__init__(); self.url = url; self.text = text

class DogLink(Static):
    """DogBrowser clickable link - focusable, keyboard & mouse interactive."""
    DEFAULT_CSS = """
    DogLink { height: auto; padding: 0 1; color: #00ccff; }
    DogLink:hover { background: #112233; color: #33ffcc; text-style: underline; }
    DogLink:focus { background: #0a3355; color: #00ffff; text-style: bold underline; border-left: thick $success; }
    
    DogLink.media-link { color: #ffaa00; }
    DogLink.media-link:hover { color: #ffcc55; background: #221100; text-style: underline; }
    DogLink.media-link:focus { color: #ffdd66; background: #331c00; text-style: bold underline; border-left: thick #ffaa00; }
    """
    can_focus = True

    def __init__(self, display, url, idx, **kw):
        super().__init__(display, **kw)
        self.dog_url = url
        self.dog_idx = idx
        self.dog_display = display

    def on_click(self, event):
        if event.button == 3:
            self.post_message(DogLinkContext(self.dog_url, self.dog_display))
        else:
            self.post_message(DogLinkActivated(self.dog_url, sender=self, ctrl=event.ctrl))

    def _on_key(self, event):
        if event.key == "enter":
            self.post_message(DogLinkActivated(self.dog_url, sender=self, ctrl=event.ctrl))
            event.prevent_default(); event.stop()


class DogText(Static):
    """DogBrowser non-interactive text block."""
    DEFAULT_CSS = "DogText { height: auto; padding: 0 1; }"

    def __init__(self, renderable="", **kwargs):
        super().__init__(renderable, **kwargs)
        self.dog_renderable = renderable

    def on_click(self, event):
        if event.button == 3:  # Right-click
            plain_text = self.dog_renderable.plain if hasattr(self.dog_renderable, 'plain') else str(self.dog_renderable)
            self.app.copy_to_clipboard(plain_text)
            self.app.query_one("#dog-status").update("🐕 📋 Copied text block to clipboard!")


class DogTab:
    def __init__(self, url="about:blank"):
        self.url = url
        self.history = DogBrowserHistory()
        self.dog_response = None
        self.dog_page = None
        self.dog_links = []
        self.dog_link_idx = -1

class DogPanelLog(VerticalScroll):
    """DogBrowser Side Panel container that acts like a log but mounts interactive widgets."""
    DEFAULT_CSS = """
    DogPanelLog {
        height: 1fr;
        scrollbar-size: 1 1;
    }
    """
    def clear(self):
        self.remove_children()

    def write(self, content):
        if isinstance(content, Text):
            url = None
            for start, end, span_style in content.spans:
                meta = getattr(span_style, 'meta', None)
                if meta and "@click" in meta:
                    click_action = meta["@click"]
                    if "open_tab" in click_action:
                        parts = click_action.split("'")
                        if len(parts) > 1:
                            url = parts[1]
                            break
            if url:
                link_w = DogLink(content.plain.strip(), url, 0)
                link_w.is_sidebar = True
                self.mount(link_w)
            else:
                self.mount(DogText(content))
        elif isinstance(content, str):
            self.mount(DogText(content))
        else:
            self.mount(Static(content))

    def on_click(self, event):
        if event.button == 3:  # Right-click
            if hasattr(self.app, 'current_panel_text') and self.app.current_panel_text:
                self.app.copy_to_clipboard(self.app.current_panel_text)
                self.app.query_one("#dog-status").update("🐕 📋 Panel content copied to clipboard!")

# ─── DogPanel Container ───
class DogPanel(Vertical):
    """DogBrowser Side Panel for displaying metadata, recon info, and media."""
    DEFAULT_CSS = """
    DogPanel {
        width: 55;
        border: solid $warning;
        background: #0d1117;
    }
    #dog-panel-editor {
        height: 1fr;
        display: none;
        background: #0a0e17;
        color: #00ff88;
        border: tall $accent;
    }
    """
    def compose(self) -> ComposeResult:
        yield DogPanelLog(id="dog-panel-log")
        yield TextArea(id="dog-panel-editor", show_line_numbers=True)
        yield Vertical(id="dog-panel-actions")


# ─── Main Widgets ───
class DogURLBar(Input):
    DEFAULT_CSS = """
    DogURLBar { dock: top; height: 3; border: solid $accent; }
    DogURLBar:focus { border: solid $success; }
    """

    def validate_value(self, val: str) -> str:
        if val == "about:blank":
            return ""
        return val

class DogStatus(Static):
    DEFAULT_CSS = "DogStatus { dock: bottom; height: 1; background: #111; color: #888; padding: 0 1; }"

class DogContentView(ScrollableContainer):
    DEFAULT_CSS = """
    DogContentView { height: 1fr; border: solid #223; scrollbar-size: 1 1; }
    """


def generate_random_user_agent():
    """Generates a random Android-like User-Agent string mimicking modern hardware."""
    import random
    
    model2_list = [
        "SM-G998B", "SM-G991B", "SM-G988B", "SM-G981B", "SM-G975F", "SM-G973F", "SM-N986B", "SM-N981B", 
        "SM-A525F", "SM-A725F", "SM-A325F", "SM-M315F", "SM-F926B", "SM-F711B"
    ]
    oppo_list = [
        "CPH2173", "CPH2023", "CPH2009", "CPH1907", "CPH1931", "CPH1983", "CPH2127", "CPH2207"
    ]
    realme_list = [
        "RMX2170", "RMX2001", "RMX1921", "RMX1971", "RMX3085", "RMX3241", "RMX2185", "RMX2103"
    ]
    HUAWEI_list = [
        "ANA-NX9", "ELS-NX9", "VOG-L29", "ELE-L29", "PCT-AL10", "PCT-TL10", "YAL-L21", "YAL-L41"
    ]
    
    brand_choice = random.choice(["Samsung", "Oppo", "Realme", "Huawei"])
    if brand_choice == "Samsung":
        brand = "samsung"
        model = random.choice(model2_list)
    elif brand_choice == "Oppo":
        brand = "OPPO"
        model = random.choice(oppo_list)
    elif brand_choice == "Realme":
        brand = "realme"
        model = random.choice(realme_list)
    else:
        brand = "HUAWEI"
        model = random.choice(HUAWEI_list)

    build_ids = ["SP1A.210812.016", "TP1A.220624.014", "TQ3A.230605.012", "RP1A.200720.012", "QP1A.190711.020"]
    build_device = random.choice(build_ids)
    
    fbav = f"{random.randint(300, 425)}.0.0.{random.randint(1, 88)}.{random.randint(40, 150)}"
    fbdm = f"{{density={random.randint(2, 3)}.{random.randint(2, 5)},width=1080,height={random.randint(1400, 2400)}}}"
    cpu_device = "arm64-v8a:armeabi-v7a:armeabi"
    fbbv = str(random.randint(111111111, 999999999))
    fbrv = str(random.randint(111111111, 999999999))
    fblc = random.choice(['de_DE', 'es_ES', 'en_US', 'en_GB', 'fr_FR', 'it_IT', 'pt_PT'])
    
    anv = str(random.randrange(9, 14))  # Android 9 to 13
    operators = ["Dialog,Dialog", "Mobitel,Mobitel", "Hutch,Hutch", "T-Mobile,T-Mobile", "Vodafone,Vodafone"]
    fbcr_raw = random.choice(operators)
    fbcr = fbcr_raw.split(",")[1].strip() if "," in fbcr_raw and len(fbcr_raw.split(",")) > 1 else fbcr_raw.strip()
    
    chrome_version = f"{random.randint(110, 125)}.0.{random.randint(5000, 6000)}.{random.randint(50, 150)}"
    base_ua = f"Mozilla/5.0 (Linux; Android {anv}; {model} Build/{build_device}; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_version} Mobile Safari/537.36"
    
    app_tag = f" [FBAN/FB4A;FBAV/{fbav};FBBV/{fbbv};FBDM/{fbdm};FBLC/{fblc};FBCR/{fbcr};FBMF/{brand};FBBD/{brand};FBDV/{model};FBSV/{anv};FBOP/19;FDBF/1]"
    
    return random.choice([base_ua, base_ua + app_tag])


def get_clipboard_text():
    """Gets the system clipboard text."""
    import sys
    if sys.platform.startswith('win'):
        try:
            import ctypes
            k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
            k32.GlobalLock.restype = ctypes.c_void_p
            k32.GlobalLock.argtypes = [ctypes.c_void_p]
            k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            u32.GetClipboardData.restype = ctypes.c_void_p
            u32.GetClipboardData.argtypes = [ctypes.c_uint]
            if u32.OpenClipboard(None):
                handle = u32.GetClipboardData(13)
                text = ""
                if handle:
                    ptr = k32.GlobalLock(handle)
                    if ptr:
                        text = ctypes.c_wchar_p(ptr).value or ""
                        k32.GlobalUnlock(handle)
                u32.CloseClipboard()
                if text:
                    return text
        except Exception:
            pass
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        text = r.clipboard_get()
        r.destroy()
        return text
    except Exception:
        return ""


class DogBrowserApp(App):
    """🐕 DogBrowser - Terminal Browser for Bug Hunters (dog-browser)"""

    CSS = """
    Screen { background: #0a0e17; }
    Header { background: #1a1e2e; color: #00ff88; }
    Footer { background: #1a1e2e; }
    #dog-main { height: 1fr; }
    #dog-page { width: 1fr; }
    #dog-info { dock: top; height: 1; background: #12162a; color: #7f8c9b; padding: 0 1; }
    #dog-panel-actions {
        padding: 1;
        background: #141923;
        border-top: solid #223;
        height: auto;
    }
    #dog-panel-actions Button {
        margin: 1 0;
        width: 100%;
    }
    """
    TITLE = f"🐕 {APP_NAME} v{APP_VERSION}"
    SUB_TITLE = "dog-browser | Arrow/Tab=Navigate Links | Enter=Follow | Media opens on side"

    BINDINGS = [
        Binding("ctrl+l", "focus_url", "URL", show=True),
        Binding("ctrl+r", "reload", "Reload", show=True),
        Binding("ctrl+left", "go_back", "Back", show=True),
        Binding("ctrl+right", "go_forward", "Fwd", show=True),
        Binding("ctrl+t", "new_tab", "New Tab", show=True),
        Binding("ctrl+w", "close_tab", "Close Tab", show=True),
        Binding("alt+right", "next_tab", "Next Tab", show=False),
        Binding("alt+left", "prev_tab", "Prev Tab", show=False),
        Binding("ctrl+e", "dogbrowser_export", "Export", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Panel", show=True),
        Binding("ctrl+q", "quit_app", "Quit", show=True),
        Binding("f1","panel_help","Help"), Binding("f2","panel_headers","Hdrs"),
        Binding("f3","panel_cookies","Cook"), Binding("f4","panel_forms","Form"),
        Binding("f5","panel_links","Link"), Binding("f6","panel_js","JS"),
        Binding("f7","panel_source","Src"), Binding("f8","panel_tech","Tech"),
        Binding("f9","panel_ssl","SSL"), Binding("f10","panel_params","Prm"),
        Binding("f11","panel_comments","Cmt"), Binding("f12","panel_recon","Rec"),
        Binding("tab", "next_link", "Next Link", show=False),
        Binding("shift+tab", "prev_link", "Prev Link", show=False),
        Binding("escape", "close_ctx", "Close", show=False),
        Binding("ctrl+u", "toggle_ua", "Cycle UA", show=True),
        Binding("ctrl+y", "panel_repeater", "Repeater", show=True),
        Binding("down", "scroll_down", "Scroll Down", show=False),
        Binding("up", "scroll_up", "Scroll Up", show=False),
        Binding("ctrl+down", "scroll_down", "Scroll Down", show=False),
        Binding("ctrl+up", "scroll_up", "Scroll Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("home", "scroll_top", "Home", show=False),
        Binding("end", "scroll_bottom", "End", show=False),
    ]

    sidebar_visible = reactive(False)
    current_panel = reactive("help")

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+v":
            focused = self.focused
            if isinstance(focused, (Input, TextArea)):
                text = get_clipboard_text()
                if text:
                    focused.insert_text_at_cursor(text)
                    event.prevent_default()
                    event.stop()

    # Available user agents for cycling
    USER_AGENTS = [
        ("Android Chrome (Mobile)", "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"),
        ("Random Android (Generated)", "RANDOM"),
        ("iOS Safari (Mobile)", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"),
        ("Firefox Desktop", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"),
        ("Chrome Desktop", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"),
        ("Googlebot Mobile", "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
    ]

    @property
    def current_tab(self):
        return self.tabs[self.active_tab_idx]

    @property
    def dog_response(self):
        return self.current_tab.dog_response

    @dog_response.setter
    def dog_response(self, val):
        self.current_tab.dog_response = val

    @property
    def dog_page(self):
        return self.current_tab.dog_page

    @dog_page.setter
    def dog_page(self, val):
        self.current_tab.dog_page = val

    @property
    def dog_links(self):
        return self.current_tab.dog_links

    @dog_links.setter
    def dog_links(self, val):
        self.current_tab.dog_links = val

    @property
    def dog_link_idx(self):
        return self.current_tab.dog_link_idx

    @dog_link_idx.setter
    def dog_link_idx(self, val):
        self.current_tab.dog_link_idx = val

    @property
    def history(self):
        return self.current_tab.history

    def __init__(self):
        super().__init__()
        self.engine = DogBrowserEngine()
        self.parser = DogBrowserParser()
        
        # Tabs initialization
        self.tabs = [DogTab()]
        self.active_tab_idx = 0
        
        self.ua_index = 0  # Starts at Kindle Mobile
        # Repeater request state
        self.repeater_url = "https://example.com"
        self.repeater_method = "GET"
        self.repeater_headers = "User-Agent: DogBrowser\nAccept: text/html"
        self.repeater_body = ""
        self.repeater_response_text = ""

        # Dynamic control references (to avoid DuplicateIds errors)
        self.cookie_name_input = None
        self.cookie_value_input = None
        self.cookie_domain_input = None
        self.rep_url_input = None
        self.rep_method_input = None
        self.rep_headers_input = None
        self.rep_body_input = None
        self.active_form_inputs = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield DogURLBar(placeholder="  🐕 URL, search query, or media link...", id="dog-url")
        yield Static(id="dog-tab-bar", markup=True)
        yield Label(f" 🐕 {APP_NAME} | Tab/↑↓=Links | Enter=Go | Right-Click Link=Menu | Media loads in panel", id="dog-info")
        with Horizontal(id="dog-main"):
            with Vertical(id="dog-page"):
                yield DogContentView(id="dog-view")
            yield DogPanel(id="dog-panel")
        yield DogStatus(f"🐕 {APP_SIGNATURE}", id="dog-status")
        yield Footer()

    def on_mount(self):
        self.query_one("#dog-panel").display = False
        self._update_tab_bar()
        self._dog_nav("about:blank")

    async def on_input_submitted(self, event):
        if event.input.id == "dog-url":
            t = event.value.strip()
            if t:
                url = self.engine.resolve_input(t)
                self._dog_nav(url)

    def on_click(self, event):
        if event.button == 3:  # Right-click — paste on inputs, copy elsewhere
            widget = event.widget
            if isinstance(widget, (Input, TextArea)):
                sel = getattr(widget, 'selected_text', None) or ''
                if sel.strip():
                    self.copy_to_clipboard(sel)
                    self.query_one("#dog-status").update("🐕 📋 Copied selected text to clipboard!")
                else:
                    text = get_clipboard_text()
                    if text:
                        widget.insert_text_at_cursor(text)
                        self.query_one("#dog-status").update("🐕 📋 Pasted from clipboard!")
                    else:
                        self.query_one("#dog-status").update("🐕 Clipboard is empty or inaccessible")
                event.stop()
                return

    # ─── Link Messages ───
    def on_dog_link_activated(self, msg: DogLinkActivated):
        url = msg.url
        is_sidebar = getattr(msg.sender, "is_sidebar", False)
        
        # If Ctrl key was held, open in default system browser
        if msg.ctrl:
            import webbrowser
            webbrowser.open(url)
            self.query_one("#dog-status").update(f"🐕 Opened URL in system browser: {url}")
            return

        if is_sidebar:
            self.action_new_tab(url)
            return

        if url.startswith("form-submit://"):
            from urllib.parse import urlparse, parse_qs
            try:
                parsed = urlparse(url)
                idx = int(parsed.netloc)
                qs = parse_qs(parsed.query)
                name = qs.get("name", [None])[0]
                val = qs.get("value", [None])[0]
                self._submit_form_by_index(idx, name, val)
            except Exception as e:
                self.query_one("#dog-status").update(f"❌ Form submit error: {e}")
            return

        # Check if the URL is a media URL (image or video)
        if is_image_url(url) or is_video_url(url):
            # Open in a new tab inside terminal, forcing media rendering
            self.action_new_tab(url, force_media=True)
        else:
            # Navigate standard URL in the current tab normally
            self.query_one("#dog-url").value = url
            self._dog_nav(url)

    def on_dog_link_context(self, msg: DogLinkContext):
        st = self.query_one("#dog-status")
        self.copy_to_clipboard(msg.url)
        st.update(f"🐕 📋 Link copied to clipboard: {msg.url}")
        self.query_one("#dog-url").value = msg.url

    async def on_button_pressed(self, event: Button.Pressed):
        btn = event.button
        action = getattr(btn, "action_name", btn.id)
        
        if action == "play-video" or action == "btn-play-video":
            import shutil, subprocess
            opened = False
            for player in ["mpv", "vlc", "ffplay"]:
                if shutil.which(player):
                    try:
                        subprocess.Popen([player, btn.dog_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        opened = True
                        self.query_one("#dog-status").update(f"🐕 Launched {player} for video: {btn.dog_url}")
                        break
                    except Exception:
                        pass
            if not opened:
                import webbrowser
                webbrowser.open(btn.dog_url)
                self.query_one("#dog-status").update(f"🐕 Opening video in default browser: {btn.dog_url}")
        elif action == "copy-url" or action == "btn-copy-url":
            self.query_one("#dog-url").value = btn.dog_url
            self.query_one("#dog-status").update(f"🐕 URL loaded to URL bar: {btn.dog_url}")
        elif action == "cookie-add" or action == "btn-cookie-add":
            name = self.cookie_name_input.value.strip() if self.cookie_name_input else ""
            val = self.cookie_value_input.value.strip() if self.cookie_value_input else ""
            dom = self.cookie_domain_input.value.strip() if self.cookie_domain_input else ""
            if name:
                self.engine.set_cookie(name, val, domain=dom)
                self.query_one("#dog-status").update(f"🍪 Cookie '{name}' set successfully!")
                self._dog_update_panel("cookies")
            else:
                self.query_one("#dog-status").update("❌ Cookie Name cannot be empty!")
        elif action == "cookie-clear" or action == "btn-cookie-clear":
            self.engine.clear_cookies()
            self.query_one("#dog-status").update("🍪 All cookies cleared!")
            self._dog_update_panel("cookies")
        elif action == "source-edit" or action == "btn-source-edit":
            if self.dog_response:
                self.query_one("#dog-panel-log", DogPanelLog).display = False
                editor = self.query_one("#dog-panel-editor", TextArea)
                editor.display = True
                editor.text = self.dog_response.body
                actions = self.query_one("#dog-panel-actions", Vertical)
                for child in list(actions.children):
                    child.remove()
                
                btn_apply = Button("💾 Apply & Re-render", variant="success")
                btn_apply.action_name = "source-apply"
                btn_cancel = Button("❌ Cancel", variant="error")
                btn_cancel.action_name = "source-cancel"
                
                await actions.mount(btn_apply)
                await actions.mount(btn_cancel)
                editor.focus()
        elif action == "source-apply" or action == "btn-source-apply":
            editor = self.query_one("#dog-panel-editor", TextArea)
            edited_html = editor.text
            if self.dog_response:
                self.dog_response.body = edited_html
                view = self.query_one("#dog-view")
                page, blocks = self.parser.parse_to_blocks(edited_html, self.dog_response.final_url)
                self.dog_page = page
                await view.remove_children()
                await self._dog_render_blocks(view, blocks, page, self.dog_response)
            self.query_one("#dog-panel-editor", TextArea).display = False
            self.query_one("#dog-panel-log", DogPanelLog).display = True
            self._dog_update_panel("source")
            self.query_one("#dog-status").update("📄 HTML code modified and re-rendered locally!")
        elif action == "source-cancel" or action == "btn-source-cancel":
            self.query_one("#dog-panel-editor", TextArea).display = False
            self.query_one("#dog-panel-log", DogPanelLog).display = True
            self._dog_update_panel("source")
            self.query_one("#dog-status").update("✏️ HTML edit cancelled.")
        elif action == "repeater-send" or action == "btn-repeater-send":
            url = self.rep_url_input.value.strip() if self.rep_url_input else ""
            method = self.rep_method_input.value.strip().upper() if self.rep_method_input else "GET"
            headers_str = self.rep_headers_input.value.strip() if self.rep_headers_input else ""
            body = self.rep_body_input.value if self.rep_body_input else ""
            self.repeater_url = url
            self.repeater_method = method
            self.repeater_headers = headers_str
            self.repeater_body = body
            headers = {}
            if headers_str:
                for part in headers_str.split(","):
                    if ":" in part:
                        k, v = part.split(":", 1)
                        headers[k.strip()] = v.strip()
            self._dog_repeater_send(url, method, headers, body)
        elif action == "repeater-load" or action == "btn-repeater-load":
            if hasattr(self, 'repeater_response') and self.repeater_response:
                resp = self.repeater_response
                self.dog_response = resp
                self.history.push(resp.final_url)
                self.query_one("#dog-url").value = resp.final_url
                page, blocks = self.parser.parse_to_blocks(resp.body, resp.final_url)
                self.dog_page = page
                view = self.query_one("#dog-view")
                await view.remove_children()
                await self._dog_render_blocks(view, blocks, page, resp)
                self.query_one("#dog-status").update(f"📥 Loaded repeater response: {resp.final_url}")
        elif action == "copy-panel-content" or action == "btn-copy-panel-content":
            if hasattr(self, 'current_panel_text') and self.current_panel_text:
                self.copy_to_clipboard(self.current_panel_text)
                self.query_one("#dog-status").update("🐕 📋 Panel content copied to clipboard!")
        elif action == "fill-form":
            form_idx = btn.form_idx
            self.active_form_idx = form_idx
            await self._dog_show_form_inputs(form_idx)
        elif action == "form-cancel" or action == "btn-form-cancel":
            self._dog_update_panel("forms")
        elif action == "submit-active-form" or action == "btn-submit-active-form":
            idx = getattr(self, "active_form_idx", None)
            if idx is not None and self.dog_page and idx < len(self.dog_page.forms):
                form = self.dog_page.forms[idx]
                form_data = {}
                for inp_idx, inp in enumerate(form["inputs"]):
                    if inp["hidden"]:
                        form_data[inp["name"]] = inp["value"]
                    else:
                        if self.active_form_inputs and inp_idx in self.active_form_inputs:
                            form_data[inp["name"]] = self.active_form_inputs[inp_idx].value
                        else:
                            form_data[inp["name"]] = inp["value"]
                
                action_url = form["action"]
                method = form["method"]
                if method == "GET":
                    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                    parts = list(urlparse(action_url))
                    query = parse_qs(parts[4])
                    for k, v in form_data.items():
                        query[k] = [v]
                    parts[4] = urlencode(query, doseq=True)
                    action_url = urlunparse(parts)
                    post_data = None
                else:
                    post_data = form_data
                
                self.query_one("#dog-status").update(f"🚀 Submitting Form #{idx+1}...")
                self._dog_nav(action_url, method=method, data=post_data)
                self._dog_update_panel("forms")
        elif action.startswith("submit-form-"):
            form_idx = btn.form_idx
            if self.dog_page and form_idx < len(self.dog_page.forms):
                form = self.dog_page.forms[form_idx]
                form_data = {}
                for inp_idx, inp in enumerate(form["inputs"]):
                    if inp["hidden"]:
                        form_data[inp["name"]] = inp["value"]
                    else:
                        key = (form_idx, inp_idx)
                        if self.active_form_inputs and key in self.active_form_inputs:
                            form_data[inp["name"]] = self.active_form_inputs[key].value
                        else:
                            form_data[inp["name"]] = inp["value"]
                
                action_url = form["action"]
                method = form["method"]
                if method == "GET":
                    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                    parts = list(urlparse(action_url))
                    query = parse_qs(parts[4])
                    for k, v in form_data.items():
                        query[k] = [v]
                    parts[4] = urlencode(query, doseq=True)
                    action_url = urlunparse(parts)
                    post_data = None
                else:
                    post_data = form_data
                
                self.query_one("#dog-status").update(f"🚀 Submitting Form #{form_idx+1}...")
                self._dog_nav(action_url, method=method, data=post_data)
                self._dog_update_panel("forms")
        elif action == "bang-add" or action == "btn-bang-add":
            k = self.bang_keyword_input.value.strip() if self.bang_keyword_input else ""
            u = self.bang_url_input.value.strip() if self.bang_url_input else ""
            if k and u:
                if not k.startswith("!"):
                    k = "!" + k
                self.engine.add_bang(k, u)
                self.query_one("#dog-status").update(f"⚡ Search bang '{k}' added successfully!")
                self._dog_update_panel("params")
            else:
                self.query_one("#dog-status").update("❌ Keyword and URL cannot be empty!")

    @work(exclusive=True, thread=False)
    async def _submit_form_by_index(self, idx, submit_name=None, submit_val=None):
        if not self.dog_page or idx >= len(self.dog_page.forms):
            return
        form = self.dog_page.forms[idx]
        form_data = {}
        for inp in form["inputs"]:
            name = inp.get("name")
            if not name:
                continue
            itype = inp.get("type", "").lower()
            if itype in ("submit", "image"):
                if submit_name and name == submit_name:
                    form_data[name] = submit_val or inp.get("value", "")
                continue
            form_data[name] = inp.get("value", "")
        if submit_name and submit_name not in form_data:
            form_data[submit_name] = submit_val or ""

        action_url = form["action"]
        method = form["method"]
        if method == "GET":
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parts = list(urlparse(action_url))
            query = parse_qs(parts[4])
            for k, v in form_data.items():
                query[k] = [v]
            parts[4] = urlencode(query, doseq=True)
            action_url = urlunparse(parts)
            post_data = None
        else:
            post_data = form_data
        
        self.query_one("#dog-status").update(f"🚀 Submitting Form #{idx+1}...")
        self._dog_nav(action_url, method=method, data=post_data)

    # ─── Media Side-Panel Loader ───
    @work(exclusive=True, thread=False)
    async def _load_media_to_panel(self, url):
        """Loads and processes image/video on the side panel."""
        self.sidebar_visible = True
        side = self.query_one("#dog-panel")
        side.display = True
        self.current_panel = "media"
        
        log = self.query_one("#dog-panel-log", DogPanelLog)
        actions = self.query_one("#dog-panel-actions", Vertical)
        
        log.clear()
        for child in list(actions.children):
            child.remove()
            
        log.write(Text("🐕 DogBrowser Media Loader", style="bold yellow"))
        log.write(Text(f"🔗 Resolving: {url}\n", style="dim"))
        
        if is_image_url(url):
            log.write(Text("⏳ Downloading image & converting to ANSI...", style="yellow"))
            ansi_art = await dogbrowser_fetch_image_ansi(url, target_width=45)
            log.clear()
            log.write(Text("🐕 DogBrowser Image View 📸", style="bold green"))
            log.write(Text(f"URL: {url}\n", style="dim"))
            log.write(ansi_art)
            
            # Action button
            btn = Button("Copy Image URL", variant="primary")
            btn.action_name = "copy-url"
            btn.dog_url = url
            await actions.mount(btn)
            
        elif is_video_url(url):
            log.write(Text("⏳ Fetching video info via yt-dlp...", style="yellow"))
            
            # Fetch video info in a background thread
            import asyncio
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, dogbrowser_get_video_info, url)
            
            log.clear()
            if "error" in info:
                log.write(Text(f"❌ Error loading video: {info['error']}", style="bold red"))
                log.write(Text("\nWould you like to open it in your player/browser anyway?", style="dim"))
                btn = Button("▶ Play Video", variant="success")
                btn.action_name = "play-video"
                btn.dog_url = url
                await actions.mount(btn)
                return
                
            log.write(Text("🐕 DogBrowser Video View 🎥", style="bold green"))
            log.write(Text(f"Title: {info['title']}", style="bold white"))
            log.write(Text(f"Uploader: {info['uploader']}", style="cyan"))
            
            duration = info.get('duration')
            if duration:
                mins, secs = divmod(duration, 60)
                log.write(Text(f"Duration: {mins}:{secs:02d}", style="dim"))
                
            views = info.get('view_count')
            if views:
                log.write(Text(f"Views: {views:,}", style="dim"))
                
            log.write(Text("-" * 45, style="dim"))
            
            # Load thumbnail if available
            thumb_url = info.get('thumbnail_url')
            if thumb_url:
                log.write(Text("⏳ Loading thumbnail...", style="dim yellow"))
                ansi_art = await dogbrowser_fetch_image_ansi(thumb_url, target_width=45)
                # Clear and rewrite with thumbnail included
                log.clear()
                log.write(Text("🐕 DogBrowser Video View 🎥", style="bold green"))
                log.write(Text(f"Title: {info['title']}", style="bold white"))
                log.write(Text(f"Uploader: {info['uploader']}", style="cyan"))
                if duration:
                    log.write(Text(f"Duration: {mins}:{secs:02d}", style="dim"))
                if views:
                    log.write(Text(f"Views: {views:,}", style="dim"))
                log.write(Text("-" * 45, style="dim"))
                log.write(ansi_art)
                log.write(Text("-" * 45, style="dim"))
            
            if info.get('description'):
                log.write(Text(f"Description:\n{info['description'][:200]}...", style="dim italic"))
                
            # Add play video buttons
            btn_play = Button("▶ Play Video", variant="success")
            btn_play.action_name = "play-video"
            btn_play.dog_url = url
            await actions.mount(btn_play)
            
            btn_copy = Button("Copy Video URL", variant="primary")
            btn_copy.action_name = "copy-url"
            btn_copy.dog_url = url
            await actions.mount(btn_copy)

    @work(exclusive=True, thread=False)
    async def _dog_nav(self, url, method="GET", data=None, force_media=False):
        # Extract target URL if it is a DuckDuckGo redirection link
        if "duckduckgo.com/l/?uddg=" in url:
            from urllib.parse import urlparse, parse_qs, unquote
            try:
                parsed = urlparse(url)
                qs = parse_qs(parsed.query)
                if "uddg" in qs:
                    url = unquote(qs["uddg"][0])
            except Exception:
                pass

        st = self.query_one("#dog-status")
        view = self.query_one("#dog-view")
        ub = self.query_one("#dog-url")

        # Save URL to current tab state
        self.current_tab.url = url
        self._update_tab_bar()

        if url == "about:blank":
            await view.remove_children()
            welcome = Text()
            welcome.append("\n  🐕 DogBrowser - Terminal Browser for Bug Hunters\n", style="bold cyan")
            welcome.append("  Type a URL or search query above to start.\n\n", style="cyan")
            welcome.append("  🌐 Follow Developer: https://github.com/Prekarshamaxx123\n", style="bold #00ccff")
            welcome.append("  💡 Mouse Copy/Paste: Hold Shift key while selecting or right-clicking.\n", style="#888888")
            welcome.append("  ⌨️ Keyboard Paste: Press Ctrl+V inside any input box.\n", style="#888888")
            welcome.append("\n  ⚠️  If a website fails to load, press Ctrl+U to cycle User-Agent.\n", style="#ffaa00")
            await view.mount(DogText(welcome))
            self.current_tab.dog_response = None
            self.current_tab.dog_page = None
            self.current_tab.dog_links = []
            self.current_tab.dog_link_idx = -1
            ub.value = ""
            st.update(f"🐕 {APP_SIGNATURE}")
            return

        # Check if we should render media view
        is_direct_img = False
        is_direct_vid = False
        if is_image_url(url):
            is_direct_img = True
        elif is_video_url(url):
            is_direct_vid = True

        if is_direct_img:
            await self._render_image_in_main_view(url)
            return
        elif is_direct_vid:
            await self._render_video_in_main_view(url)
            return

        st.update(f"🐕 Loading {url}...")

        # Clear old content
        await view.remove_children()
        await view.mount(DogText(Text(f"\n  🐕 Loading {url}...\n", style="bold yellow")))

        try:
            resp = await self.engine.fetch(url, method=method, data=data)
            self.dog_response = resp
            self.history.push(resp.final_url)
            ub.value = resp.final_url

            # Dynamically inspect Content-Type header to support direct raw media assets
            ct = resp.content_type.lower()
            if "image/" in ct:
                await self._render_image_in_main_view(resp.final_url)
                return
            elif "video/" in ct:
                await self._render_video_in_main_view(resp.final_url)
                return

            page, blocks = self.parser.parse_to_blocks(resp.body, resp.final_url)
            self.dog_page = page

            await view.remove_children()
            await self._dog_render_blocks(view, blocks, page, resp)

            st.update(
                f"🐕 {resp.status_code} | {resp.content_length}B | {resp.elapsed_ms:.0f}ms | "
                f"Enc:{resp.encoding} | Links:{len(page.links)} | Tab/↑↓=Nav Enter=Go"
            )
            self.title = f"🐕 {page.title or url}"
            if self.sidebar_visible:
                self._dog_update_panel(self.current_panel)
        except Exception as e:
            await view.remove_children()
            await view.mount(DogText(Text(f"\n  ❌ {e}\n", style="bold red")))
            st.update(f"❌ Error | {url}")

    async def _render_image_in_main_view(self, url):
        view = self.query_one("#dog-view")
        await view.remove_children()
        
        await view.mount(DogText(Text(f"\n  ⏳ Downloading image and converting to ANSI: {url}...\n", style="bold yellow")))
        
        try:
            ansi_art = await dogbrowser_fetch_image_ansi(url, target_width=80)
            await view.remove_children()
            
            await view.mount(DogText(Text("\n  🐕 DogBrowser Media Loader 📸", style="bold green")))
            await view.mount(DogText(Text(f"  🔗 URL: {url}\n", style="dim")))
            await view.mount(DogText(ansi_art))
            
            self.current_tab.dog_response = DogBrowserResponse(
                url=url, final_url=url, status_code=200, reason="OK",
                request_headers={}, response_headers={}, cookies={},
                body=f"<html><body><img src='{url}'></body></html>",
                content_type="image/jpeg", content_length=0, elapsed_ms=0.0
            )
            self.current_tab.dog_page = DogBrowserPage(url=url)
            self.query_one("#dog-status").update(f"📸 Image loaded successfully | {url}")
        except Exception as e:
            await view.remove_children()
            await view.mount(DogText(Text(f"\n  ❌ Error loading image: {e}\n", style="bold red")))

    async def _render_video_in_main_view(self, url):
        view = self.query_one("#dog-view")
        await view.remove_children()
        
        await view.mount(DogText(Text(f"\n  ⏳ Fetching video information via yt-dlp: {url}...\n", style="bold yellow")))
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, dogbrowser_get_video_info, url)
            
            await view.remove_children()
            if "error" in info:
                await view.mount(DogText(Text(f"\n  ❌ Error fetching video: {info['error']}\n", style="bold red")))
                btn = Button("▶ Play Video in External Player", variant="success")
                btn.action_name = "play-video"
                btn.dog_url = url
                await view.mount(btn)
                return
                
            await view.mount(DogText(Text("\n  🐕 DogBrowser YouTube/Video View 🎥", style="bold green")))
            await view.mount(DogText(Text(f"  🎬 Title: {info['title']}", style="bold white")))
            await view.mount(DogText(Text(f"  👤 Uploader: {info['uploader']}", style="cyan")))
            
            duration = info.get('duration')
            if duration:
                mins, secs = divmod(duration, 60)
                await view.mount(DogText(Text(f"  ⏳ Duration: {mins}:{secs:02d}", style="dim")))
                
            views = info.get('view_count')
            if views:
                await view.mount(DogText(Text(f"  👁 Views: {views:,}", style="dim")))
                
            await view.mount(DogText(Text("  " + "─" * 70, style="dim")))
            
            thumb_url = info.get('thumbnail_url')
            if thumb_url:
                await view.mount(DogText(Text("  ⏳ Loading video thumbnail...", style="dim yellow")))
                ansi_art = await dogbrowser_fetch_image_ansi(thumb_url, target_width=80)
                await view.remove_children()
                await view.mount(DogText(Text("\n  🐕 DogBrowser YouTube/Video View 🎥", style="bold green")))
                await view.mount(DogText(Text(f"  🎬 Title: {info['title']}", style="bold #ff3366")))
                await view.mount(DogText(Text(f"  👤 Uploader: {info['uploader']}", style="cyan")))
                if duration:
                    await view.mount(DogText(Text(f"  ⏳ Duration: {mins}:{secs:02d}", style="dim")))
                if views:
                    await view.mount(DogText(Text(f"  👁 Views: {views:,}", style="dim")))
                await view.mount(DogText(Text("  " + "─" * 70, style="dim")))
                await view.mount(DogText(ansi_art))
                await view.mount(DogText(Text("  " + "─" * 70, style="dim")))
                
            if info.get('description'):
                await view.mount(DogText(Text(f"  Description:\n{info['description'][:400]}...", style="dim italic")))
                
            btn_play = Button("▶ Play Video (Launch Player)", variant="success")
            btn_play.action_name = "play-video"
            btn_play.dog_url = url
            await view.mount(btn_play)
            
            self.current_tab.dog_response = DogBrowserResponse(
                url=url, final_url=url, status_code=200, reason="OK",
                request_headers={}, response_headers={}, cookies={},
                body=f"<html><body><h1>{info['title']}</h1></body></html>",
                content_type="text/html", content_length=0, elapsed_ms=0.0
            )
            self.current_tab.dog_page = DogBrowserPage(url=url)
            self.query_one("#dog-status").update(f"🎥 Video details loaded successfully | {url}")
        except Exception as e:
            await view.remove_children()
            await view.mount(DogText(Text(f"\n  ❌ Error rendering video page: {e}\n", style="bold red")))

    async def _dog_render_blocks(self, view, blocks, page, resp):
        """Render content blocks as interactive widgets."""
        # Page header
        hdr = []
        if page.title: hdr.append(f"📄 {page.title}")
        hdr.append(f"🔗 {resp.final_url}")
        hdr.append(f"📊 {resp.status_code} {resp.reason} | {resp.content_type} | Enc:{resp.encoding}")
        if resp.redirect_chain: hdr.append(f"🔀 {len(resp.redirect_chain)} redirect(s)")
        hdr.append("─" * 70)
        await view.mount(DogText(Text("\n".join(f"  {h}" for h in hdr), style="dim green")))

        self.dog_links = []
        self.dog_link_idx = -1
        text_buf = []
        recent_urls = []

        for btype, text, url, extra in blocks:
            if btype == "link":
                # De-duplicate consecutive identical URLs (like in search result lists)
                if url in recent_urls:
                    if text:
                        text_buf.append(f"  {text}")
                    continue

                # Flush text buffer
                if text_buf:
                    await view.mount(DogText("\n".join(text_buf)))
                    text_buf = []

                recent_urls.append(url)
                if len(recent_urls) > 4:
                    recent_urls.pop(0)

                idx = len(self.dog_links) + 1
                is_media = is_image_url(url) or is_video_url(url)
                
                # Check if it's a media URL to add prefix icon and class
                prefix = ""
                if is_media:
                    if is_image_url(url):
                        prefix = "🖼️ [IMG] "
                    else:
                        prefix = "🎥 [VIDEO] "
                
                display = f"  [{idx}] {prefix}{text}\n       → {url}"
                link_w = DogLink(display, url, idx)
                if is_media:
                    link_w.add_class("media-link")
                await view.mount(link_w)
                self.dog_links.append(link_w)
            elif btype == "heading":
                if text_buf:
                    await view.mount(DogText("\n".join(text_buf)))
                    text_buf = []
                await view.mount(DogText(Text(f"  {text}", style="bold #ff6600")))
            elif btype in ("image", "video", "audio"):
                if text_buf:
                    await view.mount(DogText("\n".join(text_buf)))
                    text_buf = []
                idx = len(self.dog_links) + 1
                icon = "🖼️" if btype == "image" else ("🎥" if btype == "video" else "🎵")
                display = f"  [{idx}] {icon} {text}\n       → {url}"
                link_w = DogLink(display, url, idx)
                link_w.add_class("media-link")
                await view.mount(link_w)
                self.dog_links.append(link_w)
            elif btype == "form":
                if text_buf:
                    await view.mount(DogText("\n".join(text_buf)))
                    text_buf = []
                await view.mount(DogText(Text(f"  {text}", style="bold #ff3366")))
            elif btype == "input":
                style = "bold red" if "hidden" in extra else "#aaa"
                text_buf.append(f"    {text}")
            elif btype == "separator":
                text_buf.append(f"  {text}" if text else "")
            else:
                text_buf.append(f"  {text}")

        if text_buf:
            await view.mount(DogText("\n".join(text_buf)))

    # ─── Link Navigation ───
    def action_next_link(self):
        if not self.dog_links: return
        self.dog_link_idx = (self.dog_link_idx + 1) % len(self.dog_links)
        self.dog_links[self.dog_link_idx].focus()
        self.dog_links[self.dog_link_idx].scroll_visible()
        self._show_link_info()

    def action_prev_link(self):
        if not self.dog_links: return
        self.dog_link_idx = (self.dog_link_idx - 1) % len(self.dog_links)
        self.dog_links[self.dog_link_idx].focus()
        self.dog_links[self.dog_link_idx].scroll_visible()
        self._show_link_info()

    def _show_link_info(self):
        if 0 <= self.dog_link_idx < len(self.dog_links):
            lk = self.dog_links[self.dog_link_idx]
            st = self.query_one("#dog-status")
            st.update(f"🐕 Link [{self.dog_link_idx+1}/{len(self.dog_links)}] → {lk.dog_url}")

    def action_close_ctx(self): 
        self.query_one("#dog-status").update(f"🐕 {APP_SIGNATURE}")

    # ─── Panel System ───
    def _dog_toggle(self, name):
        side = self.query_one("#dog-panel")
        if self.sidebar_visible and self.current_panel == name:
            side.display = False; self.sidebar_visible = False
        else:
            side.display = True; self.sidebar_visible = True
            self.current_panel = name; self._dog_update_panel(name)

    def copy_to_clipboard(self, text):
        import sys
        try:
            if sys.platform == "win32":
                import ctypes
                k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
                k32.GlobalAlloc.restype = ctypes.c_void_p
                k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
                k32.GlobalLock.restype = ctypes.c_void_p
                k32.GlobalLock.argtypes = [ctypes.c_void_p]
                k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                u32.SetClipboardData.restype = ctypes.c_void_p
                u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
                data = (text + '\0').encode('utf-16-le')
                if u32.OpenClipboard(None):
                    u32.EmptyClipboard()
                    h_mem = k32.GlobalAlloc(0x0002, len(data))
                    if h_mem:
                        p_mem = k32.GlobalLock(h_mem)
                        if p_mem:
                            ctypes.memmove(p_mem, data, len(data))
                            k32.GlobalUnlock(h_mem)
                        u32.SetClipboardData(13, h_mem)
                    u32.CloseClipboard()
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run("pbcopy", input=text, text=True, check=True)
            else:
                import subprocess
                subprocess.run("xclip -selection clipboard", shell=True, input=text, text=True, check=True)
        except Exception:
            pass

    def _dog_update_panel(self, name):
        log = self.query_one("#dog-panel-log", DogPanelLog)
        actions = self.query_one("#dog-panel-actions", Vertical)
        log.clear()
        for child in list(actions.children):
            child.remove()
            
        # Capture all written text for clipboard copying
        lines = []
        original_write = log.write
        def custom_write(content):
            if hasattr(content, "plain"):
                lines.append(content.plain)
            else:
                lines.append(str(content))
            original_write(content)
            
        log.write = custom_write
        fn = getattr(self, f"_dp_{name}", None)
        if fn: 
            fn(log)
            
        # Restore original write method
        log.write = original_write
        self.current_panel_text = "\n".join(lines)
        
        # Mount the clipboard copy button for the panel
        self.run_worker(self._mount_copy_button(actions))

    async def _mount_copy_button(self, actions):
        btn = Button("📋 Copy Panel Content", variant="primary")
        btn.action_name = "copy-panel-content"
        await actions.mount(btn)

    def _dp_help(self, p): p.write(Text(get_help_text(), style="bold cyan"))

    def _dp_headers(self, p):
        r = self.dog_response
        if not r: p.write(Text("  🐕 No page.", style="dim")); return
        p.write(Text("  ▸ REQUEST HEADERS [DogBrowser]", style="bold #ff6600"))
        for k,v in r.request_headers.items(): p.write(Text(f"  {k}: ",style="bold")+Text(v,style="#aaaaaa"))
        p.write(Text("\n  ▸ RESPONSE HEADERS [DogBrowser]", style="bold #ff6600"))
        for k,v in r.response_headers.items(): p.write(Text(f"  {k}: ",style="bold")+Text(v,style="#aaaaaa"))
        p.write(Text("\n  ▸ SECURITY AUDIT [DogBrowser]", style="bold #ff3366"))
        for x in dogbrowser_analyze_security_headers(r.response_headers):
            p.write(Text(f"  {x['status']} {x['header']}",style="bold green" if x["present"] else "bold red"))
        ih = dogbrowser_find_interesting_headers(r.response_headers)
        if ih:
            p.write(Text("\n  ▸ INFO LEAK [DogBrowser]", style="bold #ffcc00"))
            for x in ih: p.write(Text(f"  ⚠️ {x['header']}: {x['value']}",style="bold yellow"))

    def _dp_cookies(self, p):
        r = self.dog_response
        p.write(Text("  ▸ COOKIES [DogBrowser]", style="bold #ff6600"))
        if r and r.cookies:
            for c in dogbrowser_analyze_cookies(r.cookies):
                p.write(Text(f"  🍪 {c['name']}: {c['value']}",style="bold cyan"))
                for i in c["issues"]: p.write(Text(f"     ⚠️ {i}",style="bold yellow"))
        else:
            p.write(Text("  🐕 No active cookies.",style="dim"))
        actions = self.query_one("#dog-panel-actions", Vertical)
        self.run_worker(self._mount_cookie_controls(actions))

    async def _mount_cookie_controls(self, actions):
        self.cookie_name_input = Input(placeholder="Cookie Name")
        self.cookie_value_input = Input(placeholder="Cookie Value")
        self.cookie_domain_input = Input(placeholder="Domain (optional)")
        btn_add = Button("➕ Add / Set Cookie", variant="success")
        btn_add.action_name = "cookie-add"
        btn_clear = Button("❌ Clear All Cookies", variant="error")
        btn_clear.action_name = "cookie-clear"
        await actions.mount(self.cookie_name_input)
        await actions.mount(self.cookie_value_input)
        await actions.mount(self.cookie_domain_input)
        await actions.mount(btn_add)
        await actions.mount(btn_clear)

    def _dp_forms(self, p):
        pg = self.dog_page
        if not pg or not pg.forms: p.write(Text("  🐕 No forms.",style="dim")); return
        p.write(Text(f"  ▸ FORMS ({len(pg.forms)}) [DogBrowser]",style="bold #ff6600"))
        for i,f in enumerate(pg.forms,1):
            p.write(Text(f"  📋#{i} {f['method']} → {f['action']}",style="bold cyan"))
            for x in f["inputs"]:
                m="🔒" if x["hidden"] else "📝"; s="bold red" if x["hidden"] else "#cccccc"
                p.write(Text(f"    {m} [{x['type']}] {x['name']}: {x['value']}",style=s))
        actions = self.query_one("#dog-panel-actions", Vertical)
        self.run_worker(self._mount_forms_selector(actions))

    async def _mount_forms_selector(self, actions):
        pg = self.dog_page
        if not pg or not pg.forms:
            return
        
        self.active_form_inputs = {}
        for i, f in enumerate(pg.forms):
            await actions.mount(Label(Text(f"📋 Form #{i+1} ({f['method']} → {f['action']})", style="bold cyan")))
            for inp_idx, inp in enumerate(f["inputs"]):
                if not inp["hidden"]:
                    lbl = inp["name"] or f"input_{inp_idx}"
                    if inp["required"]:
                        lbl += " *"
                    await actions.mount(Label(f"  🔹 {lbl}:"))
                    is_pwd = inp["type"] == "password"
                    val = inp["value"] or ""
                    inp_w = Input(value=val, placeholder=inp["placeholder"] or inp["name"] or "value", password=is_pwd)
                    self.active_form_inputs[(i, inp_idx)] = inp_w
                    await actions.mount(inp_w)
            
            btn_sub = Button(f"🚀 Submit Form #{i+1}", variant="success")
            btn_sub.action_name = f"submit-form-{i}"
            btn_sub.form_idx = i
            await actions.mount(btn_sub)
            await actions.mount(Static("─" * 45))

    # _dog_show_form_inputs is no longer used since inputs are mounted inline in _mount_forms_selector

    def _dp_links(self, p):
        pg = self.dog_page
        if not pg or not pg.links: p.write(Text("  🐕 No links.",style="dim")); return
        ec=sum(1 for _,_,e in pg.links if e)
        p.write(Text(f"  ▸ LINKS ({len(pg.links)}) Int:{len(pg.links)-ec} Ext:{ec} [DogBrowser]",style="bold #ff6600"))
        for t,u,e in pg.links:
            icon="🌐" if e else "🔗"; s="bold yellow" if e else "#00ccff"
            p.write(Text(f"  {icon} {t}",style=s))
            p.write(Text(f"    {u}", style=Style(color="#888888", meta={"@click": f"app.open_tab('{u}')"})))

    def _dp_js(self, p):
        pg = self.dog_page
        if not pg or not pg.scripts: p.write(Text("  🐕 No JS.",style="dim")); return
        ext=[s for s in pg.scripts if not s[1]]; inl=[s for s in pg.scripts if s[1]]
        p.write(Text(f"  ▸ JS ({len(pg.scripts)}) Ext:{len(ext)} Inl:{len(inl)} [DogBrowser]",style="bold #ff6600"))
        for s in ext:
            url = s[0]
            p.write(Text(f"  📜 {url}", style=Style(color="#00ccff", meta={"@click": f"app.open_tab('{url}')"})))
        for s in inl: p.write(Text(f"  📝 {s[2][:80]}...",style="#888888"))

    def _dp_source(self, p):
        r = self.dog_response
        if not r: p.write(Text("  🐕 No page.",style="dim")); return
        p.write(Text(f"  ▸ SOURCE [DogBrowser] Enc:{r.encoding}",style="bold #ff6600"))
        try: p.write(Syntax(r.body[:8000],"html",theme="monokai",line_numbers=True,word_wrap=True))
        except: p.write(Text(r.body[:5000]))
        actions = self.query_one("#dog-panel-actions", Vertical)
        self.run_worker(self._mount_source_controls(actions))

    async def _mount_source_controls(self, actions):
        btn = Button("✏️ Edit HTML Code", variant="warning")
        btn.action_name = "source-edit"
        await actions.mount(btn)

    def _dp_tech(self, p):
        r = self.dog_response
        if not r: p.write(Text("  🐕 No page.",style="dim")); return
        p.write(Text("  ▸ TECH [DogBrowser]",style="bold #ff6600"))
        for t in dogbrowser_detect_technology(r.response_headers, r.body):
            p.write(Text(f"  🔧 {t['tech']} ({t['source']})",style="bold cyan"))

    def _dp_ssl(self, p):
        r = self.dog_response
        if not r or not r.ssl_info: p.write(Text("  🐕 No SSL.",style="dim")); return
        if "error" in r.ssl_info: p.write(Text(f"  ❌ {r.ssl_info['error']}",style="red")); return
        p.write(Text("  ▸ SSL [DogBrowser]",style="bold #ff6600"))
        for k,v in r.ssl_info.items():
            if k=="san":
                for s in v: p.write(Text(f"  • {s}",style="#00ccff"))
            else: p.write(Text(f"  {k}: {v}",style="#aaaaaa"))

    def _dp_params(self, p):
        pg = self.dog_page
        if pg and pg.parameters:
            p.write(Text(f"  ▸ URL PARAMETERS ({len(pg.parameters)}) [DogBrowser]", style="bold #ff6600"))
            for n, vs in pg.parameters.items():
                p.write(Text(f"  🔑 {n} = {', '.join(set(vs))}", style="bold cyan"))
            p.write(Text("\n" + "─" * 45 + "\n", style="dim"))
        else:
            p.write(Text("  🐕 No URL parameters on this page.\n\n", style="dim"))

        p.write(Text("  ▸ DUCKDUCKGO BANGS [DogBrowser]", style="bold #ff6600"))
        bangs = self.engine.get_bangs()
        for b, url in bangs.items():
            p.write(Text(f"  ⚡ {b} → ", style="bold yellow") + Text(url, style="#aaaaaa"))

        actions = self.query_one("#dog-panel-actions", Vertical)
        self.run_worker(self._mount_bang_controls(actions))

    async def _mount_bang_controls(self, actions):
        self.bang_keyword_input = Input(placeholder="Bang Keyword (e.g. !mybang)")
        self.bang_url_input = Input(placeholder="Search URL (e.g. https://site.com/search?q={query})")
        btn_add = Button("➕ Add Search Bang", variant="success")
        btn_add.action_name = "bang-add"
        
        await actions.mount(self.bang_keyword_input)
        await actions.mount(self.bang_url_input)
        await actions.mount(btn_add)

    def _dp_comments(self, p):
        pg = self.dog_page
        if not pg or not pg.comments: p.write(Text("  🐕 No comments.",style="dim")); return
        p.write(Text(f"  ▸ COMMENTS ({len(pg.comments)}) [DogBrowser]",style="bold #ff6600"))
        for c in pg.comments: p.write(Text(f"  💬 <!-- {c[:100]} -->",style="#ffcc00"))

    def _dp_recon(self, p):
        r = self.dog_response
        if not r: p.write(Text("  🐕 No page.",style="dim")); return
        from urllib.parse import urlparse
        base = f"{urlparse(r.final_url).scheme}://{urlparse(r.final_url).netloc}"
        p.write(Text("  ▸ RECON [DogBrowser]",style="bold #ff6600"))
        for path in dogbrowser_get_recon_paths():
            url = f"{base}{path}"
            p.write(Text(f"  📂 {url}", style=Style(color="#00ccff", meta={"@click": f"app.open_tab('{url}')"})))
        if self.dog_page and self.dog_page.emails:
            p.write(Text("\n  ▸ EMAILS",style="bold #ff6600"))
            for e in self.dog_page.emails: p.write(Text(f"  📧 {e}",style="#ffcc00"))

    def _dp_repeater(self, p):
        p.write(Text("  ⚡ HTTP REQUEST REPEATER [DogBrowser]", style="bold #00ff88"))
        p.write(Text("  Edit parameters below and press Send Request. You can edit URL, Method, Headers (comma separated Name:Value) and Body.", style="dim"))
        if hasattr(self, 'repeater_response_text') and self.repeater_response_text:
            p.write(Text("\n" + self.repeater_response_text))
        else:
            p.write(Text("\n  No request repeated yet.", style="dim"))
        actions = self.query_one("#dog-panel-actions", Vertical)
        self.run_worker(self._mount_repeater_controls(actions))

    async def _mount_repeater_controls(self, actions):
        self.rep_url_input = Input(value=self.repeater_url, placeholder="URL")
        self.rep_method_input = Input(value=self.repeater_method, placeholder="Method (GET/POST)")
        self.rep_headers_input = Input(value=self.repeater_headers, placeholder="Headers (Name:Val,Name2:Val2)")
        self.rep_body_input = Input(value=self.repeater_body, placeholder="Body (optional)")
        
        btn_send = Button("⚡ Send HTTP Request", variant="success")
        btn_send.action_name = "repeater-send"
        
        await actions.mount(self.rep_url_input)
        await actions.mount(self.rep_method_input)
        await actions.mount(self.rep_headers_input)
        await actions.mount(self.rep_body_input)
        await actions.mount(btn_send)
        
        if hasattr(self, 'repeater_response') and self.repeater_response:
            btn_load = Button("📥 Load Response in Browser", variant="primary")
            btn_load.action_name = "repeater-load"
            await actions.mount(btn_load)

    @work(exclusive=True, thread=False)
    async def _dog_repeater_send(self, url, method, headers, body):
        st = self.query_one("#dog-status")
        st.update("⚡ Sending repeated request...")
        try:
            data = body.encode('utf-8') if body else None
            resp = await self.engine.fetch(url, method=method, data=data, extra_headers=headers)
            self.repeater_response = resp
            
            lines = [
                "🐕 DogBrowser HTTP Repeater Response ⚡",
                f"URL: {resp.final_url}",
                f"Status: {resp.status_code} {resp.reason} | Time: {resp.elapsed_ms:.1f}ms",
                "\n▸ RESPONSE HEADERS:"
            ]
            for k, v in resp.response_headers.items():
                lines.append(f"  {k}: {v}")
            lines.append("\n▸ RESPONSE BODY SNIPPET:")
            lines.append(resp.body[:4000])
            self.repeater_response_text = "\n".join(lines)
            
            self._dog_update_panel("repeater")
            st.update(f"⚡ Response: {resp.status_code}")
        except Exception as e:
            self.repeater_response_text = f"❌ Error sending request: {e}"
            self._dog_update_panel("repeater")
            st.update(f"❌ Repeater Error: {e}")

    # ─── Actions ───
    def action_focus_url(self): self.query_one("#dog-url").focus()
    def action_reload(self):
        u=self.query_one("#dog-url").value
        if u: self._dog_nav(self.engine.resolve_input(u))
    def action_go_back(self):
        u=self.history.back()
        if u: self.query_one("#dog-url").value=u; self._dog_nav(u)
    def action_go_forward(self):
        u=self.history.forward()
        if u: self.query_one("#dog-url").value=u; self._dog_nav(u)
    def action_quit_app(self): self.exit()
    def action_toggle_sidebar(self):
        s=self.query_one("#dog-panel")
        if self.sidebar_visible: s.display=False; self.sidebar_visible=False
        else: s.display=True; self.sidebar_visible=True; self._dog_update_panel(self.current_panel)
    def action_dogbrowser_export(self):
        if self.dog_response:
            sec=dogbrowser_analyze_security_headers(self.dog_response.response_headers)
            path=dogbrowser_export(self.dog_response,self.dog_page,sec,"json")
            self.query_one("#dog-status").update(f"📁 Exported: {path}")

    def action_panel_help(self): self._dog_toggle("help")
    def action_panel_headers(self): self._dog_toggle("headers")
    def action_panel_cookies(self): self._dog_toggle("cookies")
    def action_panel_forms(self): self._dog_toggle("forms")
    def action_panel_links(self): self._dog_toggle("links")
    def action_panel_js(self): self._dog_toggle("js")
    def action_panel_source(self): self._dog_toggle("source")
    def action_panel_tech(self): self._dog_toggle("tech")
    def action_panel_ssl(self): self._dog_toggle("ssl")
    def action_panel_params(self): self._dog_toggle("params")
    def action_panel_comments(self): self._dog_toggle("comments")
    def action_panel_recon(self): self._dog_toggle("recon")
    def action_panel_repeater(self):
        if self.dog_response:
            self.repeater_url = self.dog_response.final_url
            self.repeater_headers = ", ".join(f"{k}:{v}" for k, v in self.dog_response.request_headers.items() if k.lower() not in ('accept-encoding', 'connection'))
        self._dog_toggle("repeater")
    def action_toggle_ua(self):
        self.ua_index = (self.ua_index + 1) % len(self.USER_AGENTS)
        name, ua = self.USER_AGENTS[self.ua_index]
        if ua == "RANDOM":
            ua = generate_random_user_agent()
            name = "Random Android (Generated)"
        self.engine.set_user_agent(ua)
        self.query_one("#dog-status").update(f"🐕 User-Agent cycled to: {name}")

    def action_scroll_down(self):
        self.query_one("#dog-view").scroll_down()
    def action_scroll_up(self):
        self.query_one("#dog-view").scroll_up()
    def action_page_down(self):
        self.query_one("#dog-view").scroll_page_down()
    def action_page_up(self):
        self.query_one("#dog-view").scroll_page_up()
    def action_scroll_top(self):
        self.query_one("#dog-view").scroll_to(y=0)
    def action_scroll_bottom(self):
        self.query_one("#dog-view").scroll_to(y=self.query_one("#dog-view").virtual_size.height)

    # ─── Tabs management actions ───
    def action_new_tab(self, url="about:blank", force_media=False):
        if len(self.tabs) >= 20:  # MAX_TABS is 20
            self.query_one("#dog-status").update("❌ Maximum number of tabs reached!")
            return
        new_tab = DogTab(url)
        self.tabs.append(new_tab)
        self.active_tab_idx = len(self.tabs) - 1
        self.query_one("#dog-url").value = url
        self._update_tab_bar()
        self._dog_nav(url, force_media=force_media)

    def action_close_tab(self):
        if len(self.tabs) <= 1:
            self.current_tab.url = "about:blank"
            self.current_tab.history.clear()
            self.current_tab.dog_response = None
            self.current_tab.dog_page = None
            self.current_tab.dog_links = []
            self.current_tab.dog_link_idx = -1
            self.query_one("#dog-url").value = "about:blank"
            self._update_tab_bar()
            self._dog_nav("about:blank")
            return
        
        self.tabs.pop(self.active_tab_idx)
        if self.active_tab_idx >= len(self.tabs):
            self.active_tab_idx = len(self.tabs) - 1
            
        active = self.current_tab
        self.query_one("#dog-url").value = active.url
        self._update_tab_bar()
        self.run_worker(self._render_active_tab())

    def action_close_tab_at(self, idx: int):
        if len(self.tabs) <= 1:
            self.action_close_tab()
            return
        
        self.tabs.pop(idx)
        if self.active_tab_idx >= len(self.tabs):
            self.active_tab_idx = len(self.tabs) - 1
        elif self.active_tab_idx > idx:
            self.active_tab_idx -= 1
            
        active = self.current_tab
        self.query_one("#dog-url").value = active.url
        self._update_tab_bar()
        self.run_worker(self._render_active_tab())

    def action_select_tab(self, idx: int):
        if 0 <= idx < len(self.tabs):
            self.active_tab_idx = idx
            active = self.current_tab
            self.query_one("#dog-url").value = active.url
            self._update_tab_bar()
            self.run_worker(self._render_active_tab())

    def action_open_tab(self, url: str):
        self.action_new_tab(url)

    def action_next_tab(self):
        self.active_tab_idx = (self.active_tab_idx + 1) % len(self.tabs)
        active = self.current_tab
        self.query_one("#dog-url").value = active.url
        self._update_tab_bar()
        self.run_worker(self._render_active_tab())

    def action_prev_tab(self):
        self.active_tab_idx = (self.active_tab_idx - 1) % len(self.tabs)
        active = self.current_tab
        self.query_one("#dog-url").value = active.url
        self._update_tab_bar()
        self.run_worker(self._render_active_tab())

    async def _render_active_tab(self):
        view = self.query_one("#dog-view")
        await view.remove_children()
        active = self.current_tab
        if active.dog_response:
            if is_image_url(active.url):
                await self._render_image_in_main_view(active.url)
            elif is_video_url(active.url):
                await self._render_video_in_main_view(active.url)
            else:
                page, blocks = self.parser.parse_to_blocks(active.dog_response.body, active.dog_response.final_url)
                active.dog_page = page
                await self._dog_render_blocks(view, blocks, page, active.dog_response)
        else:
            self._dog_nav(active.url)

    def _update_tab_bar(self):
        try:
            bar = self.query_one("#dog-tab-bar", Static)
        except Exception:
            return
        parts = []
        for i, tab in enumerate(self.tabs):
            title = "about:blank"
            if tab.dog_page and tab.dog_page.title:
                title = tab.dog_page.title
            elif tab.url != "about:blank":
                from urllib.parse import urlparse
                title = urlparse(tab.url).netloc or tab.url
            
            if len(title) > 15:
                title = title[:12] + "..."
                
            is_active = (i == self.active_tab_idx)
            
            tab_text = f" {title} "
            if is_active:
                part = Text(f"[{i+1}: {tab_text}]", style=Style(color="#00ff88", bold=True, bgcolor="#222233"))
            else:
                part = Text(f" {i+1}: {tab_text} ", style=Style(color="#888888", bgcolor="#111522", meta={"@click": f"app.select_tab({i})"}))
            parts.append(part)
            
            if is_active:
                parts.append(Text("x", style=Style(color="#ff3366", bold=True, bgcolor="#222233", meta={"@click": "app.close_tab()"})))
            else:
                parts.append(Text("x", style=Style(color="#555555", meta={"@click": f"app.close_tab_at({i})"})))
            parts.append(Text(" │ ", style=Style(color="#222233")))
            
        parts.append(Text(" + New Tab ", style=Style(color="#00ff88", bold=True, meta={"@click": "app.new_tab()"})))
        bar.update(Text.assemble(*parts))
