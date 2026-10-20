# Travel Plan · 旅行手册仓库

每个行程一个文件夹：`<slug>/trip.json`（唯一需要编辑的文件）→ `python3 build.py` 生成 `<slug>/index.html` 和首页 `index.html`。
GitHub Pages 从 `main` 分支根目录发布：`https://ruqinga.github.io/travel-plan/<slug>/`。

## 首页逻辑
- 右上角分段菜单切换三个视图（URL hash）：**Ongoing** `#ongoing`（默认首页）/ **Plan to go** `#plan` / **Gone** `#gone`。状态全部按日期自动判断（Europe/Madrid 当天）：没日期或未出发 = Plan，今天在行程内 = Ongoing，已结束 = Gone。
- Ongoing 视图标题是「在旅」。卡片显示第几天、进度条和「今日安排」（今天的都过了就显示「明日安排」），下一项高亮。
- 倒计时（第一版样式，按秒跳动）：有日期的 Plan 卡片显示「距出发」，Ongoing 卡片显示「距下一项」。目标来自 build.py 的 `events()`：长途交通出发 + 每天带 `time` 的条目（`flight:true` / `countdown:false` 跳过），按各自 `tz` 换算；没有带时间的条目时用出发日 0 点。
- 只有 Plan to go 有筛选：天数（自动：一日 / 2–3 日 / 4 日+）、距离 `distance`（近郊 ≤1h / 周边 1–3h / 远途 3h+）、类型 `types`（徒步、海边、城市、美食、自驾、出行；沿用已有的）。
- 置顶：`pinned: true`（或数字，越小越靠前）只对 Plan to go 生效。卡片上的图钉只改当前设备（localStorage），要所有设备一致就改 trip.json。
- 视觉与交互：遵循 Apple HIG。字体用系统字体（SF Pro / 苹方），不用衬线体；字号按 iOS 文字样式（大标题 34、标题 22、正文 17、副文 15、脚注 13）。底色用 iOS 系统色（浅色 #F2F2F7 + 白色分组，深色纯黑 + #1C1C1E），交互色是系统蓝，强调色用系统红/橙/绿；行程主题色只用在 App 图标式的天数徽章、路线和图例上（forest/sea/terracotta/plum/olive 映射到系统绿/青/橙/紫/棕）。
- 布局是 iOS 的「大标题 + 圆角分组列表（inset grouped）」：分隔线从文字处开始缩进，行高至少 44pt，Settings 式彩色小方块图标。
- 交互：大标题滚出后收进毛玻璃导航栏变成居中小标题；左上「‹ 行程」返回，右上分享图标导出；可点的行整行可点、按下变灰，带 › 或 ↗ 指示；分段控件滑块动画；导出图片用底部弹出面板（可下滑关闭，「完成」按钮，大号主按钮）；支持减弱动态效果。

## 行程页（网页端，导出图片时不包含）
- 顶部数据条（天数/目的地/交通/预算，`stats`）网页上隐藏，只在「导出图片」里出现。
- 顶栏下的**章节导航**（此刻 / 行程 / 地图 / 徒步 / 交通 / 长途交通 / 预订 / 住宿·预算 / 待办 / 贴士），只列存在的模块，滚动时高亮当前章节。
- **此刻关注**卡片：下一项安排 + 大号倒计时 + 第一条未完成的 todo；Gone 或没日期时不显示。
- **路线地图可点**：点地图空白处 → Google 地图打开全程路线（各天 route 去重，最多 9 个途经点）；点图钉/圆点 → 打开该地点（用点的 `q`，没有就用坐标）；地图下有「全程」和每天路线按钮。导航方式取 `day.travelmode` → `T.travelmode` → 根据 `mode` 推断（自驾=driving，TRAM/大巴/火车=transit，否则 walking）；transit 有途经点时不指定方式（Google 不支持）。

## 工作流程
1. 收集信息：目的地、日期、出发地（默认 Sant Joan d'Alacant）；票据截图自己提取，不让用户打字。
2. **先别动手**：把提取到的信息和行程草案列给用户确认一遍，再开始写。
3. 新建 `<slug>/trip.json`（slug 小写英文；有日期时加年份，如 `tokyo-2027`）。
4. `python3 build.py <slug>`；用 Playwright（`/opt/pw-browsers/chromium-1194` → playwright 1.56.x）截 390 宽浅/深色 + 1200 宽，点「导出图片」确认能出图、无 console 报错、地图标签不重叠。
5. `git fetch && git rebase origin/main`（如需）→ commit → push；约 1 分钟后上线。

