import httpx

client = httpx.Client(base_url="https://portal.privatemode.ai")
r = client.get("/_app/immutable/chunks/odoy_ZFG.js")
print("=== odoy_ZFG.js ===")
print(r.text)

print("\n=== DsyIRVvf.js ===")
r2 = client.get("/_app/immutable/chunks/DsyIRVvf.js")
print(r2.text[:2000])
