# -*- coding: utf-8 -*-
"""probe_api.py — 找出正确的 API 基址并验证 key。"""
import json
import urllib.error
import urllib.request
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY = sys.argv[1] if len(sys.argv) > 1 else ""
PROJECT = "632c57a4-673d-4c87-b4be-f9f3f636d199"

BASES = [
    "https://browser.lexmount.cn",
    "https://api.lexmount.cn",
    "https://browser-api.lexmount.cn",
    "https://api.browser.lexmount.cn",
]

body = json.dumps({"extract": {"url": "https://example.com"}}).encode()


def call(base, key):
    req = urllib.request.Request(
        base + "/v1/extract",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": key,
            "X-Project-Id": PROJECT,
            "Accept": "application/json",
            "User-Agent": "dsh-agent/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")[:800]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:800]
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


print("=" * 78)
print("探测 API 基址")
print("=" * 78)
for base in BASES:
    st, txt = call(base, KEY)
    print(f"\n{base}  ->  {st}")
    print(f"  {txt[:500]}")
