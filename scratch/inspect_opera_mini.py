import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import httpx
from bs4 import BeautifulSoup

ua = 'Opera/9.80 (J2ME/MIDP; Opera Mini/4.5.33860/37.9135; U; en) Presto/2.12.423 Version/12.16'
headers = {'User-Agent': ua, 'Accept-Language': 'en-US,en;q=0.9'}

r = httpx.get('https://mbasic.facebook.com/', headers=headers)
soup = BeautifulSoup(r.text, 'lxml')

print("Title:", soup.title.string if soup.title else "No title")

print("\n--- BODY TEXT ---")
body_text = [line.strip() for line in soup.body.get_text().split("\n") if line.strip()]
for line in body_text[:30]:
    print("  ", line)

print("\n--- FORMS AND INPUTS ---")
for i, f in enumerate(soup.find_all('form'), 1):
    print(f"Form #{i}: method={f.get('method')} | action={f.get('action')}")
    # Print buttons or inputs
    for inp in f.find_all(['input', 'button']):
        print(f"  [{inp.name}] name={inp.get('name')} type={inp.get('type')} value={inp.get('value')}")
    # Print form text content
    print("  Form Text:", f.get_text(separator=" | ", strip=True)[:300])

print("\n--- ALL LINKS ---")
for a in soup.find_all('a', href=True)[:15]:
    print(f"  [{a.get_text().strip()}] -> {a['href']}")
