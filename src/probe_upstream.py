# -*- coding: utf-8 -*-
"""probe_upstream.py — 用插件同样的 UA 与 token 直接请求上游，确认错误来源。"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOME = pathlib.Path.home() / ".dsh"
CLIENT_UA = "CLI/2.63.2 CodeBuddy/2.63.2"   # 插件里写死的值

# CN 凭据
cn = json.loads((HOME / ".workbuddy-cn-auth.json").read_text(encoding="utf-8"))["credential"]
CN_TOKEN = cn["accessToken"]
CN_UID = cn["uid"]
CN_DOMAIN = cn["domain"]

# Global 凭据
gl = json.loads((HOME / ".workbuddy-ai-auth.json").read_text(encoding="utf-8"))["credential"]
GL_TOKEN = gl["accessToken"]
GL_UID = gl["uid"]
GL_DOMAIN = gl["domain"]

print("=" * 86)
print("凭据")
print("=" * 86)
print(f"CN     uid={CN_UID}  domain={CN_DOMAIN}  tokenLen={len(CN_TOKEN)}")
print(f"Global uid={GL_UID}  domain={GL_DOMAIN}  tokenLen={len(GL_TOKEN)}")
print(f"伪造 UA: {CLIENT_UA}")
print()

CASES = [
    ("CN   catalog", "https://www.codebuddy.cn/v3/config", CN_TOKEN, CN_UID, CN_DOMAIN),
    ("CN   catalog(alt)", "https://copilot.tencent.com/v3/config", CN_TOKEN, CN_UID, CN_DOMAIN),
    ("GLOBAL catalog", "https://www.workbuddy.ai/v3/config", GL_TOKEN, GL_UID, GL_DOMAIN),
]


def call(label, url, token, uid, domain):
    h = {
        "User-Agent": CLIENT_UA,
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
        "X-Requested-With": "XMLHttpRequest",
        "X-User-Id": uid,
        "X-Domain": domain,
    }
    req = urllib.request.Request(url, headers=h, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
            print(f"[{label}] HTTP {r.status}  len={len(body)}")
            print(f"    {body[:300]}")
            return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"[{label}] HTTP {e.code}")
        print(f"    {body[:500]}")
        return e.code, body
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
        return 0, str(e)


for label, url, tok, uid, dom in CASES:
    print("-" * 86)
    call(label, url, tok, uid, dom)
    print()
