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
- 顶部数据条（天数/目的地/交通/预算，`stats`）网页上隐藏，只在「导出图片」不是截网页，而是用 `posterHTML()` 单独排一张 960px 宽、浅色的紧凑海报：标题 + 数据条（天数/目的地/交通/预算）+ 地图 + 每天时间线（多天并排）+ 底部卡片（徒步/交通/预订/住宿/预算/提示）。按 `LEVELS` 逐级缩小字号、减少备注/条目，直到高度 ≤ 宽度 × 2.1，保证手机一屏能看全。待办不进海报。
- **待办可轻点勾选**：trip.json 里的 `done` 是所有人看到的默认值；轻点勾选只保存在这台设备（localStorage `travelplan.todos`，按待办文字记），再点一次回到默认。用户说「XX 办完了」时仍要改 `done` 并推送，所有人才同步。
- 章节导航按实际小节生成（每个模块有自己的 id：day1/map/hikes/transport/tinfo/flights/bookings/stay/budget/checklist/todos/tips），按钮文字和小节标题一致。
