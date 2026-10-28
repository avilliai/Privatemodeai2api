"""Direct in-process Turnstile solver using Patchright and route-intercept."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.core.config import Settings, settings as app_settings
from app.core.exceptions import TurnstileError

logger = logging.getLogger(__name__)


class TurnstileService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or app_settings

    async def solve(
        self,
        url: Optional[str] = None,
        sitekey: Optional[str] = None,
        action: Optional[str] = None,
        cdata: Optional[str] = None,
    ) -> str:
        """Solve Cloudflare Turnstile and return token."""
        target_url = url or self.settings.TURNSTILE_PORTAL_URL
        target_sitekey = sitekey or self.settings.TURNSTILE_SITEKEY

        try:
            token = await self._solve_in_browser(target_url, target_sitekey, action, cdata)
            if token:
                logger.info("Successfully solved Turnstile (%d chars)", len(token))
                return token
        except Exception as e:
            logger.error("Turnstile browser solver error: %s", e)

        raise TurnstileError(f"Failed to solve Cloudflare Turnstile for {target_url} with sitekey {target_sitekey}")

    async def _solve_in_browser(
        self,
        url: str,
        sitekey: str,
        action: Optional[str] = None,
        cdata: Optional[str] = None,
    ) -> Optional[str]:
        from patchright.async_api import async_playwright

        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Turnstile</title>
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
</head>
<body style="background:#111; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;">
<div class="cf-turnstile" data-sitekey="{sitekey}"{" data-action=" + repr(action) if action else ""}{" data-cdata=" + repr(cdata) if cdata else ""}></div>
</body></html>"""

        async with async_playwright() as p:
            channel = "msedge"
            # Launch browser
            browser = await p.chromium.launch(
                headless=False,
                channel=channel,
                args=[
                    "--window-position=-2000,-2000",
                    "--window-size=600,400",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = await browser.new_context(viewport={"width": 600, "height": 400})
            page = await context.new_page()

            # Route intercept on target URL domain
            await page.route(
                f"{url.rstrip('/')}/**",
                lambda r: r.fulfill(body=html_content, status=200, content_type="text/html")
                if r.request.resource_type == "document"
                else r.continue_(),
            )

            await page.goto(f"{url.rstrip('/')}/__turnstile_challenge", wait_until="domcontentloaded", timeout=25000)

            token: Optional[str] = None
            deadline = asyncio.get_running_loop().time() + self.settings.TURNSTILE_TIMEOUT

            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.8)
                try:
                    val = await page.input_value("[name=cf-turnstile-response]")
                    if val and len(val) > 20:
                        token = val
                        break
                except Exception:
                    pass

                # Check if challenge checkbox iframe exists and click it
                for fr in page.frames:
                    if "challenges.cloudflare.com" in (fr.url or ""):
                        try:
                            el = await fr.frame_element()
                            box = await el.bounding_box()
                            if box and box["width"] > 20:
                                await page.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
                        except Exception:
                            pass

            await browser.close()
            return token