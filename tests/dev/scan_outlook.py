import httpx
import imaplib
from pathlib import Path

def test_file(filepath, max_check=10):
    lines = [l.strip() for l in Path(filepath).read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    print(f"Testing {filepath}: {len(lines)} lines")
    found = 0
    for idx, line in enumerate(lines[:max_check]):
        parts = line.split("----")
        if len(parts) < 4:
            continue
        email, pwd, cid, rtok = parts[0], parts[1], parts[2], parts[3]
        try:
            resp = httpx.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data={
                "client_id": cid,
                "grant_type": "refresh_token",
                "refresh_token": rtok,
            }, timeout=10)
            if resp.status_code == 200:
                tok = resp.json().get("access_token")
                print(f"  [OK] line {idx+1}: {email} access token obtained!")
                found += 1
                if found >= 2:
                    break
            else:
                err = resp.json().get("error", resp.text[:50])
                print(f"  [FAIL] line {idx+1}: {email} -> {err}")
        except Exception as e:
            print(f"  [ERR] line {idx+1}: {email} -> {e}")

test_file(r"C:\Users\Administrator\PycharmProjects\genspark2api\OUT-20260728-S1000-00082_Filtered.txt", 10)
