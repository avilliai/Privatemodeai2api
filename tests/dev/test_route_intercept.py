import asyncio
from patchright.async_api import async_playwright
import sys
sys.path.append(r"C:\Users\Administrator\PycharmProjects\Turnstile-Solver-NEW")
from core.browser import BrowserConfig, launch_browser, close_browser, context_options
from core.templates import build_route_html, route_glob
from turnstile.solve import click_turnstile_checkbox

async def test():
    config = BrowserConfig(browser_type="chromium", headless=True)
    driver, browser = await launch_browser(config)
    opts = context_options(config, None)
    context = await browser.new_context(**opts)
    page = await context.new_page()

    url = "https://portal.privatemode.ai/"
    sitekey = "0x4AAAAAAAWXJGBD7bONzLBd"
    page_data = build_route_html(sitekey)
    pattern = route_glob(url)
    
    # Intercept only the main document request
    await page.route(pattern, lambda r: r.fulfill(body=page_data, status=200, content_type="text/html") if r.request.resource_type == "document" else r.continue_())
    
    print("Navigating to route-intercepted page...")
    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    print("Page loaded, waiting for frames...")
    
    for i in range(15):
        await asyncio.sleep(1)
        val = await page.input_value("[name=cf-turnstile-response]")
        if val:
            print(f"Token obtained automatically! Length: {len(val)}, Value: {val[:60]}...")
            break
        # Try to click turnstile checkbox
        clicked = await click_turnstile_checkbox(page, attempts=1)
        if clicked:
            print(f"[{i}s] Clicked turnstile checkbox!")
            for _ in range(10):
                await asyncio.sleep(1)
                val = await page.input_value("[name=cf-turnstile-response]")
                if val:
                    print(f"Token obtained after click! Length: {len(val)}, Value: {val[:60]}...")
                    break
            if val:
                break
    else:
        print("Failed to get token within timeout")

    await close_browser(driver, browser)

asyncio.run(test())
