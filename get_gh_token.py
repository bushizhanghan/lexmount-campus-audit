# -*- coding: utf-8 -*-
"""get_gh_token.py — 从 Windows 凭据管理器取 GitHub token 并写入临时文件。"""
import ctypes
import ctypes.wintypes as wt
import io
import sys
import pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CRED_TYPE_GENERIC = 1


class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wt.DWORD), ("Type", wt.DWORD),
        ("TargetName", wt.LPWSTR), ("Comment", wt.LPWSTR),
        ("LastWritten", wt.FILETIME),
        ("CredentialBlobSize", wt.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wt.DWORD), ("AttributeCount", wt.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wt.LPWSTR), ("UserName", wt.LPWSTR),
    ]


advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
advapi32.CredReadW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD,
                               ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
advapi32.CredReadW.restype = wt.BOOL
advapi32.CredFree.argtypes = [ctypes.POINTER(CREDENTIAL)]


def read(target):
    p = ctypes.POINTER(CREDENTIAL)()
    if not advapi32.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(p)):
        return None
    try:
        c = p.contents
        size = c.CredentialBlobSize
        if not (size and c.CredentialBlob):
            return {"user": c.UserName, "secret": ""}
        raw = ctypes.string_at(c.CredentialBlob, size)
        return {"user": c.UserName, "secret": raw.decode("utf-16-le").rstrip("\x00")}
    finally:
        advapi32.CredFree(p)


for t in ["git:https://github.com", "git:https://bushizhanghan@github.com"]:
    r = read(t)
    if r and r["secret"].startswith(("ghp_", "github_pat_")):
        s = r["secret"]
        print(f"✓ {t}")
        print(f"  用户: {r['user']}  长度: {len(s)}  前缀: {s[:8]}")
        out = pathlib.Path(r"E:\dsh\output\gh-pages-site\.gh_token.tmp")
        out.write_text(s, "utf-8")
        print(f"  已写入 {out.name}")
        break
else:
    print("未找到 GitHub token")
