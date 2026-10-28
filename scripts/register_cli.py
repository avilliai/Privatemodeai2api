"""Command-line interface for Privatemode account registration and testing."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.dependencies import account_manager, email_service, register_service, turnstile_service


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )


async def cmd_test_turnstile() -> None:
    print("[*] Testing Cloudflare Turnstile Solver...")
    print(f"[*] Solver URL: {settings.TURNSTILE_SOLVER_URL}")
    print(f"[*] Target Sitekey: {settings.TURNSTILE_SITEKEY}")
    try:
        token = await turnstile_service.solve(
            url="https://portal.privatemode.ai/",
            sitekey=settings.TURNSTILE_SITEKEY,
        )
        if token:
            print(f"[+] Turnstile Solved Successfully! Token: {token[:40]}... (length: {len(token)})")
        else:
            print("[-] Failed to solve Turnstile: No token returned")
    except Exception as e:
        print(f"[-] Error solving Turnstile: {e}")


async def cmd_test_email() -> None:
    print("[*] Testing Outlook Email Service from account file...")
    print(f"[*] Account file: {settings.OUTLOOK_ACCOUNT_FILE}")
    try:
        inbox = await email_service.create_email()
        print(f"[+] Obtained working inbox: {inbox.address}")
        print(f"[+] OAuth2 Access Token successfully refreshed! Token preview: {inbox.token[:25]}...")
    except Exception as e:
        print(f"[-] Error obtaining Outlook inbox: {e}")


async def cmd_list_accounts() -> None:
    accounts = await account_manager.list_accounts()
    stats = await account_manager.get_stats()
    print("\n=================== PRIVATEMODE ACCOUNT POOL ===================")
    print(f"Total Accounts: {stats['total_accounts']} | Active: {stats['active_accounts']} | Exhausted: {stats['exhausted_accounts']} | Rate Limited: {stats['rate_limited_accounts']}")
    print("----------------------------------------------------------------")
    if not accounts:
        print("No accounts in pool yet. Run registration to add accounts.")
    for idx, acc in enumerate(accounts, 1):
        print(f"[{idx}] {acc['email']} | Status: {acc['status']} | API Key: {acc['api_key_masked']} | Requests: {acc['total_requests']}")
    print("================================================================\n")


async def cmd_register(count: int = 1) -> None:
    print(f"[*] Starting registration for {count} account(s)...")
    success_count = 0
    fail_count = 0

    for i in range(count):
        print(f"\n--- [{i + 1}/{count}] Starting new account registration ---")
        try:
            record = await register_service.register_single_account()
            success_count += 1
            print(f"[+] Successfully registered: {record.email}")
            print(f"[+] API Key: {record.api_key}")
            print(f"[+] Key ID: {record.key_id} | Org ID: {record.org_id}")
        except Exception as e:
            fail_count += 1
            print(f"[-] Registration {i + 1}/{count} failed: {e}")

    print("\n=================== REGISTRATION SUMMARY ===================")
    print(f"Requested: {count} | Succeeded: {success_count} | Failed: {fail_count}")
    print("============================================================")


async def main_async(args: argparse.Namespace) -> None:
    if args.test_turnstile:
        await cmd_test_turnstile()
        return

    if args.test_email:
        await cmd_test_email()
        return

    if args.list_accounts:
        await cmd_list_accounts()
        return

    await cmd_register(count=args.count)


def main() -> None:
    parser = argparse.ArgumentParser(description="Privatemode AI CLI Registration & Diagnostics")
    parser.add_argument("-c", "--count", type=int, default=1, help="Number of accounts to register (default: 1)")
    parser.add_argument("--test-turnstile", action="store_true", help="Test Turnstile solver")
    parser.add_argument("--test-email", action="store_true", help="Test Outlook email OAuth2 refresh")
    parser.add_argument("--list-accounts", action="store_true", help="List registered accounts in pool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
