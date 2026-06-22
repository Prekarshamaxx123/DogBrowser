"""
DogBrowser - Export Tools
Export security findings from DogBrowser sessions.
Part of the DogBrowser open source project (dog-browser).
"""

import json
import os
from datetime import datetime
from config.settings import APP_NAME, APP_VERSION, APP_SIGNATURE


def dogbrowser_export(response, parsed_page, security_analysis, format="json"):
    """Export DogBrowser findings to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    domain = ""
    try:
        from urllib.parse import urlparse
        domain = urlparse(response.url).netloc.replace(":", "_")
    except Exception:
        domain = "unknown"
    filename = f"dogbrowser_{domain}_{timestamp}"
    if format == "json":
        return _dogbrowser_export_json(response, parsed_page, security_analysis, filename)
    elif format == "txt":
        return _dogbrowser_export_text(response, parsed_page, security_analysis, filename)
    return None


def _dogbrowser_export_json(response, parsed_page, security_analysis, filename):
    """DogBrowser JSON export."""
    data = {
        "generator": f"{APP_NAME} v{APP_VERSION}",
        "signature": APP_SIGNATURE,
        "timestamp": datetime.now().isoformat(),
        "target": {
            "url": response.url, "final_url": response.final_url,
            "status_code": response.status_code,
            "content_type": response.content_type,
            "content_length": response.content_length,
            "elapsed_ms": response.elapsed_ms,
            "encoding": response.encoding,
        },
        "headers": {"request": response.request_headers, "response": response.response_headers},
        "cookies": response.cookies,
        "ssl": response.ssl_info,
        "redirect_chain": [
            {"status": h.status_code, "url": h.url} for h in response.redirect_chain
        ] if response.redirect_chain else [],
        "page": {
            "title": parsed_page.title if parsed_page else "",
            "links": [{"text": t, "url": u, "external": e} for t, u, e in (parsed_page.links if parsed_page else [])],
            "forms": parsed_page.forms if parsed_page else [],
            "scripts": [{"url": s[0], "inline": s[1]} for s in (parsed_page.scripts if parsed_page else [])],
            "comments": parsed_page.comments if parsed_page else [],
            "hidden_fields": parsed_page.hidden_fields if parsed_page else [],
            "parameters": parsed_page.parameters if parsed_page else {},
            "emails": parsed_page.emails if parsed_page else [],
        },
        "security": security_analysis or {},
    }
    filepath = f"{filename}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return os.path.abspath(filepath)


def _dogbrowser_export_text(response, parsed_page, security_analysis, filename):
    """DogBrowser text report export."""
    lines = [
        "=" * 70,
        f"  {APP_NAME} v{APP_VERSION} - Security Report",
        f"  {APP_SIGNATURE}",
        f"  Generated: {datetime.now().isoformat()}",
        "=" * 70, "",
        f"Target URL: {response.url}",
        f"Final URL:  {response.final_url}",
        f"Status:     {response.status_code} {response.reason}",
        f"Encoding:   {response.encoding}",
        f"Size:       {response.content_length} bytes",
        f"Time:       {response.elapsed_ms:.0f}ms", "",
    ]
    if response.redirect_chain:
        lines.append("─── Redirect Chain ───")
        for hop in response.redirect_chain:
            lines.append(f"  {hop.status_code} → {hop.url}")
        lines.append(f"  200 → {response.final_url}")
        lines.append("")
    lines.append("─── Response Headers ───")
    for k, v in response.response_headers.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    if parsed_page and parsed_page.forms:
        lines.append("─── Forms ───")
        for f in parsed_page.forms:
            lines.append(f"  {f['method']} → {f['action']}")
            for inp in f['inputs']:
                m = "🔒" if inp['hidden'] else "  "
                lines.append(f"    {m} [{inp['type']}] {inp['name']}: {inp['value']}")
        lines.append("")
    if parsed_page and parsed_page.comments:
        lines.append("─── HTML Comments ───")
        for c in parsed_page.comments:
            lines.append(f"  <!-- {c[:100]} -->")
        lines.append("")
    lines.append(f"\n{APP_SIGNATURE}")
    filepath = f"{filename}.txt"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return os.path.abspath(filepath)
