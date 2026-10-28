import httpx

client = httpx.Client(base_url="https://portal.privatemode.ai")
r = client.get("/_app/immutable/chunks/Ch1uY61F.js")
print(r.text)
