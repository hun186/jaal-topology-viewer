# Technical Decisions

> 只記錄已由實作及維護說明證實的長期取捨；日期為記錄日，不偽稱首次決策日期。

## Active Decision Index
| ID | 決策 | 狀態 | 記錄日 |
| --- | --- | --- | --- |
| ADR-0001 | 可攜核心獨立 repository 單一來源 | Accepted | 2026-11-03 |
| ADR-0002 | 下游 exact Git SHA pin 與分開驗收 | Accepted | 2026-11-03 |
| ADR-0003 | 唯讀、有界圖、loopback-only 預設 | Accepted | 2026-11-03 |
| ADR-0004 | Vercel 靜態 PoC 與 Merge-only 釋出 | Accepted | 2026-11-03 |

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

## 維護
新決策使用遞增不重用 ID；被取代時標記 Superseded 與新決策連結；不把一般 bugfix、猜測或秘密放入。
