import httpx

client = httpx.Client()
# Let's inspect clerk sign_up options or send an empty POST to inspect error response
url = "https://clerk.privatemode.ai/v1/client/sign_ups"
headers = {
    "Origin": "https://portal.privatemode.ai",
    "Referer": "https://portal.privatemode.ai/",
    "Content-Type": "application/x-www-form-urlencoded",
}
r = client.post(url, headers=headers, data={})
print("Empty sign_up status:", r.status_code)
print("Response:", r.json())
