#!/usr/bin/env python3
"""Build every trip: <slug>/trip.json + template.html -> <slug>/index.html, then the home page.

Usage:  python3 build.py            # build all trips
        python3 build.py <slug>     # build one trip (home page is always rebuilt)
"""
import html, json, re, sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
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
THEMES = {"forest": ["#28a148", "#30d158"], "sea": ["#1a8fb5", "#40c8e0"], "terracotta": ["#e5631f", "#ff9f0a"],
          "plum": ["#a54fd6", "#bf5af2"], "olive": ["#8d7b55", "#ac8e68"]}


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


def ms(local: str, tz: str) -> int:
    return int(datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(tz)).timestamp() * 1000)


def events(t):
    """Countdown targets [[epoch_ms, title, sub], ...] sorted; needs real dates. Times are local to each item's tz."""
    ds = t.get("dates") or {}
    if not ds.get("start"):
        return []
    tz, ev = t.get("tz", "Europe/Madrid"), []
    icon = {"train": "🚄", "bus": "🚌", "ferry": "⛴"}
    for f in t.get("flights", []):
        ev.append([ms(f["depart"], f["from"].get("tz", tz)), f"{f['from']['code']} {icon.get(f.get('mode'), '✈')} {f['to']['code']} 出发",
                   " · ".join(x for x in (f.get("airline"), f.get("number"), f.get("duration"), f.get("note")) if x)])
    for i, d in enumerate(t.get("days", [])):
        day = d.get("date") or (date.fromisoformat(ds["start"]) + timedelta(days=i)).isoformat()
        for it in d.get("items", []):
            if it.get("time") and it.get("title") and not it.get("flight") and it.get("countdown", True) and re.match(r"^\d{1,2}:\d{2}$", it["time"]):
                ev.append([ms(f"{day}T{it['time']:0>5}", it.get("tz", d.get("tz", tz))), it["title"],
                           " · ".join(x for x in (d.get("badge") or f"第 {i + 1} 天", it.get("note")) if x)])
    if not ev:
        ev.append([ms(ds["start"] + "T00:00", tz), "出发日", ""])
    return sorted(ev)


def build_trip(d: Path, trip):
    trip = dict(trip, _events=events(trip))
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
        "sched": day_items(t),
        "ev": [e[:2] for e in events(t)],
    }


def day_items(t):
    """{date: [[time, title], ...]} for the ongoing card's 'today' list (needs real dates)."""
    ds = t.get("dates") or {}
    if not ds.get("start"):
        return {}
    out = {}
    for i, d in enumerate(t.get("days", [])):
        day = d.get("date") or (date.fromisoformat(ds["start"]) + timedelta(days=i)).isoformat()
        out[day] = [[it.get("time", ""), it["title"]] for it in d.get("items", []) if it.get("title")]
    return out


