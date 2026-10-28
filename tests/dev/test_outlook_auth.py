import sys
import httpx
import imaplib

# Read first line from OUT-20260802-S100-00060.txt
path = r"C:\Users\Administrator\PycharmProjects\genspark2api\OUT-20260802-S100-00060.txt"
with open(path, "r", encoding="utf-8-sig") as f:
    line = f.readline().strip()

parts = line.split("----")
email, password, client_id, refresh_token = parts[0], parts[1], parts[2], parts[3]
print("Testing Outlook OAuth for:", email)

# 1. Refresh OAuth access token
token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
resp = httpx.post(token_url, data={
    "client_id": client_id,
    "grant_type": "refresh_token",
    "refresh_token": refresh_token,
}, timeout=20)

print("OAuth token status:", resp.status_code)
if resp.status_code != 200:
    print("OAuth response:", resp.text)
    sys.exit(1)

access_token = resp.json().get("access_token")
print("Access token received! Length:", len(access_token))

# 2. Test IMAP connection
client = imaplib.IMAP4_SSL("outlook.office365.com", 993, timeout=15)
auth_str = f"user={email}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")
res = client.authenticate("XOAUTH2", lambda _: auth_str)
print("IMAP auth status:", res)

status, count = client.select("INBOX", readonly=True)
print("INBOX status:", status, "count:", count)

client.logout()
print("IMAP test SUCCESS!")
