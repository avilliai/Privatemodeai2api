import asyncio
import sys
sys.path.append(r"C:\Users\Administrator\PycharmProjects\Turnstile-Solver-NEW")
from core.browser import BrowserConfig, launch_browser, close_browser, context_options
import turnstile.solve as solver

async def main():
    config = BrowserConfig(browser_type="chromium", headless=True)
    driver, browser = await launch_browser(config)
    opts = context_options(config, None)
    context = await browser.new_context(**opts)
    page = await context.new_page()
    
    url = "https://portal.privatemode.ai/"
    sitekey = "0x4AAAAAAAWXJGBD7bONzLBd"
    print("Starting turnstile solve...")
    token, method = await solver.solve(page, url, sitekey)
    print(f"Result: method={method}, token_len={len(token) if token else 0}")
    if token:
        print(f"Token sample: {token[:60]}...")
    await close_browser(driver, browser)
    return token

if __name__ == "__main__":
    asyncio.run(main())
