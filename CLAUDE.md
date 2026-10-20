# Travel Plan · 旅行手册仓库

每个行程一个文件夹：`<slug>/trip.json`（唯一需要编辑的文件）→ `python3 build.py` 生成 `<slug>/index.html` 和首页 `index.html`。
GitHub Pages 从 `main` 分支根目录发布：`https://ruqinga.github.io/travel-plan/<slug>/`。

## 工作流程（每次新行程 / 更新）
1. 收集信息：目的地、日期、人数、出发地；机票/酒店/租车/门票截图（自己从截图里提取，不让用户打字）。
2. **先别动手**：把提取到的信息和行程草案列给用户确认一遍，再开始写。
3. 新建 `<slug>/trip.json`（slug 用小写英文+年份，如 `tokyo-2027`），按下方 schema 填写。
4. `python3 build.py <slug>`；用 Playwright（`/opt/pw-browsers/chromium-*`，手机 390×844 + 深色模式）截图检查，无 console 报错。
5. `git add -A && git commit && git push origin main`；约 1 分钟后上线。把链接发给用户。
6. 之后用户说"XX 办完了 / 改一下 XX"，只改 trip.json 对应字段 → build → push，链接不变。

## 内容原则
- **以已出票的航班时间为锚**排行程，时间对不上就整体重排，别硬塞。
- 帮忙核对：博物馆闭馆日、节假日营业/售罄风险、需要提前预约的（含免费）景点、开车/换乘时长是否合理。需要时上网查。
- **发现安排有冲突或风险，直接说**，别顺着用户。
- **确认号、订单号、证件号、房间号、门锁密码一律不写进页面**——公开网址谁都能看。build.py 会拦截明显的这类字段。
- 页面永远保持"终态"：不写修改日志或版本说明（`updated` 日期除外）。
- 待办清单是纯列表，由 Claude 根据用户反馈更新 `done`，不做浏览器内勾选。
- 所有时间都是**当地时间**；跨时区的条目单独写 `tz`。

## trip.json schema
```jsonc
{
  "title": "德州劳工节牛仔之旅", "emoji": "🤠", "kicker": "可选，标题上方小字",
  "dates": {"start": "2026-09-04", "end": "2026-09-08"}, "people": 4,
  "route": "达拉斯 → 奥斯汀", "summaryLine": "可选一行补充",
  "tz": "America/Chicago",            // 默认时区（IANA）
  "updated": "2026-08-31",
  "status": [{"icon": "✈️", "text": "往返机票已出票"}, {"icon": "🎟️", "text": "门票待购", "ok": false}],  // ok:false 红色，"info" 蓝色
  "overview": "行程总览一段话",
  "map": {
    "points": { "<id>": {"name": "显示名", "lat": 0, "lon": 0, "q": "Google 地图搜索词",
                         "label": true, "kind": "minor", "big": false, "anchor": "start|middle|end", "dy": 4, "offmap": false} },
    "bounds": [latMin, lonMin, latMax, lonMax],     // 可选，默认取所有非 offmap 点
    "land": [[[lat, lon], ...]],                    // 可选，陆地多边形（手绘风粗略轮廓即可），给了它海就显示成蓝色
    "coast": [[[lat, lon], ...]],                   // 可选，只画线（州界/海岸）
    "labels": [{"text": "大 西 洋", "lat": 0, "lon": 0}]
  },
  "flights": [{"from": {"code": "MAD", "name": "马德里 T4", "tz": "Europe/Madrid"}, "to": {...},
               "depart": "2026-12-29T09:05", "arrive": "2026-12-29T09:20",   // 各自当地时间
               "duration": "1h15", "stops": "直飞", "airline": "", "number": "", "status": "已出票", "note": ""}],
  "bookings": [{"icon": "🏨", "title": "", "status": "已订", "time": "", "address": "", "q": "", "phone": "", "note": ""}],
  "days": [{
    "date": "2026-12-29", "title": "", "subtitle": "", "mapLabel": "图例短名", "color": "#可选",
    "tz": "可选", "travelmode": "driving|transit|walking",
    "route": ["pointId", ...],          // 地图上当天的线 + "全天路线"多点导航；offmap 点画成指向场外的虚线箭头
    "flightSegs": [0],                  // 可选：route 中第几段是飞行（画虚线）
    "stayPoint": "hotel",               // 地图上标"住"
    "items": [{"time": "09:20", "title": "", "note": "", "place": "Google 搜索词", "placeLabel": "",
               "tag": "需预订|已购|待购…", "tz": "可选", "flight": true, "countdown": true}],
    "stay": "今晚住哪", "stayQ": "Google 搜索词"
  }],
  "todos": [{"text": "", "done": false, "due": "12/15 前", "urgent": true, "note": ""}],
  "tips": [{"icon": "🌦️", "title": "天气", "text": ""}],
  "footer": "Travel Plan · ruqinga", "unlisted": false   // unlisted:true 不在首页列出
}
```
倒计时取最近的未来事件：航班起飞 + 每天带 `time` 的条目（`flight:true` 或 `countdown:false` 的条目跳过，避免和航班重复）。
