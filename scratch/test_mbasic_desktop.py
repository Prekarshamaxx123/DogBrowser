import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import httpx
from bs4 import BeautifulSoup

uas = {
    'FirefoxDesktop': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'ChromeDesktop': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'AndroidChrome': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    'IE11': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Googlebot': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
}

for name, ua in uas.items():
    headers = {'User-Agent': ua, 'Accept-Language': 'en-US,en;q=0.9'}
    r = httpx.get('https://mbasic.facebook.com/', headers=headers, follow_redirects=True)
    soup = BeautifulSoup(r.text, 'lxml')
    inputs = [inp.get('name') for inp in soup.find_all('input') if inp.get('name')]
    
    print(f"{name} User-Agent:")
    print(f"  Status: {r.status_code}")
    print(f"  Final URL: {r.url}")
    print(f"  Inputs: {inputs}")
    print(f"  Contains 'Loading...': {'loading...' in r.text.lower()}")
    print(f"  Contains 'not available': {'not available' in r.text.lower()}")
    print("-" * 40)
