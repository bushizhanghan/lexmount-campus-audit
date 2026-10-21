# -*- coding: utf-8 -*-
"""check_catalogs.py — 对比国内/国际两个 catalog 的模型清单，判断 deepseek-v4.1-flash 属于哪边。"""
import io
import json
import pathlib
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOME = pathlib.Path.home() / ".dsh"
UA = "CLI/2.63.2 CodeBuddy/2.63.2"

cn = json.loads((HOME / ".workbuddy-cn-auth.json").read_text(encoding="utf-8"))["credential"]
gl = json.loads((HOME / ".workbuddy-ai-auth.json").read_text(encoding="utf-8"))["credential"]


def get(url, cred, origin):
    h = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Authorization": "Bearer " + cred["accessToken"],
        "X-Requested-With": "XMLHttpRequest",
        "X-User-Id": cred["uid"],
        "X-Domain": cred["domain"],
    }
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def model_ids(cat):
    """从 /v3/config 里抽模型 id。"""
    ids = set()
    data = cat.get("data") or {}
    for agent in data.get("agents") or []:
        for m in agent.get("models") or []:
            if isinstance(m, str):
                ids.add(m)
    # 也可能在 models 表里
    for m in data.get("models") or []:
        if isinstance(m, dict) and m.get("id"):
            ids.add(m["id"])
        elif isinstance(m, str):
            ids.add(m)
    return ids


for label, url, cred in [
    ("国内 CN   ", "https://www.codebuddy.cn/v3/config", cn),
    ("国际 GLOBAL", "https://www.workbuddy.ai/v3/config", gl),
]:
    print("=" * 70)
    print(label, url)
    try:
        cat = get(url, cred, None)
        ids = model_ids(cat)
        print(f"  模型数: {len(ids)}")
        has = "deepseek-v4.1-flash" in ids
        print(f"  包含 deepseek-v4.1-flash: {'是' if has else '否'}")
        print(f"  示例: {sorted(ids)[:12]}")
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {e}")
    print()
