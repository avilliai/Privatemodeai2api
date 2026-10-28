import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    page.on("request", lambda req: print(f"REQ: {req.method} {req.url}") if "clerk" in req.url or "challenges" in req.url else None)
    
    print("Navigating to https://portal.privatemode.ai/...")
    page.goto("https://portal.privatemode.ai/", wait_until="networkidle")
    print("Page title:", page.title())
    print("URL:", page.url)
    time.sleep(3)
    browser.close()
