import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser.parser import DogBrowserParser
from browser.engine import DogBrowserEngine

def test_pagination():
    html = """
    <html>
      <body>
        <form action="/html/" method="post">
          <input type="hidden" name="q" value="test query">
          <input type="hidden" name="s" value="30">
          <input type="submit" value="Next Page">
          <button type="submit" name="btn" value="submit_val">Click Button</button>
        </form>
        <ul>
          <li><a href="/courses">Courses</a></li>
          <li>Some static list item</li>
          <li>List item with <a href="/blog">Blog Link</a> inside</li>
        </ul>
        <p>This is a paragraph with a <a href="/about">link to About page</a> inside it.</p>
      </body>
    </html>
    """
    parser = DogBrowserParser()
    page, blocks = parser.parse_to_blocks(html, "https://html.duckduckgo.com/")
    print("--- PARSED BLOCKS ---")
    for block in blocks:
        print(block)
    print("\n--- FORMS DETECTED ---")
    for idx, f in enumerate(page.forms):
        print(f"Form #{idx}: {f['method']} -> {f['action']}")
        for inp in f["inputs"]:
            print(f"  Input: [{inp['type']}] name={inp['name']}, value={inp['value']}")

def test_bangs():
    engine = DogBrowserEngine()
    print("\n--- TESTING BANGS ---")
    # Test a default bang
    url_g = engine.resolve_input("!g hello")
    print(f"!g hello -> {url_g}")
    # Add a custom bang
    engine.add_bang("!test", "https://example.com/search?myquery={query}")
    url_test = engine.resolve_input("!test world")
    print(f"!test world -> {url_test}")

if __name__ == "__main__":
    test_pagination()
    test_bangs()
