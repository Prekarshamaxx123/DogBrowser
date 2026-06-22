with open("scratch/mbasic_raw.html", "r", encoding="utf-8") as f:
    content = f.read()

print("HTML length:", len(content))
print("Contains '<script>':", "<script" in content.lower())
print("Contains '<noscript>':", "<noscript" in content.lower())
print("Contains 'loading':", "loading" in content.lower())

# Let's print the first 1000 characters
print("\n--- FIRST 1500 CHARACTERS ---")
print(content[:1500])

# Let's print the end of the file too
print("\n--- LAST 1000 CHARACTERS ---")
print(content[-1000:])
