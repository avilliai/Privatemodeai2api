import httpx
import re

client = httpx.Client(base_url="https://portal.privatemode.ai")
r = client.get("/_app/immutable/nodes/2.DeBfS3Sk.js")

# Find references to post-signup onboarding, organization, etc.
lines = r.text.split(";")
for line in lines:
    if any(k in line for k in ["pm_sign_up", "firstOrganization", "createOrganization", "organization", "backend_keys"]):
        print(line[:300])
        print("---")
