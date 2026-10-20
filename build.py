#!/usr/bin/env python3
"""Build every trip: <slug>/trip.json + template.html -> <slug>/index.html, then the home page.

Usage:  python3 build.py            # build all trips
        python3 build.py <slug>     # build one trip (home page is always rebuilt)
"""
import html, json, re, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = (ROOT / "template.html").read_text(encoding="utf-8")
# image export library, inlined so every page stays a single self-contained file
H2I = re.sub(r"//# sourceMappingURL=.*", "", (ROOT / "vendor" / "html-to-image.js").read_text(encoding="utf-8"))
SECRET_PATTERNS = [  # things that must never reach a public page
    (r"(确认号|订单号|预订号|confirmation|booking\s*(no|number|ref)|PNR)\s*[:：#]?\s*[A-Z0-9]{5,}", "确认号/订单号"),
    (r"(护照|passport|身份证|ID\s*card)\s*[:：#]?\s*[A-Z0-9]{6,}", "证件号"),
    (r"(房间号|room\s*(no|number|#))\s*[:：]?\s*\d+", "房间号"),
    (r"(密码|password|门锁码|lockbox|door\s*code)\s*[:：]?\s*\S+", "密码/门锁码"),
]
THEMES = {"forest": ["#3d6b3a", "#86b780"], "sea": ["#2d6a96", "#7fb0d8"], "terracotta": ["#a8492c", "#ef8f6c"],
          "plum": ["#6e4a8a", "#b896d6"], "olive": ["#6b6a2a", "#c2c06a"]}


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
    out = (TEMPLATE.replace("__TRIP_JSON__", data)
           .replace("__TRIP_TITLE__", html.escape(trip["title"]))
           .replace("__HTML_TO_IMAGE__", H2I.replace("</", "<\\/")))
    (d / "index.html").write_text(out, encoding="utf-8")
    print(f"✓ {d.name}/index.html")


def n_days(t):
    ds = t.get("dates") or {}
    if ds.get("start"):
        return (date.fromisoformat(ds.get("end") or ds["start"]) - date.fromisoformat(ds["start"])).days + 1
    return t.get("length") or len(t.get("days", [])) or 1


def summary(t):
    """Compact per-trip data for the home page; status is computed in the browser from the dates."""
    ds = t.get("dates") or {}
    th = THEMES.get(t.get("theme"), THEMES["forest"]) if not str(t.get("theme", "")).startswith("#") else [t["theme"]] * 2
    hk = (t.get("hikes") or [{}])[0]
    return {
        "slug": t["_slug"], "title": t["title"], "subtitle": t.get("subtitle", ""), "c": th,
        "start": ds.get("start"), "end": ds.get("end") or ds.get("start"), "n": n_days(t),
        "dest": t.get("dest", ""), "mode": t.get("mode", ""), "budget": (t.get("budget") or {}).get("total", ""),
        "distance": t.get("distance", ""), "types": t.get("types", []), "pinned": t.get("pinned", False),
        "hike": [x for x in (hk.get("distance"), ("↑" + hk["gain"]) if hk.get("gain") else None) if x],
        "nhikes": len(t.get("hikes") or []),
    }


