import sys
import time
from patchright.sync_api import sync_playwright

sitekey = "0x4AAAAAAAWXJGBD7bONzLBd"
url = "https://portal.privatemode.ai/"

html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Turnstile</title></head>
<body>
<div class="cf-turnstile" data-sitekey="{sitekey}"></div>
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
</body></html>"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("requestfailed", lambda req: print(f"REQ FAILED: {req.url} -> {req.failure}"))
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    
    page.route(
        "https://portal.privatemode.ai/**",
        lambda r: r.fulfill(body=html, status=200, content_type="text/html")
        if r.request.resource_type == "document"
        else r.continue_(),
    )
    print("Navigating...", flush=True)
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(3)
    print("Done waiting. Frames:", len(page.frames), flush=True)
    browser.close()
