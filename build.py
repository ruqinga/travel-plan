#!/usr/bin/env python3
"""Build every trip: <slug>/trip.json + template.html -> <slug>/index.html, then the home dashboard.

Usage:  python3 build.py            # build all trips
        python3 build.py <slug>     # build one trip (home page is always rebuilt)
"""
import html, json, re, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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


def load(d: Path):
    raw = (d / "trip.json").read_text(encoding="utf-8")
    check_secrets(d.name, raw)
    trip = json.loads(raw)
    trip["_slug"] = d.name
    return trip


def build_trip(d: Path, trip):
    data = json.dumps(trip, ensure_ascii=False, indent=1).replace("</", "<\\/")
    out = TEMPLATE.replace("__TRIP_JSON__", data).replace("__TRIP_TITLE__", html.escape(trip["title"]))
    (d / "index.html").write_text(out, encoding="utf-8")
    print(f"✓ {d.name}/index.html")


def ms(local: str, tz: str) -> int:
    return int(datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(tz)).timestamp() * 1000)


def summary(t):
    """Compact per-trip data for the home dashboard (countdowns are computed in the browser)."""
    tz = t.get("tz", "UTC")
    ev = []
    for f in t.get("flights", []):
        ev.append([ms(f["depart"], f["from"].get("tz", tz)), f"{f['from']['code']} → {f['to']['code']} 出发"])
    for d in t.get("days", []):
        for it in d.get("items", []):
            if it.get("time") and not it.get("flight") and it.get("countdown", True):
                ev.append([ms(f"{d['date']}T{it['time']}", it.get("tz", d.get("tz", tz))), it["title"]])
    ev.sort()
    todos = t.get("todos", [])
    nxt = next((x["text"] for x in todos if not x.get("done")), None)
    dates = t.get("dates", {})
    return {
        "slug": t["_slug"], "title": t["title"], "emoji": t.get("emoji", "🧳"), "category": t.get("category", "未分类"),
        "route": t.get("route", ""), "people": t.get("people"), "track": bool(t.get("track")),
        "start": dates.get("start", ""), "end": dates.get("end", dates.get("start", "")), "tz": tz,
        # trip window in ms: from start-of-day of first date to end-of-day of last date (trip time zone)
        "t0": ms(dates["start"] + "T00:00", tz) if dates.get("start") else 0,
        "t1": ms(dates.get("end", dates.get("start")) + "T23:59", tz) if dates.get("start") else 0,
        "events": ev, "todoDone": sum(1 for x in todos if x.get("done")), "todoAll": len(todos), "nextTodo": nxt,
        "pending": [s["text"] for s in t.get("status", []) if s.get("ok") is False],
    }