HOME = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="robots" content="noindex">
<meta name="theme-color" content="#f2f2f7" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="行旅">
<title>行旅</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%23ff3b30'/><text x='50' y='68' font-size='54' text-anchor='middle' fill='white' font-family='-apple-system,PingFang SC,sans-serif' font-weight='700'>行</text></svg>">
<style>
:root{--bg:#f2f2f7;--paper:#fff;--ink:#000;--ink2:rgba(60,60,67,.6);--ink3:rgba(60,60,67,.3);--sep:rgba(60,60,67,.18);--fill:rgba(118,118,128,.12);--press:#e5e5ea;
--tint:#007aff;--red:#ff3b30;--mat:rgba(242,242,247,.8);--seg:#fff;
--sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Pro Display","PingFang SC","Hiragino Sans GB","Helvetica Neue","Noto Sans CJK SC",sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#000;--paper:#1c1c1e;--ink:#fff;--ink2:rgba(235,235,245,.6);--ink3:rgba(235,235,245,.3);--sep:rgba(84,84,88,.6);--fill:rgba(118,118,128,.24);--press:#2c2c2e;
--tint:#0a84ff;--red:#ff453a;--mat:rgba(18,18,20,.78);--seg:#636366}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.47 var(--sans);letter-spacing:-.2px;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
svg.i{width:1em;height:1em;flex:none;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
.nb{position:sticky;top:0;z-index:20;padding-top:env(safe-area-inset-top);transition:background .2s,box-shadow .2s}
.nb.scrolled{background:var(--mat);backdrop-filter:saturate(1.8) blur(20px);-webkit-backdrop-filter:saturate(1.8) blur(20px);box-shadow:0 .5px 0 var(--sep)}
.nb .in{max-width:720px;margin:0 auto;height:44px;display:flex;align-items:center;justify-content:center}
.nb .ttl{font-size:17px;font-weight:600;opacity:0;transform:translateY(4px);transition:opacity .2s,transform .2s}
.nb.scrolled .ttl{opacity:1;transform:none}
.w{max-width:720px;margin:0 auto;padding:0 16px calc(64px + env(safe-area-inset-bottom))}
h1{margin:0;font-size:34px;line-height:1.2;font-weight:700;letter-spacing:.3px}
.sub{color:var(--ink2);font-size:15px;margin:4px 0 16px}
.seg{display:grid;grid-auto-columns:1fr;grid-auto-flow:column;background:var(--fill);border-radius:9px;padding:2px;margin:0 0 24px;position:relative}
.seg a{position:relative;z-index:1;text-align:center;font-size:13px;font-weight:500;padding:6px 4px;border-radius:7px;color:var(--ink);transition:opacity .2s}
.seg a.on{font-weight:600}
.seg a:active{opacity:.5}
.seg .thumb{position:absolute;z-index:0;top:2px;bottom:2px;left:2px;border-radius:7px;background:var(--seg);box-shadow:0 3px 8px rgba(0,0,0,.12),0 3px 1px rgba(0,0,0,.04),0 0 0 .5px rgba(0,0,0,.04);transition:transform .3s cubic-bezier(.3,.7,.2,1)}
.seg sup{font-size:10px;font-weight:700;color:var(--red);margin-left:2px}
.sh{padding:0 16px 7px;font-size:13px;color:var(--ink2);letter-spacing:.2px}
.grp{background:var(--paper);border-radius:12px;overflow:hidden;margin-bottom:28px}
.row{position:relative;display:flex;align-items:center;gap:14px;padding:12px 16px;min-height:44px;transition:background .25s}
.row+.row::before{content:"";position:absolute;top:0;right:0;left:var(--inset,82px);border-top:.5px solid var(--sep)}
a.row:active{background:var(--press);transition:none}
.ai{flex:none;width:52px;height:52px;border-radius:12px;display:grid;place-items:center;color:#fff;font-size:15px;font-weight:700;letter-spacing:.5px;
  background:linear-gradient(160deg,color-mix(in srgb,var(--k) 72%,#fff),var(--k));box-shadow:0 0 0 .5px rgba(0,0,0,.06)}
@media (prefers-color-scheme:dark){.row,.card{--k:var(--cd)!important}}
.bd{flex:1;min-width:0}
.ti{font-size:17px;font-weight:600;line-height:1.3}
.st2{font-size:15px;color:var(--ink2);margin-top:1px;line-height:1.35}
.mt{font-size:13px;color:var(--ink2);margin-top:4px;line-height:1.45}
.mt span+span::before{content:"·";margin:0 5px}
.cd{font-size:13px;font-weight:600;color:var(--red);margin-top:4px;font-variant-numeric:tabular-nums}
.cd span{color:var(--ink2);font-weight:400;margin-right:4px}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.tag{font-size:12px;font-weight:500;padding:2px 8px;border-radius:999px;background:var(--fill);color:var(--ink2)}
.tag.d{background:color-mix(in srgb,var(--k) 15%,transparent);color:var(--k);font-weight:600}
.chev{color:var(--ink3);font-size:15px;stroke-width:2.6}
.pin{flex:none;width:36px;height:36px;margin:-6px -4px -6px 0;border:0;border-radius:50%;background:none;display:grid;place-items:center;color:var(--ink3);font-size:18px;cursor:pointer}
.pin.on{color:var(--tint)} .pin.on svg{fill:currentColor}
.pin:active{opacity:.4}
.fr{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;align-items:center;margin:0 -16px 10px;padding:0 16px}
.fr::-webkit-scrollbar{display:none}
.fr .lb{flex:none;font-size:13px;color:var(--ink2);margin-right:2px}
.fr button{flex:none;font:inherit;font-size:15px;font-weight:500;padding:6px 14px;border-radius:999px;border:0;background:var(--fill);color:var(--ink);cursor:pointer;transition:background .2s,color .2s}
.fr button.on{background:var(--ink);color:var(--bg)}
.fr button:active{opacity:.6}
.filters{margin-bottom:22px}
/* ongoing card */
.card{display:block;background:var(--paper);border-radius:16px;overflow:hidden;margin-bottom:20px;transition:transform .2s}
.card:active{transform:scale(.98)}
.card .top{display:flex;gap:14px;align-items:center;padding:16px}
.card .ai{width:60px;height:60px;border-radius:14px;font-size:17px}
.card .ti{font-size:20px;font-weight:700}
.prog{height:4px;border-radius:2px;background:var(--fill);margin:0 16px;overflow:hidden}.prog i{display:block;height:100%;background:var(--k);border-radius:2px}
.card .now{padding:14px 16px 2px}
.card .now .l{font-size:13px;color:var(--ink2)}
.card .now .n{font-size:34px;font-weight:600;letter-spacing:-.5px;font-variant-numeric:tabular-nums;line-height:1.15;margin-top:2px}
.card .now .n small{font-size:15px;color:var(--ink2);font-weight:500;margin:0 4px 0 2px}
.today{padding:10px 0 6px}
.today .lb{padding:0 16px 4px;font-size:13px;color:var(--ink2)}
.today li{list-style:none;position:relative;display:flex;gap:14px;font-size:15px;padding:9px 16px;color:var(--ink)}
.today li+li::before{content:"";position:absolute;top:0;left:74px;right:0;border-top:.5px solid var(--sep)}
.today ol{margin:0;padding:0}
.today time{width:44px;flex:none;font-weight:600;font-variant-numeric:tabular-nums}
.today li.past{color:var(--ink3)}
.today li.next{font-weight:600}.today li.next time{color:var(--red)}
.today li.next::after{content:"下一项";margin-left:auto;font-size:12px;font-weight:600;color:#fff;background:var(--red);border-radius:999px;padding:0 8px;height:20px;line-height:20px;flex:none}
.empty{text-align:center;color:var(--ink2);padding:56px 24px 40px;font-size:15px}
.empty .big{font-size:22px;font-weight:700;color:var(--ink);margin-bottom:6px}
.empty a{display:inline-block;margin-top:16px;font-size:17px;color:var(--tint)}
.empty a:active{opacity:.35}
.gone .ai{filter:grayscale(.55)}
footer{margin-top:8px;text-align:center;font-size:13px;color:var(--ink2);padding:0 16px}
</style></head><body>
<header class="nb" id="nb"><div class="in"><span class="ttl" id="ttl"></span></div></header>
<div class="w" id="page"></div>
<script id="trips" type="application/json">__TRIPS__</script>
<script>
(function(){
const TRIPS = JSON.parse(document.getElementById('trips').textContent);
const PKEY='travelplan.pins', FKEY='travelplan.filters';
const esc = s => String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const get=(k,d)=>{try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v)}catch(e){return d}};
const set=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let pins = get(PKEY,{}), F = Object.assign({n:'all',dist:'all',type:'all'}, get(FKEY,{}));
const WD=['日','一','二','三','四','五','六'], CN=['','一','二','三','四','五','六','七','八','九','十'];
const fd = s => { const [Y,M,D]=s.split('-').map(Number); return `${M}月${D}日 周${WD[new Date(Date.UTC(Y,M-1,D)).getUTCDay()]}`; };
const nowParts = () => { const p={}; new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',hourCycle:'h23',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}).formatToParts(new Date()).forEach(x=>p[x.type]=x.value); return {d:`${p.year}-${p.month}-${p.day}`, t:`${p.hour}:${p.minute}`}; };
let today = nowParts().d;
const dd = (a,b) => Math.round((Date.parse(b)-Date.parse(a))/864e5);
const status = t => !t.start || today < t.start ? 'plan' : (today <= t.end ? 'on' : 'gone');
const nTag = n => n===1 ? '一日' : (n<=3 ? '2–3 日' : '4 日+');
const seal = n => n===1 ? '一日' : (CN[n]||n)+'日';
const pinVal = t => (t.slug in pins) ? pins[t.slug] : (t.pinned ? (typeof t.pinned==='number' ? t.pinned : 1) : 0);
const I = p => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const CHEV = I('<path d="M9 5l7 7-7 7"/>'), PIN = I('<path d="M9 3.5h6l-.9 5.6 3.4 3.4v1.8H6.5v-1.8l3.4-3.4z"/><path d="M12 14.3v6.2"/>');
const VIEWS = {ongoing:'在旅', plan:'计划', gone:'足迹'};
let lastVi = null;
const kv = t => `--k:${t.c[0]};--cd:${t.c[1]}`;
const p2 = n=>String(n).padStart(2,'0');

function facts(t){ return [t.dest, t.mode, t.budget, t.hike.length ? t.hike.join(' ').replace('↑约 ','↑') + (t.nhikes>1?` 等 ${t.nhikes} 条`:'') : ''].filter(Boolean); }
function row(t){
  const s = status(t), pv = pinVal(t);
  const when = !t.start ? '日期待定' : `${fd(t.start)}${t.end!==t.start?' – '+fd(t.end):''}`;
  const tags = (t.distance?`<span class="tag d">${esc(t.distance)}</span>`:'') + t.types.map(x=>`<span class="tag">${esc(x)}</span>`).join('');
  return `<a class="row" href="${esc(t.slug)}/" style="${kv(t)}"><div class="ai">${seal(t.n)}</div><div class="bd">
    <div class="ti">${esc(t.title)}</div>${t.subtitle?`<div class="st2">${esc(t.subtitle)}</div>`:''}
    <div class="mt"><span>${when}</span>${facts(t).map(f=>`<span>${esc(f)}</span>`).join('')}</div>
    ${s==='plan'&&t.ev.length?`<div class="cd" data-cd="${esc(t.slug)}"><span>距出发</span><b></b></div>`:''}
    ${tags?`<div class="tags">${tags}</div>`:''}</div>
    ${s==='plan'?`<button class="pin ${pv?'on':''}" type="button" data-pin="${esc(t.slug)}" aria-pressed="${!!pv}" aria-label="${pv?'取消置顶':'置顶'}">${PIN}</button>`:''}${CHEV}</a>`;
}
function card(t){
  const day = dd(t.start,today)+1, pct = Math.min(100, Math.round(day/t.n*100));
  let items = t.sched[today] || [], now = nowParts().t, ni = items.findIndex(x=>x[0] && x[0] >= now), lb = '今日安排';
  const tmr = new Date(Date.parse(today)+864e5).toISOString().slice(0,10);
  if(ni<0 && t.sched[tmr]){ items = t.sched[tmr]; ni = items.findIndex(x=>x[0]); now = ''; lb = '明日安排'; }
  return `<a class="card" href="${esc(t.slug)}/" style="${kv(t)}"><div class="top"><div class="ai">${seal(t.n)}</div><div class="bd">
    <div class="ti">${esc(t.title)}</div><div class="st2">第 ${day} 天，共 ${t.n} 天${t.dest?' · '+esc(t.dest):''}</div></div>${CHEV.replace('class="i"','class="i chev"')}</div>
    <div class="prog"><i style="width:${pct}%"></i></div>
    ${t.ev.length?`<div class="now" data-cd="${esc(t.slug)}"><div class="l"></div><div class="n"></div></div>`:''}
    ${items.length?`<div class="today"><div class="lb">${lb}</div><ol>${items.map((x,i)=>`<li class="${ni<0||i<ni?(x[0]&&x[0]<now?'past':''):(i===ni?'next':'')}"><time>${esc(x[0])}</time><span>${esc(x[1])}</span></li>`).join('')}</ol></div>`:''}</a>`;
}
function view(){ const v = location.hash.slice(1); return VIEWS[v] ? v : 'ongoing'; }
function render(){
  today = nowParts().d;
  const v = view(), by = k => TRIPS.filter(t=>status(t)===k);
  const on = by('on').sort((a,b)=>a.start<b.start?-1:1), allPlan = by('plan'), gone = by('gone').sort((a,b)=>a.start<b.start?1:-1);
  const keys = Object.keys(VIEWS), vi = keys.indexOf(v), from = lastVi==null ? vi : lastVi; lastVi = vi;
  let h = `<h1 id="h1">${VIEWS[v]}</h1>`;
  const sub = v==='ongoing' ? `${fd(today)}${on.length?` · ${on.length} 段旅程进行中`:''}` : v==='plan' ? `${allPlan.length} 个计划${allPlan.filter(pinVal).length?` · ${allPlan.filter(pinVal).length} 个置顶`:''}` : (gone.length?`走过的 ${gone.length} 段路`:'');
  h += `<div class="sub">${sub||'&nbsp;'}</div>`;
  h += `<nav class="seg" role="tablist" style="grid-template-columns:repeat(${keys.length},1fr)"><span class="thumb" style="width:calc((100% - 4px)/${keys.length});transform:translateX(${from*100}%)" data-to="${vi*100}"></span>${keys.map(k=>`<a href="#${k}" role="tab" class="${k===v?'on':''}" aria-selected="${k===v}">${VIEWS[k]}${k==='ongoing'&&on.length?`<sup>${on.length}</sup>`:''}</a>`).join('')}</nav>`;
  if(v==='ongoing'){
    h += on.length ? on.map(card).join('') : `<div class="empty"><div class="big">此刻不在旅</div>下一次出发，从计划开始。<br><a href="#plan">查看 ${allPlan.length} 个计划</a></div>`;
  } else if(v==='plan'){
    const opts = { n:['一日','2–3 日','4 日+'].filter(x=>allPlan.some(t=>nTag(t.n)===x)),
      dist:['近郊','周边','远途',...new Set(allPlan.map(t=>t.distance))].filter((x,i,a)=>x&&a.indexOf(x)===i&&allPlan.some(t=>t.distance===x)),
      type:[...new Set(allPlan.flatMap(t=>t.types))] };
    for(const k in opts) if(F[k]!=='all' && !opts[k].includes(F[k])) F[k]='all';
    const fr = (k,lb) => opts[k].length>1 ? `<div class="fr"><span class="lb">${lb}</span>${['all',...opts[k]].map(x=>`<button type="button" data-k="${k}" data-v="${esc(x)}" class="${F[k]===x?'on':''}" aria-pressed="${F[k]===x}">${x==='all'?'全部':esc(x)}</button>`).join('')}</div>` : '';
    const plan = allPlan.filter(t=>(F.n==='all'||nTag(t.n)===F.n) && (F.dist==='all'||t.distance===F.dist) && (F.type==='all'||t.types.includes(F.type))).sort((a,b)=>{
      const pa=pinVal(a), pb=pinVal(b);
      if(!!pa!==!!pb) return pa?-1:1;
      if(pa&&pb&&pa!==pb) return pa-pb;
      if(!!a.start!==!!b.start) return a.start?-1:1;
      return (a.start||'')<(b.start||'')?-1:(a.start||'')>(b.start||'')?1:a.title.localeCompare(b.title,'zh');
    });
    const f = fr('n','天数')+fr('dist','距离')+fr('type','类型');
    if(f) h += `<div class="filters">${f}</div>`;
    const pinned = plan.filter(pinVal), rest = plan.filter(t=>!pinVal(t));
    if(pinned.length) h += `<div class="sh">置顶</div><div class="grp">${pinned.map(row).join('')}</div>`;
    if(rest.length) h += `${pinned.length?'<div class="sh">其他计划</div>':''}<div class="grp">${rest.map(row).join('')}</div>`;
    if(!plan.length) h += `<div class="empty"><div class="big">没有符合的计划</div>换个筛选条件试试。</div>`;
  } else {
    h += gone.length ? `<div class="grp gone">${gone.map(row).join('')}</div>` : `<div class="empty"><div class="big">还没有足迹</div>行程结束后会自动收进这里。</div>`;
  }
  h += `<footer>状态按日期自动切换${v==='plan'?'。图钉只对这台设备生效，要在所有设备同步请改行程数据。':''}</footer>`;
  document.getElementById('page').innerHTML = h;
  document.getElementById('ttl').textContent = VIEWS[v];
  document.title = `${VIEWS[v]} · 行旅`;
  const th = document.querySelector('.seg .thumb'); if(th) requestAnimationFrame(()=>requestAnimationFrame(()=>{ th.style.transform = `translateX(${th.dataset.to}%)`; }));
  tick(); onScroll();
}
function tick(){
  const now = Date.now();
  document.querySelectorAll('[data-cd]').forEach(el=>{
    const t = TRIPS.find(x=>x.slug===el.dataset.cd), e = t.ev.find(e=>e[0]>now);
    if(!e){ el.style.display='none'; return; }
    let s = Math.floor((e[0]-now)/1000); const D = Math.floor(s/86400); s %= 86400;
    const hms = `${p2(Math.floor(s/3600))}:${p2(Math.floor(s%3600/60))}:${p2(s%60)}`;
    if(el.classList.contains('now')){
      el.querySelector('.l').textContent = `距下一项 · ${e[1]}`;
      el.querySelector('.n').innerHTML = `${D?`${D}<small>天</small>`:''}${hms}`;
    } else el.querySelector('b').textContent = `${D?D+' 天 ':''}${hms}`;
  });
}
const $nb = document.getElementById('nb');
function onScroll(){ const h1 = document.getElementById('h1'); if(h1) $nb.classList.toggle('scrolled', h1.getBoundingClientRect().bottom < 44); }
window.addEventListener('scroll', onScroll, {passive:true});
document.addEventListener('click', ev=>{
  const p = ev.target.closest('[data-pin]');
  if(p){ ev.preventDefault(); ev.stopPropagation(); const t=TRIPS.find(x=>x.slug===p.dataset.pin); pins[t.slug] = pinVal(t) ? 0 : Date.now(); set(PKEY,pins); render(); return; }
  const f = ev.target.closest('[data-k]');
  if(f){ F[f.dataset.k] = f.dataset.v; set(FKEY,F); render(); }
});
window.addEventListener('hashchange', ()=>{ render(); window.scrollTo(0,0); });
window.addEventListener('pageshow', ()=>{ pins=get(PKEY,{}); render(); });
render(); setInterval(tick, 1000); setInterval(()=>{ if(view()==='ongoing') render(); }, 60000);
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
