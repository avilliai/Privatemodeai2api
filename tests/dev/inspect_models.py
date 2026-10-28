import httpx
import re

client = httpx.Client(base_url="https://portal.privatemode.ai")
r = client.get("/_app/immutable/chunks/DsyIRVvf.js")
models = re.findall(r'[\'"`]([a-zA-Z0-9_\-\.\/]+)[\'"`]', r.text)
print("Possible models or tokens in DsyIRVvf.js:")
for m in set(models):
    if any(k in m for k in ["glm", "claude", "gpt", "llama", "deepseek", "qwen", "mistral"]):
        print(" ", m)
