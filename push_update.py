# -*- coding: utf-8 -*-
"""push_update.py — 用 GitHub Contents API 增量更新仓库文件。

用法：python push_update.py <TOKEN>
"""
import base64
import json
import pathlib
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
OWNER = "bushizhanghan"
REPO = "lexmount-campus-audit"
SITE = pathlib.Path(r"E:\dsh\output\gh-pages-site")

TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
if not TOKEN:
    print("需要 token")
    sys.exit(1)


def req(method, path, body=None):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + TOKEN)
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("User-Agent", "dsh-agent")
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            txt = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(txt) if txt.strip().startswith(("{", "[")) else txt)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


# 1. 校验
code, me = req("GET", "/user")
if code != 200:
    print("token 无效:", code, me)
    sys.exit(1)
print(f"身份: {me['login']}")

# 2. 取远端当前文件树（拿 sha）
print("读取远端文件列表 ...")
existing = {}
page = 1
while True:
    code, tree = req("GET", f"/repos/{OWNER}/{REPO}/git/trees/main?recursive=1")
    if code != 200:
        print("读取失败:", code, str(tree)[:200])
        sys.exit(1)
    for item in tree.get("tree", []):
        if item["type"] == "blob":
            existing[item["path"]] = item["sha"]
    break
print(f"  远端 {len(existing)} 个文件")

# 3. 上传本地文件
SKIP_SUFFIX = {".tmp"}
local = []
for p in sorted(SITE.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(SITE).as_posix()
    if rel.startswith(".git/") or p.suffix in SKIP_SUFFIX:
        continue
    if rel in ("push-to-github-pages.ps1",):
        continue
    local.append((p, rel))

print(f"待上传 {len(local)} 个文件")
ok = skip = fail = 0
fails = []

for p, rel in local:
    content = p.read_bytes()
    b64 = base64.b64encode(content).decode("ascii")

    # 同内容且大小一致则跳过（省配额）
    remote_sha = existing.get(rel)
    if remote_sha:
        c2, ex = req("GET", f"/repos/{OWNER}/{REPO}/contents/{rel}")
        if c2 == 200 and isinstance(ex, dict) and ex.get("size") == len(content):
            skip += 1
            continue

    body = {"message": f"update {rel}", "content": b64, "branch": "main"}
    if remote_sha:
        body["sha"] = remote_sha

    code, res = req("PUT", f"/repos/{OWNER}/{REPO}/contents/{rel}", body)
    if code in (200, 201):
        ok += 1
        print(f"  ✓ {rel} ({len(content):,} B)")
    else:
        fail += 1
        fails.append((rel, code, str(res)[:150]))
        print(f"  ✗ {rel}: {code}")

print(f"\n上传: {ok} 成功 / {skip} 跳过 / {fail} 失败")
for f in fails:
    print("  ", f)

print(f"\n站点: https://{OWNER}.github.io/{REPO}/")
