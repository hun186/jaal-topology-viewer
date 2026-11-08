# Technical Decisions

> 只記錄已由實作及維護說明證實的長期取捨；日期為記錄日，不偽稱首次決策日期。

## Active Decision Index
| ID | 決策 | 狀態 | 記錄日 |
| --- | --- | --- | --- |
| ADR-0001 | 可攜核心獨立 repository 單一來源 | Accepted | 2026-11-03 |
| ADR-0002 | 下游 exact Git SHA pin 與分開驗收 | Accepted | 2026-11-03 |
| ADR-0003 | 唯讀、有界圖、loopback-only 預設 | Accepted | 2026-11-03 |
| ADR-0004 | Vercel 靜態 PoC 與 Merge-only 釋出 | Superseded by ADR-0005 (static only) | 2026-11-03 |
| ADR-0005 | 公開 PoC 共用真正 Jaal/Dash，維持 Merge-only | Accepted | 2026-11-03 |
| ADR-0006 | 有界 Gallery 多 Dash route 取代同頁直接換 Graph | Accepted | 2026-11-03 |
| ADR-0007 | 原版類別樹通訊示意與新合成郵件業務情境區分 | Accepted | 2026-11-03 |
| ADR-0008 | 原事件流與時間片圖分離，先預算並以瀏覽器動畫播放 | Accepted | 2026-11-03 |
| ADR-0010 | 客戶私人案例採 local-first browser storage 與獨立檢視 | Accepted | 2026-11-04 |
| ADR-0011 | 超大合成圖隔離 Canvas，保留原版 Jaal 限額 | Accepted | 2026-11-08 |
| ADR-0009 | 精確半開區間及預設互斥分段，多粒度與 240 格硬上限 | Accepted | 2026-11-04 |

