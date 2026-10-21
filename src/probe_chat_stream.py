# -*- coding: utf-8 -*-
"""probe_chat_stream.py — 用 stream=true 复刻真实调用路径。"""
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


def hdr(cred, origin):
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
    return h


def run(label, url, cred, origin, model):
    print("=" * 86)
    print(f"{label}  model={model}")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "say hi"}],
        "stream": True,
        "max_tokens": 16,
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=hdr(cred, origin), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read(2048).decode("utf-8", "replace")
            print(f"  HTTP {r.status}")
            print(f"  {raw[:400]}")
    except urllib.error.HTTPError as e:
        b = e.read().decode("utf-8", "replace")
        print(f"  HTTP {e.code}")
        print(f"  {b[:700]}")
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {e}")
    print()


run("CN     chat stream", "https://copilot.tencent.com/v2/chat/completions",
    cn, "https://www.codebuddy.cn", "deepseek-v4.1-flash")

run("GLOBAL chat stream", "https://www.workbuddy.ai/v2/chat/completions",
    gl, "https://www.workbuddy.ai", "deepseek-v4.1-flash")

# 交叉：CN token 打 global 端点（模拟区域错配）
run("CN token -> GLOBAL", "https://www.workbuddy.ai/v2/chat/completions",
    cn, "https://www.workbuddy.ai", "deepseek-v4.1-flash")

# 交叉：不要 X-Product 头
def hdr_no_product(cred, origin):
    h = hdr(cred, origin)
    h.pop("X-Product", None)
    return h

print("=" * 86)
print("CN chat stream（去掉 X-Product 头）")
body = {"model": "deepseek-v4.1-flash",
        "messages": [{"role": "user", "content": "hi"}], "stream": True, "max_tokens": 16}
req = urllib.request.Request("https://copilot.tencent.com/v2/chat/completions",
                             data=json.dumps(body).encode(),
                             headers=hdr_no_product(cn, "https://www.codebuddy.cn"),
                             method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"  HTTP {r.status}  {r.read(300).decode('utf-8','replace')[:300]}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}\n  {e.read().decode('utf-8','replace')[:600]}")
except Exception as e:
    print(f"  ERR {e}")