HOME = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="robots" content="noindex">
<title>Travel Plan</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧳</text></svg>">
<style>
:root{--bg:#f6f2ea;--paper:#fffdf8;--ink:#2b2622;--muted:#7c7268;--line:#e7dfd2;--accent:#c8402f;--accent-soft:#fbe6e1;
--ok:#2f8a57;--ok-soft:#e3f3e8;--info:#2d6fb0;--info-soft:#e3eef9;--star:#b27a00;--star-soft:#fdf0d8;
--shadow:0 1px 2px rgba(60,40,20,.06),0 6px 20px rgba(60,40,20,.06);--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#191714;--paper:#23201c;--ink:#ece6dc;--muted:#a39888;--line:#37322b;--accent:#ff7a63;--accent-soft:#3d2520;
--ok:#6cc792;--ok-soft:#1f3328;--info:#7fb3e8;--info-soft:#1d2b3a;--star:#f0b04a;--star-soft:#3a2d17;--shadow:0 1px 2px rgba(0,0,0,.3),0 6px 20px rgba(0,0,0,.25)}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif}
.w{max-width:760px;margin:0 auto;padding:28px 16px 60px}
h1{margin:0;font-size:26px} .sub{color:var(--muted);font-size:13px;margin:2px 0 14px}
.filters{position:sticky;top:0;z-index:5;display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;margin:0 -16px;padding:10px 16px;
background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.filters::-webkit-scrollbar{display:none}
.filters button{flex:none;font:inherit;font-size:13px;padding:5px 13px;border-radius:999px;border:1px solid var(--line);background:var(--paper);color:var(--ink);cursor:pointer}
.filters button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.filters button small{opacity:.6;margin-left:3px}
h2{font-size:15px;margin:24px 0 10px;color:var(--muted);letter-spacing:1px;display:flex;align-items:center;gap:6px}
.card{position:relative;display:block;background:var(--paper);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:14px 16px;margin-bottom:10px;text-decoration:none;color:inherit}
.row{display:flex;gap:12px;align-items:flex-start}
.e{font-size:28px;line-height:1.2}
.ti{font-weight:700;font-size:16px;padding-right:44px}
.m{font-size:12.5px;color:var(--muted)}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}
.tag{font-size:11.5px;padding:0 8px;border-radius:999px;background:var(--info-soft);color:var(--info)}
.tag.when{background:var(--ok-soft);color:var(--ok)} .tag.p{background:var(--accent-soft);color:var(--accent)}
.star{position:absolute;top:10px;right:10px;width:36px;height:36px;border-radius:50%;border:1px solid var(--line);background:var(--paper);color:var(--muted);font-size:17px;cursor:pointer;line-height:1}
.star.on{color:var(--star);background:var(--star-soft);border-color:transparent}
.live{margin-top:10px;padding-top:10px;border-top:1px dashed var(--line)}
.live .lb{font-size:11px;letter-spacing:2px;color:var(--muted)}
.live .ev{font-weight:600;font-size:14px}
.cd{font-family:var(--mono);font-size:24px;font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums}
.prog{height:5px;border-radius:3px;background:var(--line);overflow:hidden;margin-top:8px}.prog i{display:block;height:100%;background:var(--ok)}
.todo{font-size:12.5px;margin-top:6px}.todo b{font-size:11px;padding:0 7px;border-radius:999px;background:var(--accent);color:#fff;font-weight:500;margin-right:6px}
details summary{cursor:pointer;color:var(--muted);font-size:15px;margin:24px 0 10px;letter-spacing:1px;font-weight:700}
.empty{color:var(--muted);font-size:13.5px;background:var(--paper);border:1px dashed var(--line);border-radius:14px;padding:14px 16px}
footer{margin-top:36px;text-align:center;font-size:12px;color:var(--muted)}
</style></head><body><div class="w">
<h1>🧳 Travel Plan</h1><div class="sub" id="sub"></div>
<div class="filters" id="filters"></div>
<div id="list"></div>
<footer>点 ☆ 追踪行程：追踪的行程置顶并显示实时倒计时（只保存在这台设备的浏览器里）。</footer>
</div>
<script id="trips" type="application/json">__TRIPS__</script>
<script>
(function(){
const TRIPS = JSON.parse(document.getElementById('trips').textContent);
const KEY='travelplan.tracked', FKEY='travelplan.filter';
const esc = s => String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const get=(k,d)=>{try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v)}catch(e){return d}};
const set=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let trackMap = get(KEY,{}), filter = get(FKEY,'all');
const tracked = t => (t.slug in trackMap) ? !!trackMap[t.slug] : t.track;
const WD=['日','一','二','三','四','五','六'];
const fd = s => { const [Y,M,D]=s.split('-').map(Number); return `${M}/${D}（周${WD[new Date(Date.UTC(Y,M-1,D)).getUTCDay()]}）`; };
const phase = (t,now) => now < t.t0 ? 'up' : (now <= t.t1 ? 'on' : 'past');
const cats = [...new Set(TRIPS.map(t=>t.category))];

function when(t, now){
  const p = phase(t,now);
  if(p==='up'){ const d=Math.ceil((t.t0-now)/864e5); return `还有 ${d} 天`; }
  if(p==='on'){ return `进行中 · 第 ${Math.floor((now-t.t0)/864e5)+1} 天`; }
  return '已结束';
}
function card(t, now, live){
  const on = tracked(t), p = phase(t,now);
  const pct = t.todoAll ? Math.round(t.todoDone/t.todoAll*100) : 0;
  let h = `<a class="card" href="${esc(t.slug)}/" data-slug="${esc(t.slug)}"><div class="row"><div class="e">${esc(t.emoji)}</div><div style="flex:1;min-width:0">
    <div class="ti">${esc(t.title)}</div>
    <div class="m">${fd(t.start)} → ${fd(t.end)}${t.people?` · ${t.people} 人`:''}${t.route?` · ${esc(t.route)}`:''}</div>
    <div class="tags"><span class="tag when">${when(t,now)}</span><span class="tag">${esc(t.category)}</span>${p!=='past'&&t.pending.length?`<span class="tag p">${t.pending.length} 项待办预订</span>`:''}</div>`;
  if(live && p!=='past'){
    h += `<div class="live"><div class="lb">下一项 · NEXT</div><div class="ev" data-ev></div><div class="cd" data-cd></div>
      ${t.todoAll?`<div class="prog"><i style="width:${pct}%"></i></div><div class="m">待办 ${t.todoDone}/${t.todoAll}</div>`:''}
      ${t.nextTodo?`<div class="todo"><b>当前待办</b>${esc(t.nextTodo)}</div>`:''}</div>`;
  }
  h += `</div></div><button class="star ${on?'on':''}" type="button" aria-label="${on?'取消追踪':'追踪'}" data-star="${esc(t.slug)}">${on?'★':'☆'}</button></a>`;
  return h;
}
function render(){
  const now = Date.now();
  const counts = {all:TRIPS.length, tracked:TRIPS.filter(tracked).length};
  cats.forEach(c=>counts['c:'+c]=TRIPS.filter(t=>t.category===c).length);
  if(filter!=='all' && filter!=='tracked' && !counts[filter]) filter='all';
  const fb = [['all','全部'],['tracked','★ 追踪'],...cats.map(c=>['c:'+c,c])];
  document.getElementById('filters').innerHTML = fb.map(([k,l])=>`<button type="button" data-f="${esc(k)}" class="${filter===k?'on':''}">${esc(l)}<small>${counts[k]||0}</small></button>`).join('');
  const up = TRIPS.filter(t=>phase(t,now)!=='past').length;
  document.getElementById('sub').textContent = `${TRIPS.length} 个行程 · ${up} 个进行中/即将出发 · ${counts.tracked} 个追踪中`;

  const pass = t => filter==='all' || (filter==='tracked' ? tracked(t) : t.category===filter.slice(2));
  const vis = TRIPS.filter(pass);
  const tr = vis.filter(t=>tracked(t) && phase(t,now)!=='past').sort((a,b)=>a.t0-b.t0);
  const rest = vis.filter(t=>!tr.includes(t));
  const on = rest.filter(t=>phase(t,now)==='on').sort((a,b)=>a.t0-b.t0);
  const upc = rest.filter(t=>phase(t,now)==='up').sort((a,b)=>a.t0-b.t0);
  const past = rest.filter(t=>phase(t,now)==='past').sort((a,b)=>b.t0-a.t0);
  let h='';
  if(tr.length) h += `<h2>★ 追踪中</h2>` + tr.map(t=>card(t,now,true)).join('');
  else if(filter==='tracked'||filter==='all') h += `<h2>★ 追踪中</h2><div class="empty">还没有追踪的行程。点行程卡片右上角的 ☆，它就会置顶并显示实时倒计时。</div>`;
  if(on.length) h += `<h2>🟢 进行中</h2>` + on.map(t=>card(t,now,false)).join('');
  if(upc.length) h += `<h2>🗓️ 即将出发</h2>` + upc.map(t=>card(t,now,false)).join('');
  if(past.length) h += `<details ${filter!=='all'?'open':''}><summary>📦 已结束（${past.length}）</summary>${past.map(t=>card(t,now,false)).join('')}</details>`;
  if(!vis.length) h += `<div class="empty">这个分类下还没有行程。</div>`;
  document.getElementById('list').innerHTML = h;
  tick();
}
function tick(){
  const now = Date.now(), p2 = n=>String(n).padStart(2,'0');
  document.querySelectorAll('.card .live').forEach(el=>{
    const t = TRIPS.find(x=>x.slug===el.closest('.card').dataset.slug);
    const e = t.events.find(e=>e[0]>now);
    if(!e){ el.querySelector('[data-ev]').textContent='行程安排已全部结束'; el.querySelector('[data-cd]').textContent=''; return; }
    let s=Math.floor((e[0]-now)/1000); const D=Math.floor(s/86400); s%=86400;
    el.querySelector('[data-ev]').textContent = e[1];
    el.querySelector('[data-cd]').textContent = `${D?D+'天 ':''}${p2(Math.floor(s/3600))}:${p2(Math.floor(s%3600/60))}:${p2(s%60)}`;
  });
}
document.addEventListener('click', ev=>{
  const st = ev.target.closest('[data-star]');
  if(st){ ev.preventDefault(); const t=TRIPS.find(x=>x.slug===st.dataset.star); trackMap[t.slug]=!tracked(t); set(KEY,trackMap); render(); return; }
  const f = ev.target.closest('[data-f]');
  if(f){ filter=f.dataset.f; set(FKEY,filter); render(); }
});
window.addEventListener('pageshow', ()=>{ trackMap=get(KEY,{}); render(); });
render(); setInterval(tick,1000);
})();
</script></body></html>"""


def build_home(trips):
    data = [summary(t) for t in trips if not t.get("unlisted")]
    out = HOME.replace("__TRIPS__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"✓ index.html（{len(data)} 个行程）")


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    dirs = sorted(p for p in ROOT.iterdir() if (p / "trip.json").is_file())
    if only and not any(d.name == only for d in dirs):
        sys.exit(f"✗ 找不到 {only}/trip.json")
    trips = []
    for d in dirs:
        t = load(d)
        if only in (None, d.name):
            build_trip(d, t)
        trips.append(t)
    build_home(trips)


if __name__ == "__main__":
    main()
