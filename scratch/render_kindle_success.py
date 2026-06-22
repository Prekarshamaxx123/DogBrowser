import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from bs4 import BeautifulSoup
from browser.parser import DogBrowserParser

with open("scratch/mbasic_success_KindleFire.html", "r", encoding="utf-8") as f:
    html = f.read()

parser = DogBrowserParser()
page, blocks = parser.parse_to_blocks(html, "https://mbasic.facebook.com/")

print("=== PARSED BLOCKS ===")
for btype, text, url, extra in blocks[:40]:
    print(f"[{btype}] {text} | {url} | {extra}")
