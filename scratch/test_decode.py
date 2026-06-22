import httpx
import re
import json
from urllib.parse import urlparse, parse_qs

def test_parse(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    r = httpx.get(url, headers=headers, follow_redirects=True)
    html = r.text
    base_url = str(r.url)
    
    # 1. Match
    match = re.search(r'var ytInitialData\s*=\s*({.*?});', html)
    if not match:
        match = re.search(r'window\["ytInitialData"\]\s*=\s*({.*?});', html)
    if not match:
        match = re.search(r'ytInitialData\s*=\s*({.*?});', html)
        
    is_escaped = False
    if not match:
        match = re.search(r'var ytInitialData\s*=\s*\'((?:[^\'\\]|\\.)*)\';', html)
        if not match:
            match = re.search(r'window\["ytInitialData"\]\s*=\s*\'((?:[^\'\\]|\\.)*)\';', html)
        if not match:
            match = re.search(r'ytInitialData\s*=\s*\'((?:[^\'\\]|\\.)*)\';', html)
        if match:
            is_escaped = True
            
    if not match:
        print(f"[{url}] Failed to find ytInitialData")
        return
        
    try:
        if is_escaped:
            escaped_str = match.group(1)
            def replace_hex(m):
                return chr(int(m.group(1), 16))
            decoded_str = re.sub(r'\\x([0-9a-fA-F]{2})', replace_hex, escaped_str)
            decoded_str = decoded_str.replace('\\"', '"').replace('\\\\', '\\')
            data = json.loads(decoded_str)
        else:
            data = json.loads(match.group(1))
            
        def extract_videos(d):
            videos = []
            if isinstance(d, dict):
                if 'videoRenderer' in d:
                    videos.append(d['videoRenderer'])
                elif 'videoWithContextRenderer' in d:
                    videos.append(d['videoWithContextRenderer'])
                for k, v in d.items():
                    videos.extend(extract_videos(v))
            elif isinstance(d, list):
                for item in d:
                    videos.extend(extract_videos(item))
            return videos
            
        videos = extract_videos(data)
        print(f"[{url}] Found {len(videos)} videos.")
        
        # Test one extraction
        if videos:
            video = videos[0]
            video_id = video.get('videoId')
            
            # Title
            title = "Unknown Title"
            if 'title' in video:
                t_node = video['title']
                if 'runs' in t_node and len(t_node['runs']) > 0:
                    title = t_node['runs'][0]['text']
                elif 'accessibility' in t_node:
                    title = t_node['accessibility']['accessibilityData']['label']
            elif 'headline' in video:
                t_node = video['headline']
                if 'runs' in t_node and len(t_node['runs']) > 0:
                    title = t_node['runs'][0]['text']
                    
            print("  First Title:", title)
            print("  First Video ID:", video_id)
            
    except Exception as e:
        print(f"[{url}] Error: {e}")

test_parse("https://m.youtube.com/")
test_parse("https://m.youtube.com/results?search_query=cat")
