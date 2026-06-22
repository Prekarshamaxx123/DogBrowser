import httpx
from bs4 import BeautifulSoup

ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"

print("Testing mbasic.facebook.com...")
try:
    r = httpx.get("https://mbasic.facebook.com/", headers={"User-Agent": ua}, follow_redirects=True)
    print("  Status:", r.status_code)
    print("  Final URL:", r.url)
    print("  Length:", len(r.text))
    print("  Snippet of text:")
    soup = BeautifulSoup(r.text, 'lxml')
    text_lines = [line.strip() for line in soup.get_text().split("\n") if line.strip()]
    for line in text_lines[:25]:
        print("    ", line)
except Exception as e:
    print("  Error:", e)
