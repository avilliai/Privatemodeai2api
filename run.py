# -*- coding: utf-8 -*-
"""Startup script for Privatemode AI 2API gateway."""

import os
import sys
import subprocess
import urllib.request
import time

# Ensure UTF-8 output encoding for console & loggers
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def check_turnstile_solver():
    """Verify if the Turnstile Solver is running on port 5072."""
    try:
        req = urllib.request.Request("http://127.0.0.1:5072/turnstile")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status in (200, 405)
    except Exception:
        return False

def main():
    print("=" * 60)
    print("  Privatemode AI 2API Gateway & Account Manager")
    print("=" * 60)

    if check_turnstile_solver():
        print("[OK] Turnstile Solver is running at http://127.0.0.1:5072")
    else:
        print("[WARN] Turnstile Solver not detected at http://127.0.0.1:5072")
        print("       Automatic registration requires Turnstile Solver.")
        print("       Repository: https://github.com/D3-vin/Turnstile-Solver-NEW")

    print("[INFO] Starting FastAPI gateway on http://127.0.0.1:8000 ...")
    print("[INFO] Web Dashboard: http://127.0.0.1:8000/")
    print("[INFO] OpenAPI Docs:  http://127.0.0.1:8000/docs")

    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")

if __name__ == "__main__":
    main()
