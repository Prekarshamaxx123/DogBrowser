"""
DogBrowser - HTML Parser
Converts HTML to terminal-renderable content for the DogBrowser terminal browser.
Part of the DogBrowser open source project (dog-browser).
"""

import re
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup, Comment, NavigableString
from config.settings import IMAGE_EXTENSIONS, APP_SIGNATURE


class DogBrowserPage:
    """Parsed page data structure for DogBrowser."""
    def __init__(self, url=""):
        self.url = url
        self.title = ""
        self.rendered_text = ""
        self.links = []
        self.forms = []
        self.images = []
        self.scripts = []
        self.styles = []
        self.comments = []
        self.meta_tags = []
        self.headings = []
        self.parameters = {}
        self.emails = []
        self.hidden_fields = []


class DogBrowserParser:
    """
    DogBrowser HTML Parser.
    Core parser component of the dog-browser project.
    Extracts security-relevant data from HTML pages.
    """

    def __init__(self):
        self._link_index = 0

    def _preprocess_youtube_html(self, html, base_url):
        if "youtube.com" not in base_url and "youtu.be" not in base_url:
            return html
            
        import re
        import json
        import codecs
        from urllib.parse import urlparse, parse_qs
        
        # Find ytInitialData by scanning for the assignment statement
        patterns = [
            r'var\s+ytInitialData\s*=',
            r'window\["ytInitialData"\]\s*=',
            r'ytInitialData\s*=',
        ]
        
        data_str = None
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                start = m.end()
                rest = html[start:].lstrip()
                
                if not rest:
                    break
                
                # Case 1: JavaScript string with escapes: var ytInitialData = '...';
                if rest[0] in ("'", '"'):
                    quote = rest[0]
                    escaped = False
                    end = -1
                    for i, ch in enumerate(rest[1:], 1):
                        if escaped:
                            escaped = False
                            continue
                        if ch == '\\':
                            escaped = True
                            continue
                        if ch == quote:
                            end = i + 1
                            break
                    if end > 0:
                        raw_content = rest[1:end-1]
                        try:
                            data_str = codecs.decode(raw_content, 'unicode_escape')
                        except Exception:
                            data_str = raw_content
                else:
                    # Case 2: Direct JSON assignment: var ytInitialData = {...};
                    brace_count = 0
                    in_string = False
                    escaped = False
                    end = -1
                    for i, ch in enumerate(rest):
                        if escaped:
                            escaped = False
                            continue
                        if ch == '\\' and in_string:
                            escaped = True
                            continue
                        if ch == '"' and not escaped:
                            in_string = not in_string
                            continue
                        if in_string:
                            continue
                        if ch == '{':
                            brace_count += 1
                        elif ch == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    if end > 0:
                        data_str = rest[:end]
                break
        
        if not data_str:
            return html
            
        try:
            data = json.loads(data_str)
            
            def extract_video_items(d):
                items = []
                if isinstance(d, dict):
                    for k in ('videoRenderer', 'videoWithContextRenderer', 'compactVideoRenderer'):
                        if k in d:
                            items.append((k, d[k]))
                    if 'compactPlaylistRenderer' in d:
                        items.append(('compactPlaylistRenderer', d['compactPlaylistRenderer']))
                    for v in d.values():
                        items.extend(extract_video_items(v))
                elif isinstance(d, list):
                    for item in d:
                        items.extend(extract_video_items(item))
                return items
                
            def get_runs_text(obj, *keys):
                for k in keys:
                    v = obj.get(k)
                    if isinstance(v, dict):
                        if 'runs' in v and v['runs']:
                            return ''.join(r.get('text', '') for r in v['runs'])
                        if 'simpleText' in v:
                            return v['simpleText']
                return ''
                
            video_items = extract_video_items(data)
            
            # If homepage has no video data, try yt-dlp for trending
            if not video_items and 'search_query=' not in base_url and 'q=' not in base_url:
                try:
                    import yt_dlp
                    ydl = yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'no_warnings': True})
                    info = ydl.extract_info("ytsearch20:trending", download=False)
                    for entry in info.get('entries', []):
                        video_items.append(('videoRenderer', {
                            'videoId': entry.get('id', ''),
                            'title': {'runs': [{'text': entry.get('title', 'Untitled')}]},
                            'ownerText': {'runs': [{'text': entry.get('uploader', 'Unknown')}]},
                            'shortViewCountText': {'simpleText': f"{entry.get('view_count', 0):,} views" if entry.get('view_count') else ''},
                            'lengthText': {'simpleText': str(entry.get('duration', '')) if entry.get('duration') else ''},
                        }))
                except Exception:
                    pass
            
            query = ""
            if "search_query=" in base_url:
                try:
                    query = parse_qs(urlparse(base_url).query).get("search_query", [""])[0]
                except Exception:
                    pass
            elif "q=" in base_url:
                try:
                    query = parse_qs(urlparse(base_url).query).get("q", [""])[0]
                except Exception:
                    pass
                    
            title_str = f"YouTube Search: {query}" if query else "YouTube"
            
            out = []
            out.append("<!DOCTYPE html><html>")
            out.append(f"<head><title>{title_str}</title></head>")
            out.append("<body>")
            
            if query:
                out.append(f"<h1>YouTube Search Results for '{query}'</h1>")
            elif video_items:
                out.append("<h1>YouTube Trending</h1>")
            else:
                out.append("<h1>YouTube</h1>")
                
            out.append("<p>Select a video to view details, or use the search box below.</p>")
            out.append("<hr>")
            
            # Search Form
            out.append(f'<form action="https://www.youtube.com/results" method="GET">')
            out.append(f'  <input type="text" name="search_query" value="{query}" placeholder="Search YouTube...">')
            out.append('  <input type="submit" value="Search">')
            out.append('</form>')
            out.append("<hr>")
            
            if video_items:
                out.append("<ul>")
                for rtype, video in video_items:
                    if rtype == 'compactPlaylistRenderer':
                        playlist_id = video.get('playlistId', '')
                        if not playlist_id:
                            continue
                        pl_title = get_runs_text(video, 'title') or 'Untitled Playlist'
                        channel = get_runs_text(video, 'shortBylineText', 'longBylineText') or 'Unknown'
                        video_count = video.get('videoCount', '')
                        count_str = f" ({video_count})" if video_count else ""
                        url = f"https://www.youtube.com/playlist?list={playlist_id}"
                        out.append("  <li>")
                        out.append(f"    <h3><a href=\"{url}\">📋 {pl_title}{count_str}</a></h3>")
                        out.append(f"    <p>Channel: <b>{channel}</b></p>")
                        out.append("    <br>")
                        out.append("  </li>")
                        continue
                    
                    video_id = video.get('videoId')
                    if not video_id:
                        continue
                    
                    title = get_runs_text(video, 'title', 'headline')
                    if not title:
                        title = "Unknown Title"
                    
                    channel = get_runs_text(video, 'ownerText', 'longBylineText', 'shortBylineText')
                    if not channel:
                        channel = "Unknown Channel"
                    
                    views = get_runs_text(video, 'viewCountText', 'shortViewCountText') or "Unknown views"
                    duration = get_runs_text(video, 'lengthText') or ""
                    published = get_runs_text(video, 'publishedTimeText') or ""
                    
                    desc = ""
                    if 'descriptionSnippet' in video and 'runs' in video['descriptionSnippet']:
                        desc = ''.join(r.get('text', '') for r in video['descriptionSnippet']['runs'])
                    elif 'detailedMetadataSnippets' in video and video['detailedMetadataSnippets']:
                        snippet = video['detailedMetadataSnippets'][0]
                        desc = get_runs_text(snippet, 'snippetText') or ""
                    if not desc and 'description' in video:
                        desc = video['description']
                        
                    dur_str = f" ({duration})" if duration else ""
                    pub_str = f" - {published}" if published else ""
                    
                    watch_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    out.append("  <li>")
                    out.append(f"    <h3><a href=\"{watch_url}\">{title}{dur_str}</a></h3>")
                    out.append(f"    <p>Channel: <b>{channel}</b> | {views}{pub_str}</p>")
                    if desc:
                        safe_desc = desc.replace('<', '&lt;').replace('>', '&gt;')
                        out.append(f"    <p><i>{safe_desc[:200]}</i></p>")
                    out.append("    <br>")
                    out.append("  </li>")
                    
                out.append("</ul>")
            else:
                out.append("<p>No video results available. Use the search form above to find videos.</p>")
                
            out.append("</body></html>")
            return "\n".join(out)
        except Exception:
            return html

    def parse(self, html, base_url=""):
        """Parse HTML into DogBrowserPage."""
        html = self._preprocess_youtube_html(html, base_url)
        page = DogBrowserPage(url=base_url)
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("title")
        page.title = title_tag.get_text(strip=True) if title_tag else ""

        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property", "")
            content = meta.get("content", "")
            if name and content:
                page.meta_tags.append({"name": name, "content": content})

        self._link_index = 0
        seen_hrefs = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True) or href
            full_url = urljoin(base_url, href) if base_url else href
            is_external = self._is_external(base_url, full_url)
            if full_url not in seen_hrefs:
                page.links.append((text[:80], full_url, is_external))
                seen_hrefs.add(full_url)
            self._extract_params(full_url, page.parameters)

        for form in soup.find_all("form"):
            form_data = {
                "action": urljoin(base_url, form.get("action", "")),
                "method": form.get("method", "GET").upper(),
                "enctype": form.get("enctype", ""),
                "inputs": [],
            }
            for inp in form.find_all(["input", "textarea", "select"]):
                inp_data = {
                    "tag": inp.name, "name": inp.get("name", ""),
                    "type": inp.get("type", "text"), "value": inp.get("value", ""),
                    "placeholder": inp.get("placeholder", ""),
                    "hidden": inp.get("type") == "hidden",
                    "required": inp.has_attr("required"),
                }
                form_data["inputs"].append(inp_data)
                if inp_data["hidden"]:
                    page.hidden_fields.append({
                        "form_action": form_data["action"],
                        "name": inp_data["name"], "value": inp_data["value"],
                    })
            page.forms.append(form_data)

        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            full_src = urljoin(base_url, src) if base_url else src
            ext = self._get_extension(full_src)
            page.images.append((alt, full_src, ext))

        for script in soup.find_all("script"):
            src = script.get("src", "")
            if src:
                full_src = urljoin(base_url, src) if base_url else src
                page.scripts.append((full_src, False, ""))
            else:
                snippet = script.get_text(strip=True)[:200]
                if snippet:
                    page.scripts.append(("", True, snippet))

        for link in soup.find_all("link", rel="stylesheet"):
            href = link.get("href", "")
            if href:
                page.styles.append(urljoin(base_url, href) if base_url else href)

        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            text = str(comment).strip()
            if text and len(text) > 2:
                page.comments.append(text)

        for level in range(1, 7):
            for h in soup.find_all(f"h{level}"):
                text = h.get_text(strip=True)
                if text:
                    page.headings.append((level, text))

        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        page.emails = list(set(email_pattern.findall(str(soup))))

        self._extract_params(base_url, page.parameters)
        page.rendered_text = self._render_to_text(soup, base_url)
        return page

    def parse_to_blocks(self, html, base_url=""):
        """Parse HTML into interactive content blocks for DogBrowser UI.
        Returns (DogBrowserPage, list_of_blocks).
        Each block is a tuple: (type, text, url, extra).
        type: 'text','link','heading','image','form','input','separator'
        """
        html = self._preprocess_youtube_html(html, base_url)
        page = self.parse(html, base_url)
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
        blocks = []
        body = soup.find("body") or soup
        self._link_index = 0
        self._blocks_walk(body, blocks, base_url, soup)
        return page, blocks

    def _blocks_walk(self, el, blocks, base_url, soup=None):
        """Walk HTML tree producing content blocks for DogBrowser."""
        for child in el.children:
            if isinstance(child, NavigableString):
                if isinstance(child, Comment):
                    continue
                t = str(child).strip()
                if t:
                    blocks.append(("text", t, "", ""))
                continue
            tag = child.name
            if not tag or tag in ("script", "style", "noscript"):
                continue
            if tag in ("h1","h2","h3","h4","h5","h6"):
                t = child.get_text(strip=True)
                if t:
                    lv = int(tag[1])
                    pfx = "═" * (7 - lv)
                    blocks.append(("heading", f"{pfx} {t} {pfx}", "", str(lv)))
                    # If heading contains a link, also emit it as a link block
                    a_tag = child.find("a", href=True) if hasattr(child, 'find') else None
                    if a_tag:
                        href = a_tag.get("href", "")
                        a_text = a_tag.get_text(strip=True) or href
                        self._link_index += 1
                        url = urljoin(base_url, href) if base_url else href
                        blocks.append(("link", a_text[:80], url, str(self._link_index)))
            elif tag == "a":
                href = child.get("href", "")
                t = child.get_text(strip=True) or href
                self._link_index += 1
                url = urljoin(base_url, href) if base_url else href
                if "/l/?uddg=" in url or "duckduckgo.com/l/?uddg=" in url:
                    from urllib.parse import urlparse, parse_qs, unquote
                    try:
                        parsed = urlparse(url)
                        qs = parse_qs(parsed.query)
                        if "uddg" in qs:
                            url = unquote(qs["uddg"][0])
                    except Exception:
                        pass
                blocks.append(("link", t[:80], url, str(self._link_index)))
            elif tag == "img":
                src = child.get("src", "").strip()
                alt = child.get("alt", "no alt")
                if src.startswith("data:"):
                    full = "data:inline-image"
                    ext = "inline"
                else:
                    full = urljoin(base_url, src) if base_url else src
                    ext = self._get_extension(full)
                blocks.append(("image", f"[IMG:{ext}] {alt}", full, ""))
            elif tag == "video":
                src = child.get("src", "").strip()
                if not src:
                    source_tag = child.find("source")
                    if source_tag:
                        src = source_tag.get("src", "").strip()
                if src:
                    full = urljoin(base_url, src) if base_url else src
                    ext = self._get_extension(full)
                    blocks.append(("video", f"[VIDEO:{ext}]", full, ""))
            elif tag == "audio":
                src = child.get("src", "").strip()
                if not src:
                    source_tag = child.find("source")
                    if source_tag:
                        src = source_tag.get("src", "").strip()
                if src:
                    full = urljoin(base_url, src) if base_url else src
                    ext = self._get_extension(full)
                    blocks.append(("audio", f"[AUDIO:{ext}]", full, ""))
            elif tag == "p":
                start_len = len(blocks)
                self._blocks_walk(child, blocks, base_url, soup)
                if len(blocks) > start_len:
                    blocks.append(("separator", "", "", ""))
            elif tag == "li":
                start_len = len(blocks)
                self._blocks_walk(child, blocks, base_url, soup)
                if len(blocks) > start_len:
                    first_block = blocks[start_len]
                    btype, btext, burl, bextra = first_block
                    if btype in ("text", "link"):
                        if not btext.startswith("• "):
                            blocks[start_len] = (btype, f"• {btext}", burl, bextra)
            elif tag in ("ul", "ol"):
                self._blocks_walk(child, blocks, base_url, soup)
            elif tag == "br":
                blocks.append(("separator", "", "", ""))
            elif tag == "hr":
                blocks.append(("separator", "─" * 60, "", ""))
            elif tag == "form":
                act = urljoin(base_url, child.get("action", ""))
                mtd = child.get("method", "GET").upper()
                blocks.append(("form", f"[FORM] {mtd} → {act}", act, ""))
                self._blocks_walk(child, blocks, base_url, soup)
            elif tag == "input":
                it = child.get("type", "text").lower()
                nm = child.get("name", "")
                vl = child.get("value", "") or child.get("placeholder", "")
                if it in ("submit", "image"):
                    form_idx = -1
                    if soup:
                        parent = child.parent
                        while parent:
                            if parent.name == "form":
                                try:
                                    forms = list(soup.find_all("form"))
                                    form_idx = forms.index(parent)
                                except ValueError:
                                    pass
                                break
                            parent = parent.parent
                    label = child.get("value") or child.get("alt") or child.get("name") or "Submit"
                    self._link_index += 1
                    if form_idx != -1:
                        submit_url = f"form-submit://{form_idx}?name={nm}&value={vl}"
                        blocks.append(("link", f"🔘 [Submit] {label}", submit_url, str(self._link_index)))
                    else:
                        blocks.append(("text", f"🔘 [Submit] {label} (No Form)", "", ""))
                else:
                    mk = "🔒" if it == "hidden" else "📝"
                    blocks.append(("input", f"{mk} [{it}] {nm}: {vl}", "", it))
            elif tag == "textarea":
                blocks.append(("input", f"📝 [textarea] {child.get('name','')}", "", ""))
            elif tag == "select":
                nm = child.get("name", "")
                opts = [o.get_text(strip=True) for o in child.find_all("option")][:5]
                blocks.append(("input", f"📝 [select] {nm}: {', '.join(opts)}", "", ""))
            elif tag == "button":
                it = child.get("type", "submit").lower()
                nm = child.get("name", "")
                vl = child.get("value", "")
                form_idx = -1
                if soup:
                    parent = child.parent
                    while parent:
                        if parent.name == "form":
                            try:
                                forms = list(soup.find_all("form"))
                                form_idx = forms.index(parent)
                            except ValueError:
                                pass
                            break
                        parent = parent.parent
                label = child.get_text(strip=True) or "Submit"
                self._link_index += 1
                if form_idx != -1:
                    submit_url = f"form-submit://{form_idx}?name={nm}&value={vl}"
                    blocks.append(("link", f"🔘 [Submit] {label}", submit_url, str(self._link_index)))
                else:
                    blocks.append(("text", f"🔘 [Submit] {label} (No Form)", "", ""))
            elif tag == "table":
                for row in child.find_all("tr"):
                    cells = [c.get_text(strip=True)[:25] for c in row.find_all(["th","td"])]
                    if cells:
                        blocks.append(("text", " │ ".join(cells), "", "table"))
            else:
                self._blocks_walk(child, blocks, base_url, soup)

    def _render_to_text(self, soup, base_url):
        """DogBrowser text renderer."""
        lines = []
        body = soup.find("body") or soup
        self._link_index = 0
        self._walk_element(body, lines, base_url, indent=0)
        return "\n".join(lines)

    def _walk_element(self, element, lines, base_url, indent=0):
        """Walk HTML tree for DogBrowser rendering."""
        for child in element.children:
            if isinstance(child, NavigableString):
                if isinstance(child, Comment):
                    continue
                text = str(child).strip()
                if text:
                    lines.append(" " * indent + text)
                continue

            tag = child.name
            if tag is None or tag in ("script", "style", "noscript"):
                continue

            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(tag[1])
                text = child.get_text(strip=True)
                prefix = "═" * (7 - level)
                lines.append("")
                lines.append(f" {prefix} {text} {prefix}")
                lines.append("")
            elif tag == "p":
                text = child.get_text(strip=True)
                if text:
                    lines.append("")
                    words = text.split()
                    line = " " * indent
                    for word in words:
                        if len(line) + len(word) + 1 > 100:
                            lines.append(line)
                            line = " " * indent + word
                        else:
                            line += " " + word if line.strip() else " " * indent + word
                    if line.strip():
                        lines.append(line)
            elif tag == "a":
                href = child.get("href", "")
                text = child.get_text(strip=True) or href
                self._link_index += 1
                full_url = urljoin(base_url, href) if base_url else href
                lines.append(f" [{self._link_index}] {text}")
                lines.append(f"      → {full_url}")
            elif tag == "img":
                src = child.get("src", "").strip()
                alt = child.get("alt", "no alt")
                if src.startswith("data:"):
                    full_src = "data:inline-image"
                    ext = "inline"
                else:
                    full_src = urljoin(base_url, src) if base_url else src
                    ext = self._get_extension(full_src)
                lines.append(f" [IMG:{ext}] {alt}")
                lines.append(f"      → {full_src}")
            elif tag == "li":
                text = child.get_text(strip=True)
                lines.append(f" {'  ' * indent}• {text}")
            elif tag in ("ul", "ol"):
                lines.append("")
                self._walk_element(child, lines, base_url, indent + 1)
            elif tag == "table":
                self._render_table(child, lines)
            elif tag == "br":
                lines.append("")
            elif tag == "hr":
                lines.append(" " + "─" * 60)
            elif tag == "form":
                action = child.get("action", "")
                method = child.get("method", "GET").upper()
                lines.append("")
                lines.append(f" [FORM] {method} → {urljoin(base_url, action)}")
                self._walk_element(child, lines, base_url, indent + 1)
            elif tag == "input":
                itype = child.get("type", "text")
                name = child.get("name", "")
                value = child.get("value", "")
                placeholder = child.get("placeholder", "")
                display = placeholder or value or ""
                marker = "🔒" if itype == "hidden" else "📝"
                lines.append(f"  {marker} [{itype}] {name}: {display}")
            elif tag == "textarea":
                name = child.get("name", "")
                lines.append(f"  📝 [textarea] {name}")
            elif tag == "select":
                name = child.get("name", "")
                options = [o.get_text(strip=True) for o in child.find_all("option")][:5]
                lines.append(f"  📝 [select] {name}: {', '.join(options)}")
            elif tag == "button":
                text = child.get_text(strip=True) or "Submit"
                lines.append(f"  [BTN] {text}")
            else:
                self._walk_element(child, lines, base_url, indent)

    def _render_table(self, table, lines):
        lines.append("")
        rows = table.find_all("tr")
        if not rows:
            return
        table_data = []
        for row in rows:
            cells = row.find_all(["th", "td"])
            row_data = [c.get_text(strip=True)[:30] for c in cells]
            table_data.append(row_data)
        if not table_data:
            return
        max_cols = max(len(r) for r in table_data)
        col_widths = [0] * max_cols
        for row in table_data:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell), 3)
        sep = " ┼ ".join("─" * w for w in col_widths)
        for i, row in enumerate(table_data):
            padded = []
            for j in range(max_cols):
                val = row[j] if j < len(row) else ""
                padded.append(val.ljust(col_widths[j]))
            lines.append(" │ " + " │ ".join(padded) + " │")
            if i == 0:
                lines.append(" ┼─" + sep + "─┼")

    def _is_external(self, base_url, target_url):
        if not base_url or not target_url:
            return False
        try:
            return urlparse(base_url).netloc != urlparse(target_url).netloc
        except Exception:
            return False

    def _extract_params(self, url, params_dict):
        try:
            query_params = parse_qs(urlparse(url).query)
            for key, values in query_params.items():
                if key not in params_dict:
                    params_dict[key] = []
                params_dict[key].extend(values)
        except Exception:
            pass

    def _get_extension(self, url):
        try:
            path = urlparse(url).path
            if "." in path:
                return "." + path.rsplit(".", 1)[-1].lower()[:10]
            return ".unknown"
        except Exception:
            return ".unknown"
