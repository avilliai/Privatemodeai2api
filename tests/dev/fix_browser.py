import re
from pathlib import Path

path = Path(r"C:\Users\Administrator\PycharmProjects\Turnstile-Solver-NEW\core\browser.py")
content = path.read_text(encoding="utf-8")
old = "browser = await driver.chromium.launch(channel=config.browser_type, headless=False, args=args)"
new = "channel = None if config.browser_type == 'chromium' else config.browser_type\n    browser = await driver.chromium.launch(channel=channel, headless=False, args=args)"
if old in content:
    content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")
    print("browser.py updated successfully")
else:
    print("pattern not found")
