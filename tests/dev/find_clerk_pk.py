import httpx
import re

client = httpx.Client(base_url="https://portal.privatemode.ai")
r = client.get("/")

# Search for pk_live_ or pk_test_ or clerk in index.html and all js files
print("Searching for clerk publishable key...")

# Find all script tags or preload links
scripts = re.findall(r'href="(/_app/immutable/[^"]+\.js)"', r.text)

for s in scripts:
    content = client.get(s).text
    pks = re.findall(r'pk_(?:live|test)_[a-zA-Z0-9_\-]+', content)
    clerk_urls = re.findall(r'https://clerk\.[a-zA-Z0-9_\-\.]+', content)
    if pks or clerk_urls:
        print(f"File: {s}")
        if pks:
            print("  PK:", pks)
        if clerk_urls:
            print("  Clerk URLs:", clerk_urls)
