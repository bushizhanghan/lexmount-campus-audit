# -*- coding: utf-8 -*-
"""probe_chat.py — 复刻插件的 chat 请求头，直接打上游 chat 接口。"""
import io
import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOME = pathlib.Path.home() / ".dsh"
CLIENT_UA = "CLI/2.63.2 CodeBuddy/2.63.2"

cn = json.loads((HOME / ".workbuddy-cn-auth.json").read_text(encoding="utf-8"))["credential"]
gl = json.loads((HOME / ".workbuddy-ai-auth.json").read_text(encoding="utf-8"))["credential"]


def chat_headers(cred, origin):
    h = {
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": origin,
        "Referer": origin + "/",
        "User-Agent": CLIENT_UA,
        "Content-Type": "application/json",
        "X-User-Id": cred["uid"],
        "X-No-Enterprise-Id": "1",
        "X-Product": "SaaS",
        "Authorization": "Bearer " + cred["accessToken"],
    }
    if cred.get("domain"):
        h["X-Domain"] = cred["domain"]
    else:
        h["X-No-Department-Info"] = "1"
    return h


BODY = {
    "model": "deepseek-v4.1-flash",
    "messages": [{"role": "user", "content": "hi"}],
    "stream": False,
    "max_tokens": 16,
}

CASES = [
    ("CN     chat", "https://copilot.tencent.com/v2/chat/completions",
     cn, "https://www.codebuddy.cn"),
    ("GLOBAL chat", "https://www.workbuddy.ai/v2/chat/completions",
     gl, "https://www.workbuddy.ai"),
]

for label, url, cred, origin in CASES:
    print("=" * 86)
    print(f"{label}  ->  {url}")
    print(f"  Origin={origin}  UA={CLIENT_UA}")
    req = urllib.request.Request(
        url,
        data=json.dumps(BODY).encode(),
        headers=chat_headers(cred, origin),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
            print(f"  HTTP {r.status}  len={len(body)}")
            print(f"  {body[:400]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"  HTTP {e.code}")
        print(f"  {body[:700]}")
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {e}")
    print()