## 内容原则
- 以已出票的时间为锚排行程；核对闭馆日、节假日、需预约的景点、换乘时长、天气；有冲突直接说。
- **确认号、订单号、证件号、房间号、门锁密码一律不写进页面**（build.py 会拦截）。
- 页面保持“终态”，不写修改日志（`updated` 除外）。所有时间是当地时间。

## trip.json schema（所有模块都是可选的，有就显示）
```jsonc
{
  "title": "Font Roja 森林 & Alcoy 小城", "subtitle": "两天一夜徒步计划",
  "highlights": ["亮点一", "亮点二"],          // 标题下一行，用 · 连接
  "theme": "forest(竹青)|sea(黛蓝)|terracotta(赭红)|plum(黛紫)|olive(橄榄)|#hex", "seal": "可选，印章文字，默认按天数",
  "from": "Sant Joan d'Alacant", "people": 2,
  "dates": {"start": "2026-11-14", "end": "2026-11-15"},   // 没定就写 null，再写 "length": 天数
  "dest": "Alcoy", "mode": "大巴 + 出租车",     // 首页卡片和自动数据条用
  "distance": "周边", "types": ["徒步", "城市"], "pinned": false,
  "tz": "Europe/Madrid", "updated": "2026-10-20",
  "stats": [{"k": "全程", "v": "约 8.4 km"}],  // 可选；不写就自动生成 天数/目的地/交通/预算
  "days": [{
    "date": "可选（不写则按 dates.start 推算）", "badge": "可选，默认 Day N / 一日行程", "title": "",
    "color": "可选 accent|main|gold|green|blue|#hex（默认单数天红、双数天主题色）",
    "route": ["pointId", ...], "dashed": [段序号], "mapLabel": "图例名",
    "items": [
      {"time": "09:15", "title": "", "note": "", "place": "Google 搜索词", "pt": "地图点 id（地图上显示同号图钉）", "mark": "gold|green|accent|main|blue"},
      {"move": "大巴 约 1 小时"}                 // 交通段：不编号，画成虚线连接
    ],
    "stay": "今晚住哪", "alt": {"title": "体力一般的替代方案", "text": ""}
  }],
  "map": {
    "subtitle": "", "bounds": [latMin, lonMin, latMax, lonMax], "maxH": 520,
    "points": {"id": {"name": "", "lat": 0, "lon": 0, "anchor": "start|middle|end", "dy": 4, "big": false, "label": true, "offmap": false, "time": false}},
    "land": [[[lat, lon], ...]],                // 陆地轮廓，给了海就是蓝色
    "areas": [{"name": "自然公园", "poly": [[lat, lon], ...], "labelAt": [lat, lon], "rotate": -30}],
    "lines": [{"name": "TRAM 线路", "pts": [[lat, lon], ...], "color": "#8a96a3|gold|accent", "dash": "8 6", "width": 3}],
    "labels": [{"text": "地中海", "lat": 0, "lon": 0, "size": 16, "sea": true}]
  },
  "hikes": [{"name": "", "shape": "环线|单程|往返", "distance": "", "time": "", "gain": "", "difficulty": "", "note": "",
             "wikiloc": "轨迹链接（可选）", "search": "没有链接时用来搜 Wikiloc 的关键词"}],
  "transport": {"title": "交通路线",
    "chain": [{"at": "San Juan"}, {"via": "TRAM 约 30 分钟"}, {"at": "Alicante"}],   // 有 chain → 全宽虚线框
    "lines": [{"label": "去程", "text": ""}, {"text": "", "hot": true}],              // 有 lines → 底部三栏里的交通卡
    "note": ""},
  "packing": ["水 2 L", "防晒"],                 // 装备标签
  "stay": {"name": "", "text": "", "q": "Google 搜索词"},
  "flights": [...], "bookings": [{"icon": "🏨", "title": "", "status": "已订|待订", "time": "", "address": "", "q": "", "note": ""}],
  "budget": {"title": "预算参考（一人）", "rows": [{"label": "", "est": "约 14 €", "actual": "Gone 后回填"}], "total": "150–175 €", "note": ""},
  "checklistTitle": "行前小贴士", "checklist": ["…"],
  "todos": [{"text": "", "done": false, "due": "", "urgent": true}],
  "band": {"text": "底部标语", "note": "右侧小字"},
  "unlisted": false                                // true：不在首页列出
}
```
「导出图片」把海报区域按 1240px 宽、浅色主题渲染成 PNG（vendor/html-to-image.js 内联进页面，无外部依赖）；带 `noexp` 的元素（地图链接、按钮）不进图。
