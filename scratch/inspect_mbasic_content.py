from bs4 import BeautifulSoup
import httpx

ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"

r = httpx.get("https://mbasic.facebook.com/", headers={"User-Agent": ua}, follow_redirects=True)
soup = BeautifulSoup(r.text, 'lxml')

print("Page Title:", soup.title.string if soup.title else "No title")

# Print all inputs and forms
print("\n--- FORMS ---")
for f in soup.find_all('form'):
    print(f"Form method: {f.get('method')} | action: {f.get('action')}")
    for inp in f.find_all('input'):
        print(f"  Input: name={inp.get('name')} type={inp.get('type')} value={inp.get('value')}")

# Print all links
print("\n--- LINKS (first 10) ---")
for a in soup.find_all('a', href=True)[:10]:
    print(f"  Link: {a.get_text().strip()} -> {a['href']}")

# Save file
with open("scratch/mbasic_raw.html", "w", encoding="utf-8") as f:
    f.write(r.text)
