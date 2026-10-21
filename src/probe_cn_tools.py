# -*- coding: utf-8 -*-
"""probe_cn_tools.py — 国内端点在不同请求形状下是否也触发渠道校验。"""
import io
import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOME = pathlib.Path.home() / ".dsh"
UA = "CLI/2.63.2 CodeBuddy/2.63.2"
cn = json.loads((HOME / ".workbuddy-cn-auth.json").read_text(encoding="utf-8"))["credential"]

URL_CN = "https://copilot.tencent.com/v2/chat/completions"
URL_GL = "https://www.workbuddy.ai/v2/chat/completions"


def hdr(cred, origin):
    return {
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": origin,
        "Referer": origin + "/",
        "User-Agent": UA,
        "Content-Type": "application/json",
        "X-User-Id": cred["uid"],
        "X-No-Enterprise-Id": "1",
        "X-Domain": cred["domain"],
        "X-Product": "SaaS",
        "Authorization": "Bearer " + cred["accessToken"],
    }


def send(label, url, body, origin):
    print("-" * 78)
    print(label)
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=hdr(cn, origin), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read(300).decode("utf-8", "replace")
            print(f"  HTTP {r.status}  {txt[:220]}")
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        code = ""
        try:
            code = str(json.loads(txt).get("code"))
        except Exception:
            pass
        print(f"  HTTP {e.code}  code={code}")
        print(f"  {txt[:260]}")
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {e}")


BASE = {"model": "deepseek-v4.1-flash", "stream": True, "max_tokens": 32}

# 1. 最小请求
send("CN 极简请求", URL_CN,
     {**BASE, "messages": [{"role": "user", "content": "hi"}]},
     "https://www.codebuddy.cn")

# 2. 带 system + tools（接近真实 Agent 请求）
send("CN 带 system+tools", URL_CN, {
    **BASE,
    "messages": [
        {"role": "system", "content": "You are a helpful coding agent."},
        {"role": "user", "content": "list files"},
    ],
    "tools": [{
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}}, "required": ["path"]},
        },
    }],
}, "https://www.codebuddy.cn")

# 3. 国际端点同样的极简请求（对照）
send("GLOBAL 极简请求", URL_GL,
     {**BASE, "messages": [{"role": "user", "content": "hi"}]},
     "https://www.workbuddy.ai")
