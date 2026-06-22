"""
DogBrowser - Security Analysis Tools
Header analysis, tech detection, cookie audit for DogBrowser.
Part of the DogBrowser open source project (dog-browser).
"""

import re
from config.settings import SECURITY_HEADERS, INTERESTING_HEADERS, TECH_SIGNATURES, RECON_PATHS


def dogbrowser_analyze_security_headers(response_headers):
    """DogBrowser security header audit."""
    results = []
    headers_lower = {k.lower(): v for k, v in response_headers.items()}
    for header in SECURITY_HEADERS:
        present = header.lower() in headers_lower
        value = headers_lower.get(header.lower(), "")
        results.append({
            "header": header, "present": present,
            "value": value, "status": "✅" if present else "❌",
        })
    return results


def dogbrowser_detect_technology(response_headers, body=""):
    """DogBrowser technology fingerprinting."""
    detected = []
    headers_lower = {k.lower(): v for k, v in response_headers.items()}
    for header_name, signatures in TECH_SIGNATURES.items():
        value = headers_lower.get(header_name.lower(), "").lower()
        if value:
            for pattern, tech_name in signatures.items():
                if pattern in value:
                    detected.append({"tech": tech_name, "source": header_name, "evidence": value})
    body_lower = body.lower()
    body_checks = [
        ("wp-content", "WordPress"), ("wp-includes", "WordPress"),
        ("drupal", "Drupal"), ("joomla", "Joomla"),
        ("shopify", "Shopify"), ("squarespace", "Squarespace"),
        ("wix.com", "Wix"), ("react", "React"),
        ("angular", "Angular"), ("vue", "Vue.js"),
        ("jquery", "jQuery"), ("bootstrap", "Bootstrap"),
        ("tailwind", "Tailwind CSS"), ("laravel", "Laravel"),
        ("__next", "Next.js"), ("__nuxt", "Nuxt.js"),
        ("cloudflare", "Cloudflare"), ("recaptcha", "reCAPTCHA"),
        ("google-analytics", "Google Analytics"), ("gtag", "Google Tag Manager"),
    ]
    for pattern, tech in body_checks:
        if pattern in body_lower:
            detected.append({"tech": tech, "source": "HTML Body", "evidence": pattern})
    gen_match = re.search(r'<meta\s+name=["\']generator["\']\s+content=["\']([^"\']+)["\']', body, re.I)
    if gen_match:
        detected.append({"tech": gen_match.group(1), "source": "Meta Generator", "evidence": gen_match.group(0)[:80]})
    seen = set()
    unique = []
    for d in detected:
        if d["tech"] not in seen:
            seen.add(d["tech"])
            unique.append(d)
    return unique


def dogbrowser_find_interesting_headers(response_headers):
    """DogBrowser information leak detection."""
    results = []
    headers_lower = {k.lower(): v for k, v in response_headers.items()}
    for header in INTERESTING_HEADERS:
        value = headers_lower.get(header.lower(), "")
        if value:
            results.append({"header": header, "value": value})
    return results


def dogbrowser_analyze_cookies(cookies):
    """DogBrowser cookie security analysis."""
    results = []
    for name, info in cookies.items():
        if isinstance(info, dict):
            value = info.get("value", "")
            flags = {"secure": info.get("secure", False), "domain": info.get("domain", ""), "path": info.get("path", "/")}
        else:
            value = str(info)
            flags = {}
        issues = []
        if not flags.get("secure"):
            issues.append("Missing Secure flag")
        if len(value) > 100:
            issues.append("Large cookie (possible session token)")
        results.append({
            "name": name,
            "value": value[:50] + "..." if len(value) > 50 else value,
            "flags": flags, "issues": issues,
        })
    return results


def dogbrowser_get_recon_paths():
    """Get DogBrowser recon paths list."""
    return RECON_PATHS


def dogbrowser_extract_endpoints_from_js(js_content):
    """DogBrowser JS endpoint extractor."""
    patterns = [
        r'["\'](/api/[^"\']+)["\']',
        r'["\'](/v[0-9]+/[^"\']+)["\']',
        r'fetch\s*\(\s*["\']([^"\']+)["\']',
        r'axios\.\w+\s*\(\s*["\']([^"\']+)["\']',
        r'["\']https?://[^"\']+["\']',
    ]
    endpoints = set()
    for pattern in patterns:
        endpoints.update(re.findall(pattern, js_content))
    return sorted(endpoints)