## ADR-0001 — 單一來源
- 背景：portable 核心曾位於 `text-category-profiler/packages/jaal-topology`，下游整合 PR [#209](https://github.com/hun186/text-category-profiler/pull/209)、[#210](https://github.com/hun186/text-category-profiler/pull/210) 後搬離。
- 決策：本 repo 負責 Python/JS 通用核心，consumer 保留 Stage 4 特定 root、sidebar、iframe 等 UI。
- 取捨：減少重複核心，但跨 repository 需升級協調。證據：`REPOSITORY_SETUP.md`、merged [PR #1](https://github.com/hun186/jaal-topology-viewer/pull/1)。

## ADR-0002 — Pin exact SHA
- 背景：上游版本變化可能影響下游 Stage 4。
- 決策：consumer 使用經 review 的 Git SHA 而非浮動 `main`；更新 pin 需獨立 PR、provenance 與 CI。
- 取捨：較慢獲取新功能，換取重現性與相容控制；offline 可以 exact SHA wheel + hash。
- 證據：`README.md`、`REPOSITORY_SETUP.md`。

## ADR-0003 — 安全／效能有界
- 決策：CSV 不回寫；匯入 max 100,000 unique edges；render max 3000 nodes/5000 edges；CLI 只監聽 loopback；空可視邊拒絕。
- 取捨：過大圖需選 root，公網部署需另做安全 review。證據：`data.py`、`cli.py`、`viewer.py`。

## ADR-0004 — Static public PoC and merge-only deployment

- 使用者授權新增 Vercel PoC 並要求避免每個 Push/PR 都浪費每日部署額度。
- PoC 僅使用既有虛構 CSV 產生靜態 SVG，不公開 Python/Dash Jaal Server；部門收攏不是 Louvain。
- vercel.json 關閉所有 Git 自動部署。GitHub Actions 必須滿足 PR closed、merged、base main、相關檔案變更、顯式 enable，並檢查同 merge SHA 是否已部署。
- 需獨立的 Vercel project、最小權限 GitHub environment secret 和固定 CLI 版本；憑證不存在則不部署。
- CI/正式 Review 與 Vercel READY 分開驗證，不推定 merge 就等於上線。

## ADR-0005 — Shared Jaal/Dash Flask PoC instead of separate SVG

- 使用者指出 Vercel 靜態 SVG 與本機原版的外觀、功能差異過大。
- 決策：在 `app.py` 使用原本 `build_app()`、完整 Jaal/visdcc、五種模式與 callback，而非維護平行視覺引擎。
- 僅允許公網展示 `examples/company_communications.csv` 與 `company_people.csv`，固定 77/169；不支援外部 CSV 上傳、不暴露私人 Stage 4 或模型資料。
- 保留 ADR-0004 的部署預算控制：Vercel Git 自動部署永遠關閉、僅相關 PR Merge + 明確 enable；每次部署還需真實 READY/HTTP 驗證。
- 代價：Flask/Dash serverless 需處理冷啟動、Python 套件體積、資源消耗，不能等同靜態站；未驗證前不得宣稱在 Vercel 與 Windows CLI 完全相同。

## ADR-0006 — Independent Dash apps per gallery case

- 使用者希望獨立 Viewer 可選單快速切換寄收件網、階層樹、其他網路案例，而非手動重啟程式。
- 原版 Jaal Search／Filter／Color／Size 回呼在建立時綁定 Python Graph/Network；同一個 Dash app 直接替換 `graph.data` 會保留舊圖 closure，造成錯誤搜尋／收攏／配色。
- 決策：採取 `GalleryCase` registry，最多 20 個明確、可驗證案例，一個 Flask/Port 下為每案建獨立 Dash app／子路徑，下拉以同來源 URL 導頁；切換需要重新載入 Dash 頁面，但每案 callbacks、模式合法性、Louvain membership 隔離，且只在開機建圖一次。
- 單案例 `build_app`／`mount_flask` 仍原樣相容；Gallery API 可供任何 Python consumer 可選使用。公網案例均為固定虛構資料，無 CSV 上傳／外部 URL。
- 此改動不代表 Vercel 已部署：Git auto/Preview 仍禁用，只可在 reviewed Merge 後依額度發布，完整上線需 HTTP/browser 證據。

## ADR-0007 — Distinguish historical topology from plausible synthetic email

- 原本 77/169 寄收件示意由 TW Affairs 類別樹改名、加上人工回信與連線，不是根據郵件時間／頻率或企業作業模型產生；不得再宣稱它已模擬真實收發行為。
- 新增固定種子、20 個工作日的虛構事件生成器，明確涵蓋：團隊內、主管、業務提案／客訴升級、月底對帳、夜間系統事件、主管簡報與 HR 作業。所有參與者只用角色名，不使用真實個資。
- 原版仍為 Gallery 獨立舊案例；新業務情境成為預設案例，提供可重現的 read-only 逐封事件 CSV 與有向彙總 CSV。無真實郵件串接／任意上傳／資料寫回。
- 保留一般 `Graph(edges,nodes,translations)` API；僅附帶明確 `edge_counts` 的圖會加權 Louvain 與顯示郵件線寬，避免偷偷更改分類樹或舊示例的拓樸語義。社群聚合邊數仍是獨立有向關係數，不等同郵件封數。
- 這只是具業務合理性的示範假設，未由真實企業資料校準；公開站改版仍需 Merge Gate 與 Vercel API 額度恢復後獨立驗證。

## ADR-0008 — Temporal event windows without per-tick server calls

- 需求：有向收發網路可任選時間範圍、累積／滑動窗口、步長、速度、手動跳格、自動輪轉，展示真實拓樸變化。
- 決策：`Graph` 保留單時間片內的去重有向邊和選用封數；`TemporalTimeline` 另存 ISO 事件時間，按窗口重新產出 Graph 和加權 Louvain，不將「某個時間」硬塞給一條累積邊。
- 在分析設定變更時由 Python 有界計算多個日片，交給同來源瀏覽器 `dcc.Store`；`dcc.Interval` 由純 clientside JS 播放，不作逐格 HTTP。切換沿用同一 visdcc Network/Camera，原版單圖 `build_app(graph)` 不帶時間 UI。
- 兼顧資料量與安全：50,000 events/120 calendar days/180,000 frame-edge 限額；一致使用 naive local 或 normalized UTC、拒絕混用；禁止把 CSV/事件資料插入 JS 指令字串，原事件流唯讀。
- 取捨：目前原版 Jaal Filter/Size **server callbacks** 仍基於全期間來源；時間演化部分更新可視 DataSets/統計與 Louvain，不宣稱每個 Jaal 篩選／尺寸選項已完全動態化。實時資料接入、時區 UX、分群標籤穩定性及對照雙圖另列候選工作。
- 發布與部署不變：Vercel Push/PR auto-deploy 禁用，必須通過最新 SHA CI/Code Review 與 Merge Gate 才能考慮發布。

## ADR-0009 — Minute-level disjoint-by-default interval playback

- 使用者指出原先日資料藍條左端不移動、起點不易調整、區間重疊與分鐘級分析欠缺定義。
- 增加保留原始事件分鐘時間戳的 `interval_frames(start_minute,end_minute,window_minutes,step_minutes)`；`[start,end)` 左閉右開，預設 step=window（互斥），另可設定小於窗長的 overlap，累積模式沿用單一起點。原 `snapshot()/frames()` 日層級函式保留。
- RangeSlider 為分析起訖，另有目前播放時段藍條；兩端均可拖拉或以 ISO 時間文字編輯。避免誤將固定分析範圍當成播放窗。
- 保留原始完整 CSV/事件，現場只算有界摘要；最多 240 個 frame、180000 frame-edges。超限回明確錯誤而非在畫面保留與控制項不一致的舊資料。永不逐格呼叫 Vercel。
- Python minute/local-naive/UTC 事件規範延續 ADR-0008，部署、下游 consumer 發布閘門不變。

## 維護
新決策使用遞增不重用 ID；被取代時標記 Superseded 與新決策連結；不把一般 bugfix、猜測或秘密放入。

## ADR-0010 — Private browser case workspace without server-side Jaal swapping

- Requirement: customers upload their own relationship files and save/reopen graph cases with a friendly UI, optionally remembering a local path or browser cache.
- Browsers cannot re-open arbitrary local files from a remembered path. Chosen design stores a bounded, validated typed graph in IndexedDB scoped to the current origin/browser profile and provides manual JSON export/import. No server POST/temporary upload/session store, cross-device sync or sensitive path logging.
- Existing Jaal's Dash callback closure is bound to each startup graph. Swapping a user-owned graph into that same app would make Search/Filter/Color/Size stale, and transferring bytes to a shared/public server conflicts with local-first privacy. Therefore the user-workspace is a separate, clearly labeled native SVG browser renderer; the existing 5-mode Jaal gallery remains unchanged, without pretending feature parity.
- Bound input, strict UTF-8/RFC4180 parser, DOM text-only rendering, CSP denying network connections, endpoint GET allowlist, browser-local persistence and opt-in plaintext backup. Storage eviction, shared browser profiles and JS-based drawing limits are explained in UI. Future full Jaal parity requires a separately reviewed secure client graph integration rather than an implied compatibility claim.

## ADR-0011 — Scale stress lab isolated from bounded Jaal

- 需求：展示 500／3000／5000／20000 人、更多部門與管理層，及三個真正互不連通的郵件群。
- 決策：保留 Jaal 3000 nodes/5000 edges 硬限與既有 Gallery callback 隔離；設計獨立 GET-only Canvas 實驗室，所有虛構人員／有向加權關係在瀏覽器由固定業務規則生成，摘要／局部／完整圖明確標示，20k 全圖不冒充 Jaal 原生容量。
- 取捨：Canvas 不提供原生五模式、Louvain 與時間播放；不同瀏覽器對全量 20k 畫布耗時不同。只記實測生成／繪製時間，不作不受支持的效能承諾。三連通分量情境無跨群有向邊。
- 既有部署 merge-only／禁用 PR 自動部署、私人工作區不傳資料及下游 exact pin 均不變。
