"""
DogBrowser - HTTP Engine
Core HTTP engine for DogBrowser terminal browser.
Handles requests, encoding detection, SSL, redirects, and proxy support.
Part of the DogBrowser open source project (dog-browser).
"""

import httpx
import ssl
import re
import time
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from typing import Optional
from config.settings import (
    DEFAULT_USER_AGENT, DEFAULT_TIMEOUT, MAX_REDIRECTS,
    ENCODING_FALLBACKS, APP_VERSION, DOGBROWSER_UA_TAG,
    DEFAULT_SEARCH_ENGINE, SEARCH_ENGINES,
)


@dataclass
class RedirectHop:
    """DogBrowser redirect chain hop."""
    status_code: int
    url: str
    headers: dict


@dataclass
class DogBrowserResponse:
    """DogBrowser full response data for security analysis."""
    url: str
    final_url: str
    status_code: int
    reason: str
    request_headers: dict
    response_headers: dict
    cookies: dict
    body: str
    content_type: str
    content_length: int
    elapsed_ms: float
    redirect_chain: list = field(default_factory=list)
    ssl_info: Optional[dict] = None
    error: Optional[str] = None
    encoding: str = "utf-8"
    http_version: str = ""
    raw_bytes: Optional[bytes] = None


class DogBrowserEngine:
    """
    DogBrowser HTTP Engine.
    Core component of the dog-browser project.
    Handles all HTTP communication with advanced encoding support.
    """

    def __init__(self):
        self._client = None
        self._cookies = httpx.Cookies()
        self._custom_headers = {}
        self._user_agent = DEFAULT_USER_AGENT
        self._timeout = DEFAULT_TIMEOUT
        self._verify_ssl = True
        self._proxy = None
        self._follow_redirects = True
        self._max_redirects = MAX_REDIRECTS
        self._search_engine = "duckduckgo"
        self._bangs = self._load_bangs()

    def _load_bangs(self):
        import json, os
        path = os.path.join("config", "bangs.json")
        default_bangs = {
            "!g": "https://www.google.com/search?q={query}",
            "!yt": "https://www.youtube.com/results?search_query={query}",
            "!w": "https://en.wikipedia.org/w/index.php?search={query}",
            "!gh": "https://github.com/search?q={query}",
            "!github": "https://github.com/search?q={query}",
            "!so": "https://stackoverflow.com/search?q={query}",
            "!bing": "https://www.bing.com/search?q={query}",
            "!yahoo": "https://search.yahoo.com/search?p={query}"
        }
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return default_bangs
        return default_bangs

    def get_bangs(self):
        return self._bangs

    def add_bang(self, keyword, url):
        import json, os
        self._bangs[keyword] = url
        path = os.path.join("config", "bangs.json")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._bangs, f, indent=2)
        except Exception:
            pass

    async def _get_client(self):
        """Get or create DogBrowser HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                follow_redirects=False,
                timeout=httpx.Timeout(self._timeout),
                verify=self._verify_ssl,
                cookies=self._cookies,
                proxy=self._proxy,
            )
        return self._client

    def set_user_agent(self, ua):
        self._user_agent = ua

    def set_proxy(self, proxy):
        """Set proxy for DogBrowser (e.g., Burp Suite http://127.0.0.1:8080)."""
        self._proxy = proxy
        self._client = None

    def set_header(self, name, value):
        self._custom_headers[name] = value

    def set_verify_ssl(self, verify):
        self._verify_ssl = verify
        self._client = None

    def set_cookie(self, name, value, domain=""):
        self._cookies.set(name, value, domain=domain)

    def clear_cookies(self):
        self._cookies.clear()

    def set_search_engine(self, engine_name):
        """Set DogBrowser search engine."""
        if engine_name in SEARCH_ENGINES:
            self._search_engine = engine_name

    def _build_headers(self):
        """Build DogBrowser request headers."""
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        headers.update(self._custom_headers)
        return headers

    def resolve_input(self, user_input):
        """
        DogBrowser smart input resolver.
        Determines if input is a URL or search query.
        Returns the final URL to navigate to.
        """
        text = user_input.strip()
        if not text:
            return "about:blank"

        # Already a full URL
        if text.startswith(("http://", "https://", "about:")):
            return text

        # Check for manual DuckDuckGo keyword bangs (e.g., !g, !yt, !w, !gh)
        parts = text.split(maxsplit=1)
        if parts and parts[0] in self._bangs:
            bang_key = parts[0]
            search_query = parts[1] if len(parts) > 1 else ""
            from urllib.parse import quote_plus
            return self._bangs[bang_key].format(query=quote_plus(search_query))

        # Looks like a domain (has dots and no spaces)
        if " " not in text and "." in text:
            # Check for common TLDs or IP-like patterns
            if re.match(r'^[\w\-]+\.[\w\.\-]+', text):
                return "https://" + text

        # localhost or IP
        if text.startswith("localhost") or re.match(r'^\d+\.\d+\.\d+\.\d+', text):
            return "http://" + text

        # It's a search query - use DogBrowser search
        engine_url = SEARCH_ENGINES.get(self._search_engine, DEFAULT_SEARCH_ENGINE)
        from urllib.parse import quote_plus
        return engine_url.format(query=quote_plus(text))

    async def fetch(self, url, method="GET", data=None, json_data=None, extra_headers=None):
        """
        DogBrowser fetch - navigate to URL with full response capture.
        Handles encoding, compression, redirects, and SSL.
        """
        if url.startswith("about:"):
            return DogBrowserResponse(
                url=url, final_url=url, status_code=200, reason="OK",
                request_headers={}, response_headers={}, cookies={},
                body=self._about_page(url), content_type="text/html",
                content_length=0, elapsed_ms=0.0,
            )

        client = await self._get_client()
        headers = self._build_headers()
        if extra_headers:
            headers.update(extra_headers)

        redirect_chain = []
        current_url = url
        start_time = time.time()

        try:
            for _ in range(self._max_redirects + 1):
                if method.upper() == "POST":
                    response = await client.post(current_url, headers=headers, data=data, json=json_data)
                else:
                    response = await client.get(current_url, headers=headers)

                if response.is_redirect and self._follow_redirects:
                    redirect_chain.append(RedirectHop(
                        status_code=response.status_code,
                        url=current_url,
                        headers=dict(response.headers),
                    ))
                    location = response.headers.get("location", "")
                    current_url = urljoin(current_url, location)
                    # Standard HTTP: convert POST to GET on 301/302/303 redirects
                    if response.status_code in (301, 302, 303):
                        method = "GET"
                        data = None
                        json_data = None
                    continue

                elapsed = (time.time() - start_time) * 1000

                # DogBrowser encoding detection & decoding
                raw_bytes = response.content
                detected_encoding = self._detect_encoding(response)
                body_text = self._decode_body(raw_bytes, detected_encoding)

                # Extract cookies
                cookies = {}
                for c in client.cookies.jar:
                    cookies[c.name] = {
                        "value": c.value, "domain": c.domain,
                        "path": c.path, "secure": c.secure,
                    }
                for key, val in response.cookies.items():
                    cookies[key] = {"value": val}

                # SSL info for HTTPS
                ssl_info = None
                parsed = urlparse(current_url)
                if parsed.scheme == "https":
                    ssl_info = await self._get_ssl_info(parsed.hostname, parsed.port or 443)

                return DogBrowserResponse(
                    url=url, final_url=str(response.url),
                    status_code=response.status_code,
                    reason=response.reason_phrase or "",
                    request_headers=dict(headers),
                    response_headers=dict(response.headers),
                    cookies=cookies, body=body_text,
                    content_type=response.headers.get("content-type", ""),
                    content_length=len(raw_bytes),
                    elapsed_ms=elapsed, redirect_chain=redirect_chain,
                    ssl_info=ssl_info,
                    http_version=str(response.http_version),
                    encoding=detected_encoding,
                    raw_bytes=raw_bytes,
                )

            elapsed = (time.time() - start_time) * 1000
            return DogBrowserResponse(
                url=url, final_url=current_url, status_code=0,
                reason="Too many redirects",
                request_headers=dict(headers), response_headers={},
                cookies={},
                body="<h1>DogBrowser Error: Too many redirects</h1>",
                content_type="text/html", content_length=0,
                elapsed_ms=elapsed, redirect_chain=redirect_chain,
                error=f"DogBrowser: Max redirects ({self._max_redirects})",
            )
        except httpx.ConnectError as e:
            return self._error_response(url, headers, start_time, "Connection Error", e)
        except httpx.TimeoutException as e:
            return self._error_response(url, headers, start_time, "Timeout", e)
        except Exception as e:
            return self._error_response(url, headers, start_time, "Error", e)

    def _error_response(self, url, headers, start_time, reason, error):
        """Generate DogBrowser error response."""
        elapsed = (time.time() - start_time) * 1000
        return DogBrowserResponse(
            url=url, final_url=url, status_code=0, reason=reason,
            request_headers=dict(headers), response_headers={}, cookies={},
            body=f"<h1>DogBrowser - {reason}</h1><p>{error}</p>",
            content_type="text/html", content_length=0,
            elapsed_ms=elapsed, error=str(error),
        )

    def _detect_encoding(self, response):
        """
        DogBrowser smart encoding detection.
        1. Check Content-Type charset
        2. Check BOM
        3. Use chardet
        4. Fallback to httpx detection
        """
        # 1. From Content-Type header
        ct = response.headers.get("content-type", "")
        charset_match = re.search(r'charset=([^\s;]+)', ct, re.I)
        if charset_match:
            charset = charset_match.group(1).strip('"\'')
            return charset

        # 2. Check HTML meta charset
        raw = response.content[:4096]
        meta_match = re.search(rb'<meta[^>]+charset=["\']?([^"\'\s;>]+)', raw, re.I)
        if meta_match:
            return meta_match.group(1).decode("ascii", errors="ignore")

        # 3. Check BOM
        if raw.startswith(b'\xef\xbb\xbf'):
            return "utf-8-sig"
        if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
            return "utf-16"

        # 4. Use chardet
        try:
            import chardet
            result = chardet.detect(raw)
            if result and result.get("encoding") and result.get("confidence", 0) > 0.5:
                return result["encoding"]
        except Exception:
            pass

        # 5. Fallback
        return response.encoding or "utf-8"

    def _decode_body(self, raw_bytes, encoding):
        """
        DogBrowser body decoder with fallback chain.
        Tries detected encoding first, then falls through alternatives.
        """
        if not raw_bytes:
            return ""

        # Try detected encoding first
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            pass

        # Try fallback encodings
        for enc in ENCODING_FALLBACKS:
            try:
                return raw_bytes.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue

        # Last resort: decode with replacement
        return raw_bytes.decode("utf-8", errors="replace")

    async def _get_ssl_info(self, hostname, port=443):
        """Get SSL certificate info for DogBrowser SSL panel."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            def _fetch_cert():
                import socket
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with socket.create_connection((hostname, port), timeout=10) as sock:
                    with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert(binary_form=True)
                        cipher = ssock.cipher()
                        version = ssock.version()
                        from cryptography import x509
                        from cryptography.hazmat.backends import default_backend
                        parsed = x509.load_der_x509_certificate(cert, default_backend())
                        san = []
                        try:
                            ext = parsed.extensions.get_extension_for_class(x509.SubjectAlternativeName)
                            san = ext.value.get_values_for_type(x509.DNSName)
                        except Exception:
                            pass
                        return {
                            "subject": str(parsed.subject),
                            "issuer": str(parsed.issuer),
                            "serial": str(parsed.serial_number),
                            "not_before": str(parsed.not_valid_before_utc),
                            "not_after": str(parsed.not_valid_after_utc),
                            "version": version,
                            "cipher": cipher[0] if cipher else "?",
                            "cipher_bits": cipher[2] if cipher and len(cipher) > 2 else 0,
                            "san": san,
                        }
            return await loop.run_in_executor(None, _fetch_cert)
        except Exception as e:
            return {"error": str(e)}

    def _about_page(self, url):
        """DogBrowser about: pages."""
        if url == "about:blank":
            return """<html><body>
<h1>🐕 DogBrowser v2.0</h1>
<h2>Terminal Browser for Bug Hunters</h2>
<p>Follow the developer: <a href="https://github.com/Prekarshamaxx123">github.com/Prekarshamaxx123</a></p>
<p>Press Ctrl+L to enter a URL or search query.</p>
<h3>Quick Start:</h3>
<ul>
<li>Type a URL to navigate, or type text to search Google</li>
<li>F1 - Keybindings Help</li>
<li>F2 - Headers Inspector</li>
<li>F3 - Cookie Inspector</li>
<li>F4 - Form Detector</li>
<li>F5 - Link Extractor</li>
<li>F6 - JavaScript Files</li>
<li>F7 - Page Source</li>
<li>F8 - Technology Detection</li>
<li>F9 - SSL/TLS Info</li>
<li>F10 - URL Parameters</li>
<li>F11 - HTML Comments</li>
<li>F12 - Recon Tools</li>
</ul>
<p>Ctrl+B Toggle Sidebar | Ctrl+E Export | Ctrl+Q Quit</p>
<p>Powered by DogBrowser - Open Source Terminal Browser</p>
</body></html>"""
        return f"<html><body><h1>DogBrowser - {url}</h1></body></html>"

    async def close(self):
        """Shutdown DogBrowser engine."""
        if self._client:
            await self._client.aclose()
            self._client = None
