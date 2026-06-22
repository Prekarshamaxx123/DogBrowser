import httpx
from bs4 import BeautifulSoup

uas = {
    'OperaMini': 'Opera/9.80 (J2ME/MIDP; Opera Mini/4.5.33860/37.9135; U; en) Presto/2.12.423 Version/12.16',
    'NokiaSymbian': 'NokiaN73-1/3.0638.0.0.1 Series60/3.0 Profile/MIDP-2.0 Configuration/CLDC-1.1',
    'BlackBerry': 'BlackBerry9700/5.0.0.351 Profile/MIDP-2.1 Configuration/CLDC-1.1 VendorID/102',
    'PSP': 'Mozilla/4.0 (PlayStation Portable); 2.00',
    'SamsungFeature': 'SAMSUNG-GT-S5233T/S5233TDDJE3 SHP/VPP/R5 Profile/MIDP-2.1 Configuration/CLDC-1.1',
}

for name, ua in uas.items():
    headers = {'User-Agent': ua, 'Accept-Language': 'en-US,en;q=0.9'}
    r = httpx.get('https://mbasic.facebook.com/', headers=headers, follow_redirects=True)
    soup = BeautifulSoup(r.text, 'lxml')
    # Check if there is an email or login form
    has_login_form = bool(soup.find('form'))
    inputs = [inp.get('name') for inp in soup.find_all('input') if inp.get('name')]
    print(f"{name} User-Agent:")
    print(f"  Status: {r.status_code}")
    print(f"  Final URL: {r.url}")
    print(f"  Has forms: {has_login_form}")
    print(f"  Inputs found: {inputs}")
    print(f"  Contains 'Loading...': {'loading...' in r.text.lower()}")
    print("-" * 40)
    
    if has_login_form and 'email' in inputs:
        with open(f"scratch/mbasic_success_{name}.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"===> SUCCESS with {name}! Saved to scratch/mbasic_success_{name}.html")
        break
