import httpx

client = httpx.Client()
resp = client.get("https://clerk.privatemode.ai/v1/environment", headers={
    "Origin": "https://portal.privatemode.ai",
    "Referer": "https://portal.privatemode.ai/"
})
print("Environment status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Display config:", data.get("display_config", {}))
    print("User settings:", list(data.get("user_settings", {}).keys()))
    print("Auth config:", data.get("auth_config"))
