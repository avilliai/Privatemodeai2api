import httpx

client = httpx.Client(base_url="https://portal.privatemode.ai")
r = client.get("/_app/immutable/nodes/6.-ftwtBCU.js")
print(r.text[3000:6500])
