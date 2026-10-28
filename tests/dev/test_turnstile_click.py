import asyncio
from patchright.async_api import async_playwright
import sys
sys.path.append(r'C:\Users\Administrator\PycharmProjects\Turnstile-Solver-NEW')
from core.browser import BrowserConfig, launch_browser, close_browser, context_options
from core.templates import build_route_html, route_glob
from turnstile.solve import click_turnstile_checkbox, _get_token_route

async def test():
    config = BrowserConfig(browser_type='msedge', headless=True)
    driver, browser = await launch_browser(config)
    opts = context_options(config, None)
    context = await browser.new_context(**opts)
    page = await context.new_page()

    url = 'https://portal.privatemode.ai/'
    sitekey = '0x4AAAAAAAWXJGBD7bONzLBd'
    page_data = build_route_html(sitekey)
    pattern = route_glob(url)
    await page.route(pattern, lambda r: r.fulfill(body=page_data, status=200))
    print('Navigating...')
    await page.goto(url, wait_until='domcontentloaded', timeout=30000)

    print('Waiting for turnstile and clicking checkbox...')
    for attempt in range(15):
        await asyncio.sleep(1)
        val = await page.input_value('[name=cf-turnstile-response]')
        if val:
            print('Got token immediately!', val[:50])
            break
        clicked = await click_turnstile_checkbox(page, attempts=1)
        if clicked:
            print(f'Attempt {attempt}: clicked turnstile checkbox!')
            # wait a bit for token
            for _ in range(10):
                await asyncio.sleep(1)
                val = await page.input_value('[name=cf-turnstile-response]')
                if val:
                    print('Got token after click!', val[:60])
                    break
            if val:
                break
    else:
        print('Could not get token')

    await close_browser(driver, browser)

asyncio.run(test())
