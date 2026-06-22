"""
DogBrowser - Media Rendering and Integration Tools
Handles downloading and converting images to ANSI blocks for terminal display,
and extracts metadata for YouTube and other video formats.
Part of the DogBrowser open source project (dog-browser).
"""

import os
import io
import asyncio
import httpx
from PIL import Image
from rich.text import Text
from rich.color import Color
from rich.style import Style

# Import yt-dlp for video metadata extraction
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# Check for common image extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico', '.tiff'}
VIDEO_DOMAINS = {'youtube.com', 'youtu.be', 'vimeo.com', 'twitch.tv'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv'}

def is_image_url(url):
    """Check if the URL points to a standard image."""
    parsed = os.path.basename(url.split('?')[0].lower())
    _, ext = os.path.splitext(parsed)
    return ext in IMAGE_EXTENSIONS

def is_video_url(url):
    """Check if the URL is an actual video file or a supported specific video player page."""
    from urllib.parse import urlparse
    try:
        parsed_uri = urlparse(url.lower())
        domain = parsed_uri.netloc
        path = parsed_uri.path
    except Exception:
        return False

    # Check YouTube
    if "youtube.com" in domain:
        # Check watch page, shorts, embed or v path
        if "/watch" in path or "/embed/" in path or "/v/" in path or "/shorts/" in path:
            return True
        return False
        
    if "youtu.be" in domain:
        # If there is a path component (e.g. youtu.be/xxxx), it's a video
        cleaned_path = path.strip('/')
        if cleaned_path and not cleaned_path.startswith(('feed', 'channel', 'c/')):
            return True
        return False

    # Check Vimeo
    if "vimeo.com" in domain:
        # Vimeo video URLs are usually vimeo.com/123456789
        cleaned_path = path.strip('/')
        if cleaned_path.isdigit():
            return True
        return False

    # Check Twitch
    if "twitch.tv" in domain:
        # Twitch stream or video path
        cleaned_path = path.strip('/')
        if cleaned_path and cleaned_path not in ('', 'directory', 'videos', 'p', 'search', 'moderator'):
            return True
        return False

    # Check video file extensions
    parsed = os.path.basename(url.split('?')[0].lower())
    _, ext = os.path.splitext(parsed)
    return ext in VIDEO_EXTENSIONS

async def dogbrowser_render_image_to_ansi(image_bytes, target_width=48):
    """
    Convert image bytes into ANSI colored terminal block characters.
    Uses half-block characters (▄) to double the vertical resolution.
    """
    try:
        # Load image with Pillow
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('RGBA')
        
        # Calculate height keeping aspect ratio (half blocks are twice as tall as they are wide,
        # so we divide the aspect ratio factor by 2 to get square-ish terminal pixels)
        w, h = img.size
        aspect = h / w
        target_height = int(target_width * aspect * 0.5)
        
        # Ensure minimum size
        target_height = max(1, target_height)
        
        # Resize image
        img = img.resize((target_width, target_height * 2), Image.Resampling.LANCZOS)
        pixels = img.load()
        
        ansi_text = Text()
        
        # Render using half-block characters: foreground color for top pixel,
        # background color for bottom pixel in each cell.
        for y in range(0, target_height * 2, 2):
            for x in range(target_width):
                r1, g1, b1, a1 = pixels[x, y]
                r2, g2, b2, a2 = pixels[x, y + 1]
                
                # If pixels are transparent, fall back to terminal default (or dark gray)
                if a1 < 30 and a2 < 30:
                    ansi_text.append(" ", Style())
                elif a1 < 30:
                    # Only bottom pixel visible
                    fg_color = Color.from_rgb(r2, g2, b2)
                    ansi_text.append("▄", Style(color=fg_color))
                elif a2 < 30:
                    # Only top pixel visible
                    fg_color = Color.from_rgb(r1, g1, b1)
                    ansi_text.append("▀", Style(color=fg_color))
                else:
                    # Both visible
                    fg_color = Color.from_rgb(r2, g2, b2)
                    bg_color = Color.from_rgb(r1, g1, b1)
                    ansi_text.append("▄", Style(color=fg_color, bgcolor=bg_color))
            ansi_text.append("\n")
            
        return ansi_text
    except Exception as e:
        return Text(f"Error rendering image: {str(e)}", style="bold red")

async def dogbrowser_fetch_image_ansi(url, target_width=48):
    """Download image and convert it to ANSI blocks."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                return await dogbrowser_render_image_to_ansi(resp.content, target_width)
            else:
                return Text(f"HTTP Error {resp.status_code} fetching image", style="bold red")
    except Exception as e:
        return Text(f"Error fetching image: {str(e)}", style="bold red")

def dogbrowser_get_video_info(url):
    """
    Extract video metadata using yt-dlp in a separate thread.
    Returns metadata dict or error info.
    """
    if not yt_dlp:
        return {"error": "yt-dlp is not installed or available"}
        
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract relevant fields
            title = info.get('title', 'Unknown Title')
            description = info.get('description', '')
            if description and len(description) > 300:
                description = description[:300] + "..."
                
            thumbnails = info.get('thumbnails', [])
            thumbnail_url = None
            if thumbnails:
                # Find a reasonable sized thumbnail
                thumbnail_url = thumbnails[-1].get('url')
                
            return {
                "title": title,
                "uploader": info.get('uploader', 'Unknown Uploader'),
                "duration": info.get('duration'),
                "view_count": info.get('view_count'),
                "like_count": info.get('like_count'),
                "description": description,
                "thumbnail_url": thumbnail_url,
                "url": url,
                "original_url": info.get('webpage_url', url)
            }
    except Exception as e:
        return {"error": str(e)}
