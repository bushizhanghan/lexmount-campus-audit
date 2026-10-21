# -*- coding: utf-8 -*-
import json, io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = pathlib.Path(r"E:\dsh\output\webfetch-playground\project\report_data.json")
d = json.loads(p.read_text(encoding="utf-8"))
for s in sorted(d["sites"], key=lambda x: -(x.get("text_len") or 0)):
    print(f"{s['name']:<14} ok={s.get('ok')} status={s.get('status')} len={s.get('text_len')} links={s.get('link_count')}")
