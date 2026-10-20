#!/usr/bin/env python3
"""Build every trip: <slug>/trip.json + template.html -> <slug>/index.html, then the home page.

Usage:  python3 build.py            # build all trips
        python3 build.py <slug>     # build one trip (home page is always rebuilt)
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = (ROOT / "template.html").read_text(encoding="utf-8")
SECRET_PATTERNS = [  # things that must never reach a public page
    (r"(确认号|订单号|预订号|confirmation|booking\s*(no|number|ref)|PNR)\s*[:：#]?\s*[A-Z0-9]{5,}", "确认号/订单号"),
    (r"(护照|passport|身份证|ID\s*card)\s*[:：#]?\s*[A-Z0-9]{6,}", "证件号"),
    (r"(房间号|room\s*(no|number|#))\s*[:：]?\s*\d+", "房间号"),
    (r"(密码|password|门锁码|lockbox|door\s*code)\s*[:：]?\s*\S+", "密码/门锁码"),
]


def check_secrets(slug, raw):
    hits = [label for pat, label in SECRET_PATTERNS if re.search(pat, raw, re.I)]
    if hits:
        sys.exit(f"✗ {slug}/trip.json 里疑似含有敏感信息：{', '.join(hits)}。公开网页不能写这些，请删除后再构建。")


def build_trip(d: Path):
    raw = (d / "trip.json").read_text(encoding="utf-8")
    check_secrets(d.name, raw)
    trip = json.loads(raw)
    data = json.dumps(trip, ensure_ascii=False, indent=1).replace("</", "<\\/")
    out = TEMPLATE.replace("__TRIP_JSON__", data).replace("__TRIP_TITLE__", html.escape(trip["title"]))
    (d / "index.html").write_text(out, encoding="utf-8")
    print(f"✓ {d.name}/index.html")
    return trip


def build_home(trips):
    trips = sorted(trips, key=lambda t: t[1].get("dates", {}).get("start", ""), reverse=True)
    cards = "".join(
        f'<a class="t" href="{slug}/"><span class="e">{html.escape(t.get("emoji", "🧳"))}</span>'
        f'<span><b>{html.escape(t["title"])}</b><small>{html.escape(t.get("dates", {}).get("start", ""))} → '
        f'{html.escape(t.get("dates", {}).get("end", ""))}{" · " + html.escape(t["route"]) if t.get("route") else ""}</small></span></a>'
        for slug, t in trips if not t.get("unlisted")
    ) or "<p>还没有行程。</p>"
    page = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Travel Plan</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧳</text></svg>">
<style>
:root{{--bg:#f6f2ea;--paper:#fffdf8;--ink:#2b2622;--muted:#7c7268;--line:#e7dfd2}}
@media (prefers-color-scheme:dark){{:root{{--bg:#191714;--paper:#23201c;--ink:#ece6dc;--muted:#a39888;--line:#37322b}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}}
.w{{max-width:640px;margin:0 auto;padding:40px 16px}} h1{{margin:0 0 4px}} p{{color:var(--muted);margin:0 0 20px}}
.t{{display:flex;gap:14px;align-items:center;background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px;text-decoration:none;color:inherit}}
.e{{font-size:28px}} b{{display:block}} small{{color:var(--muted)}}
</style></head><body><div class="w"><h1>🧳 Travel Plan</h1><p>我们的旅行手册</p>{cards}</div></body></html>"""
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    print("✓ index.html")


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    trips = []
    for d in sorted(p for p in ROOT.iterdir() if (p / "trip.json").is_file()):
        trips.append((d.name, build_trip(d) if (only in (None, d.name)) else json.loads((d / "trip.json").read_text(encoding="utf-8"))))
    build_home(trips)


if __name__ == "__main__":
    main()