HOME = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="robots" content="noindex">
<title>Travel Plan</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧭</text></svg>">
<style>
:root{--bg:#f5efe3;--paper:#fffbf2;--ink:#2a2620;--muted:#7a6f60;--line:#eadcc0;--sand:#f2deb0;--sand-ink:#5e4515;--accent:#bf5236;--brand:#3d6b3a}
@media (prefers-color-scheme:dark){:root{--bg:#171512;--paper:#221f1a;--ink:#eee6d8;--muted:#a69a88;--line:#3a332a;--sand:#3d3220;--sand-ink:#ecc982;--accent:#f07a5c;--brand:#86b780}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif}
.w{max-width:820px;margin:0 auto;padding:26px 16px 60px}
h1{margin:0;font-size:30px;font-weight:800;color:var(--brand);letter-spacing:.5px}
.sub{color:var(--muted);font-size:13px;margin:2px 0 12px}
.filters{position:sticky;top:0;z-index:5;margin:0 -16px;padding:8px 16px 6px;background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.fr{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding:3px 0;align-items:center}
.fr::-webkit-scrollbar{display:none}
.fr .lb{flex:none;font-size:12px;color:var(--muted);width:30px}
.fr button{flex:none;font:inherit;font-size:13px;padding:3px 12px;border-radius:999px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink);cursor:pointer}
.fr button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
h2{font-size:14px;margin:22px 0 10px;color:var(--muted);letter-spacing:1.5px;font-weight:800;display:flex;gap:8px;align-items:center}
h2 b{font-size:11px;font-weight:700;padding:0 8px;border-radius:999px;background:var(--line);color:var(--muted);letter-spacing:0}
.card{--k:var(--c);position:relative;display:block;background:var(--paper);border:2px solid var(--line);border-left:7px solid var(--k);border-radius:18px;padding:13px 16px 12px;margin-bottom:10px;text-decoration:none;color:inherit}
@media (prefers-color-scheme:dark){.card{--k:var(--cd)}}
.ti{font-weight:800;font-size:17px;line-height:1.35;color:var(--k);padding-right:42px}
.st2{font-size:13px;color:var(--accent);font-weight:700}
.when{font-size:12.5px;color:var(--muted);margin-top:2px}
.when b{color:var(--ink)}
.facts{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;margin-top:6px}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.tag{font-size:11.5px;padding:0 9px;border-radius:999px;background:var(--sand);color:var(--sand-ink);font-weight:600}
.tag.d{background:color-mix(in srgb,var(--k) 14%,var(--paper));color:var(--k)}
.pin{position:absolute;top:9px;right:9px;width:36px;height:36px;border-radius:50%;border:1.5px solid var(--line);background:var(--paper);font-size:16px;cursor:pointer;filter:grayscale(1);opacity:.55}
.pin.on{filter:none;opacity:1;background:var(--sand);border-color:transparent}
.ongo{position:absolute;top:12px;right:12px;font-size:11.5px;font-weight:700;padding:1px 9px;border-radius:999px;background:var(--k);color:#fff}
details summary{cursor:pointer;color:var(--muted);font-size:14px;margin:22px 0 10px;letter-spacing:1.5px;font-weight:800}
.gone .card{opacity:.82}
.empty{color:var(--muted);font-size:13.5px;border:2px dashed var(--line);border-radius:16px;padding:14px 16px}
footer{margin-top:32px;text-align:center;font-size:12px;color:var(--muted)}
</style></head><body><div class="w">
<h1>Travel Plan</h1><div class="sub" id="sub"></div>
<div class="filters" id="filters"></div>
<div id="list"></div>
<footer>状态按日期自动切换 · 📌 置顶跟随行程数据，点图钉只改这台设备</footer>
</div>
<script id="trips" type="application/json">__TRIPS__</script>
<script>
(function(){
const TRIPS = JSON.parse(document.getElementById('trips').textContent);
const PKEY='travelplan.pins', FKEY='travelplan.filters';
const esc = s => String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const get=(k,d)=>{try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v)}catch(e){return d}};
const set=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let pins = get(PKEY,{}), F = Object.assign({n:'all',dist:'all',type:'all'}, get(FKEY,{}));
const WD=['日','一','二','三','四','五','六'];
const fd = s => { const [Y,M,D]=s.split('-').map(Number); return `${M}/${D}（周${WD[new Date(Date.UTC(Y,M-1,D)).getUTCDay()]}）`; };
const today = (()=>{ const p={}; new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).forEach(x=>p[x.type]=x.value); return `${p.year}-${p.month}-${p.day}`; })();
const dd = (a,b) => Math.round((Date.parse(b)-Date.parse(a))/864e5);
const status = t => !t.start || today < t.start ? 'plan' : (today <= t.end ? 'on' : 'gone');
const nTag = n => n===1 ? '一日' : (n<=3 ? '2–3 日' : '4 日+');
const pinVal = t => (t.slug in pins) ? pins[t.slug] : (t.pinned ? (typeof t.pinned==='number' ? t.pinned : 1) : 0);

function card(t){
  const s = status(t), pv = pinVal(t);
  let when;
  if(!t.start) when = '日期待定';
  else if(s==='plan') when = `${fd(t.start)}${t.end!==t.start?' – '+fd(t.end):''} · <b>还有 ${dd(today,t.start)} 天</b>`;
  else if(s==='on') when = `<b>第 ${dd(t.start,today)+1} / ${t.n} 天</b> · ${fd(t.start)} – ${fd(t.end)}`;
  else when = `${fd(t.start)}${t.end!==t.start?' – '+fd(t.end):''}`;
  const facts = [['🗓️', t.n===1?'一日':`${t.n} 天`], ['📍',t.dest], ['🚌',t.mode], ['💶',t.budget], ['🥾', t.hike.join(' ') + (t.nhikes>1?` 等 ${t.nhikes} 条`:'')]].filter(x=>x[1]);
  return `<a class="card" href="${esc(t.slug)}/" style="--c:${t.c[0]};--cd:${t.c[1]}">
    <div class="ti">${esc(t.title)}</div>${t.subtitle?`<div class="st2">${esc(t.subtitle)}</div>`:''}
    <div class="when">${when}</div>
    <div class="facts">${facts.map(f=>`<span>${f[0]} ${esc(f[1])}</span>`).join('')}</div>
    <div class="tags"><span class="tag d">${nTag(t.n)}</span>${t.distance?`<span class="tag d">${esc(t.distance)}</span>`:''}${t.types.map(x=>`<span class="tag">${esc(x)}</span>`).join('')}</div>
    ${s==='plan'?`<button class="pin ${pv?'on':''}" type="button" data-pin="${esc(t.slug)}" aria-label="${pv?'取消置顶':'置顶'}">📌</button>`:''}
    ${s==='on'?'<span class="ongo">旅途中</span>':''}</a>`;
}
function render(){
  const opts = {
    n: ['一日','2–3 日','4 日+'].filter(x=>TRIPS.some(t=>nTag(t.n)===x)),
    dist: [...new Set(['近郊','周边','远途',...TRIPS.map(t=>t.distance)])].filter(x=>x&&TRIPS.some(t=>t.distance===x)),
    type: [...new Set(TRIPS.flatMap(t=>t.types))],
  };
  for(const k in opts) if(F[k]!=='all' && !opts[k].includes(F[k])) F[k]='all';
  const row = (k,lb) => opts[k].length ? `<div class="fr"><span class="lb">${lb}</span>${['all',...opts[k]].map(v=>`<button type="button" data-k="${k}" data-v="${esc(v)}" class="${F[k]===v?'on':''}">${v==='all'?'全部':esc(v)}</button>`).join('')}</div>` : '';
  document.getElementById('filters').innerHTML = row('n','天数') + row('dist','距离') + row('type','类型');
  const vis = TRIPS.filter(t=>(F.n==='all'||nTag(t.n)===F.n) && (F.dist==='all'||t.distance===F.dist) && (F.type==='all'||t.types.includes(F.type)));
  const on = vis.filter(t=>status(t)==='on').sort((a,b)=>a.start<b.start?-1:1);
  const plan = vis.filter(t=>status(t)==='plan').sort((a,b)=>{
    const pa=pinVal(a), pb=pinVal(b);
    if(!!pa!==!!pb) return pa?-1:1;
    if(pa&&pb&&pa!==pb) return pa-pb;
    if(!!a.start!==!!b.start) return a.start?-1:1;
    return (a.start||'')<(b.start||'')?-1:(a.start||'')>(b.start||'')?1:a.title.localeCompare(b.title,'zh');
  });
  const gone = vis.filter(t=>status(t)==='gone').sort((a,b)=>a.start<b.start?1:-1);
  document.getElementById('sub').textContent = `${TRIPS.filter(t=>status(t)==='plan').length} 个计划 · ${TRIPS.filter(t=>status(t)==='on').length} 个进行中 · ${TRIPS.filter(t=>status(t)==='gone').length} 个已完成`;
  let h = '';
  if(on.length) h += `<h2>ONGOING · 旅途中<b>${on.length}</b></h2>` + on.map(card).join('');
  h += `<h2>PLAN TO GO · 计划<b>${plan.length}</b></h2>` + (plan.length ? plan.map(card).join('') : `<div class="empty">没有符合筛选的计划。</div>`);
  if(gone.length) h += `<details class="gone" ${F.n!=='all'||F.dist!=='all'||F.type!=='all'?'open':''}><summary>GONE · 已完成（${gone.length}）</summary>${gone.map(card).join('')}</details>`;
  document.getElementById('list').innerHTML = h;
}
document.addEventListener('click', ev=>{
  const p = ev.target.closest('[data-pin]');
  if(p){ ev.preventDefault(); const t=TRIPS.find(x=>x.slug===p.dataset.pin); pins[t.slug] = pinVal(t) ? 0 : Date.now(); set(PKEY,pins); render(); return; }
  const f = ev.target.closest('[data-k]');
  if(f){ F[f.dataset.k] = f.dataset.v; set(FKEY,F); render(); }
});
window.addEventListener('pageshow', ()=>{ pins=get(PKEY,{}); render(); });
render();
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
