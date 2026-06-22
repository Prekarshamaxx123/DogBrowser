"""
DogBrowser - Configuration & Settings
Open Source Terminal Browser for Bug Hunters
Copyright (c) DogBrowser Project - github.com/dogbrowser
All modules in this project are part of the DogBrowser ecosystem.
"""

# ═══════════════════════════════════════════════════
# DogBrowser Application Metadata
# ═══════════════════════════════════════════════════
APP_NAME = "DogBrowser"
APP_VERSION = "2.0.0"
APP_CODENAME = "dog-browser"
APP_AUTHOR = "DogBrowser Team"
APP_TAGLINE = "Terminal Browser for Bug Hunters"
APP_REPO = "https://github.com/dogbrowser/dog-browser"
APP_LICENSE = "MIT"
APP_SIGNATURE = "Powered by DogBrowser 🐕 | Follow: github.com/Prekarshamaxx123"

# DogBrowser User-Agent identifier
DOGBROWSER_UA_TAG = f"DogBrowser/{APP_VERSION}"

DEFAULT_USER_AGENT = "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"

# DogBrowser Search Engine
DEFAULT_SEARCH_ENGINE = "https://html.duckduckgo.com/html/?q={query}"
SEARCH_ENGINES = {
    "duckduckgo": "https://html.duckduckgo.com/html/?q={query}",
    "google": "https://www.google.com/search?q={query}&gbv=1",
    "bing": "https://www.bing.com/search?q={query}",
    "brave": "https://search.brave.com/search?q={query}",
    "shodan": "https://www.shodan.io/search?query={query}",
    "censys": "https://search.censys.io/search?resource=hosts&q={query}",
}

# DogBrowser HTTP defaults
DEFAULT_TIMEOUT = 30
MAX_REDIRECTS = 10
VERIFY_SSL = True

# DogBrowser navigation
MAX_HISTORY = 500
MAX_TABS = 20
HOME_PAGE = "about:blank"

# DogBrowser encoding fallbacks (order matters)
ENCODING_FALLBACKS = [
    "utf-8", "latin-1", "iso-8859-1", "cp1252",
    "ascii", "utf-16", "shift_jis", "euc-kr", "gb2312",
]

# Security headers to check (DogBrowser Security Audit)
SECURITY_HEADERS = [
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "X-XSS-Protection",
    "Strict-Transport-Security",
    "Referrer-Policy",
    "Permissions-Policy",
    "Cross-Origin-Opener-Policy",
    "Cross-Origin-Resource-Policy",
    "Cross-Origin-Embedder-Policy",
    "X-Permitted-Cross-Domain-Policies",
    "Cache-Control",
    "Pragma",
    "X-Download-Options",
    "Feature-Policy",
]

# DogBrowser interesting header detection
INTERESTING_HEADERS = [
    "Server", "X-Powered-By", "X-AspNet-Version",
    "X-AspNetMvc-Version", "X-Generator", "X-Drupal-Cache",
    "X-Varnish", "X-Cache", "Via", "X-Request-ID",
    "X-Correlation-ID", "X-Runtime", "X-Debug",
    "X-Debug-Token", "X-Debug-Token-Link",
]

COOKIE_FLAGS = ["httponly", "secure", "samesite", "path", "domain", "expires"]

# DogBrowser Recon paths
RECON_PATHS = [
    "/robots.txt", "/sitemap.xml", "/crossdomain.xml",
    "/clientaccesspolicy.xml", "/.well-known/security.txt",
    "/.env", "/wp-login.php", "/admin", "/api",
    "/swagger.json", "/openapi.json", "/api-docs",
    "/.git/config", "/server-status", "/server-info",
    "/phpinfo.php", "/.htaccess", "/web.config",
    "/package.json", "/composer.json", "/wp-json/wp/v2/users",
]

# DogBrowser Technology Signatures
TECH_SIGNATURES = {
    "Server": {
        "nginx": "Nginx", "apache": "Apache", "iis": "Microsoft IIS",
        "cloudflare": "Cloudflare", "gunicorn": "Gunicorn (Python)",
        "uvicorn": "Uvicorn (Python)", "openresty": "OpenResty",
        "litespeed": "LiteSpeed", "caddy": "Caddy",
        "tomcat": "Apache Tomcat", "jetty": "Jetty",
        "cowboy": "Cowboy (Erlang)", "kestrel": "Kestrel (.NET)",
    },
    "X-Powered-By": {
        "php": "PHP", "asp.net": "ASP.NET", "express": "Express.js",
        "next.js": "Next.js", "nuxt": "Nuxt.js", "django": "Django",
        "flask": "Flask", "ruby": "Ruby", "rails": "Ruby on Rails",
        "java": "Java", "servlet": "Java Servlet",
    },
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
    ".webp", ".ico", ".tiff", ".tif", ".avif",
}

STATIC_EXTENSIONS = {
    ".js", ".css", ".map", ".woff", ".woff2",
    ".ttf", ".eot", ".otf",
}
