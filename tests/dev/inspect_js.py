import httpx
import re

# Fetch the main HTML to get all chunks
r = httpx.get("https://portal.privatemode.ai/")
chunks = re.findall(r'href="(/_app/immutable/[^"]+)"', r.text)

print("Found initial links:", len(chunks))

all_js = set()
for c in chunks:
    if c.endswith(".js"):
        all_js.add(c)

# Also fetch all nodes 0..10
for i in range(15):
    # check in app.js
    pass

client = httpx.Client(base_url="https://portal.privatemode.ai")

# Download each and search for chunk references
to_visit = set(all_js)
visited = set()

while to_visit:
    url = to_visit.pop()
    if url in visited:
        continue
    visited.add(url)
    res = client.get(url)
    if res.status_code == 200:
        found = re.findall(r'["\'](/_app/immutable/[^"\']+\.js)["\']', res.text)
        found_rel = re.findall(r'["\'](\.\./[^"\']+\.js)["\']', res.text)
        for f in found:
            if f not in visited:
                to_visit.add(f)
        for f in found_rel:
            norm = "/_app/immutable/" + f.replace("../", "")
            if norm not in visited:
                to_visit.add(norm)

print(f"Total JS files collected: {len(visited)}")

keywords = ["clerk", "api_key", "apiKey", "api-key", "token", "create", "balance", "credit", "models", "completions", "saas-api"]

results = {}
for url in visited:
    res = client.get(url)
    text = res.text
    matches = []
    for kw in keywords:
        if kw in text:
            matches.append(kw)
    if matches:
        print(f"{url}: {matches}")
        # search for interesting substrings
        for kw in ["saas-api", "clerk", "apiKey", "api-key"]:
            for m in re.finditer(rf'.{{0,50}}{kw}.{{0,50}}', text, re.IGNORECASE):
                snippet = m.group(0).replace("\n", " ")
                print(f"   [{kw}] {snippet}")
