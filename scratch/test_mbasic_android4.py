import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import httpx
from bs4 import BeautifulSoup

uas = {
    'Android4': 'Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; LGMS323 Build/KOT49I.MS32310c) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36',
    'Android4_0': 'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30',
    'KindleFire': 'Mozilla/5.0 (Linux; U; Android 2.3.4; en-us; Kindle Fire Build/GINGERBREAD) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1',
    'GooglebotMobile': 'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'OperaMiniAndroid': 'Mozilla/5.0 (Linux; U; Android 9; en-US; SM-G960F Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 OPR/46.0.2254.139040',
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
    
    if 'email' in inputs and 'pass' in inputs:
        print(f"===> SUCCESS with {name}!")
        with open(f"scratch/mbasic_success_{name}.html", "w", encoding="utf-8") as f:
            f.write(r.text)
