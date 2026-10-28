import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("request", lambda req: print(f"REQ: {req.method} {req.url}") if any(k in req.url for k in ["clerk", "challenges", "turnstile"]) else None)
    
    print("Navigating to https://portal.privatemode.ai/sign-up...")
    page.goto("https://portal.privatemode.ai/sign-up", wait_until="networkidle")
    print("Page title:", page.title())
    print("URL:", page.url)
    print("Inputs on page:", [el.get_attribute("name") or el.get_attribute("type") or el.get_attribute("placeholder") for el in page.query_selector_all("input")])
    browser.close()
