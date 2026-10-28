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

print("Starting playwright...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.route(
        "https://portal.privatemode.ai/**",
        lambda r: r.fulfill(body=html, status=200, content_type="text/html")
        if r.request.resource_type == "document"
        else r.continue_(),
    )
    print("Navigating...")
    page.goto(url, wait_until="domcontentloaded")
    print("Navigated! Checking for Turnstile...")
    token = None
    for i in range(15):
        time.sleep(1)
        try:
            val = page.input_value("[name=cf-turnstile-response]")
            if val:
                print("Got token:", val[:50], "len:", len(val))
                token = val
                break
        except Exception:
            pass

        for fr in page.frames:
            if "challenges.cloudflare.com" in fr.url:
                try:
                    el = fr.frame_element()
                    box = el.bounding_box()
                    if box and box["width"] > 20:
                        page.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
                        print(f"[{i}s] Clicked Turnstile iframe box: {box}")
                except Exception as e:
                    pass
    browser.close()
    if token:
        print("SUCCESS! Solved Turnstile token:", token[:40] + "...")
    else:
        print("FAILED to get token")
