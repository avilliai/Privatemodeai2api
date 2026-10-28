import httpx

client = httpx.Client(base_url="https://portal.privatemode.ai")
r = client.get("/_app/immutable/nodes/4.C5ra3I1_.js")
print("=== nodes/4.C5ra3I1_.js ===")
print(r.text[:3000])

r2 = client.get("/_app/immutable/chunks/DraMRLtw.js")
print("\n=== DraMRLtw.js ===")
print(r2.text[:2000])
