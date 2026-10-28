import httpx

client = httpx.Client()
url = "https://clerk.privatemode.ai/v1/client/sign_ups"
headers = {
    "Origin": "https://portal.privatemode.ai",
    "Referer": "https://portal.privatemode.ai/",
    "Content-Type": "application/x-www-form-urlencoded",
}
r = client.post(url, headers=headers, data={"captcha_token": "test_fake_token"})
print("Status:", r.status_code)
print("Response:", r.json())
