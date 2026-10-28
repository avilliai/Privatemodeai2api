import httpx
import re

r = httpx.get('https://portal.privatemode.ai/_app/immutable/entry/app.DneSHGpV.js')
for m in re.finditer(r'"(/[^"]*)":\s*\[([0-9,\s\[\]]+)\]', r.text):
    print(m.group(1), '->', m.group(2))
