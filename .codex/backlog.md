# Backlog

> Accepted/documented deferred validation。以下是 README/REPOSITORY_SETUP 既有的未完成**驗證閘門**，不是可重現 bug，也沒有承諾交付日期。

## Accepted Items
| ID | 優先度 | 狀態 | 項目 | 完成條件 |
| --- | --- | --- | --- | --- |
| BL-001 | High | Partial PASS | Windows 實機 Jaal／Stage 4 browser 視覺相容驗收 | 已有 consumer PR #227、Windows 使用者 9 項候選實機 PASS 與 Hosted browser acceptance；未覆蓋的 UI／版本組合或完整 ML 工況仍需個別列證，不宣稱全矩陣已驗收 |
| BL-003 | High | In Progress | Vercel PoC 與本機 Jaal 視覺／互動一致 | PR #10–#15 已 Merge：真正 Jaal/Dash、可收合側欄、非 sticky 工具列、全版檢視、四案例與虛構企業郵件事件；**公網仍未驗證部署**（先前 Vercel HTTP 402、merge-only opt-in/secret）；後續僅於符合權限與額度時發布 exact merge SHA 並實測 HTTP/Chromium，未 READY 不宣稱完成 |
| BL-004 | Medium | In Progress | 上傳案例與原版 Jaal 五模式／Louvain／時間演化整合 | 已 Merge PR #22／#23 的本機 SVG 網狀／階層、局部子圖、加權流向著色與互動量尺寸；後續改善雙向箭頭重疊。原 Jaal 五模式、Louvain、時間演化仍未整合，不能宣稱完整 parity |
| BL-002 | Medium | In Progress | 乾淨外部 consumer 安裝與 Dash/Jaal 版本組合驗證 | 原有 Ubuntu／Windows clean Wheel、HTTP/JS/CSS 與 Dash 2.18.2／3.4.0／4.5.0 Hosted CI PASS；PR #16 新增的外部 consumer TemporalTimeline + Flask 同埠驗證已於 Windows/Ubuntu clean Wheel CI PASS；完整下游 Stage 4 和跨 Windows/Dash browser 仍需個別證據 |

## Candidate Ideas
- 目前無已採納的額外構想。PyPI、Docker、公網服務部署都是另需授權與安全 review 的議題，不能自動當成待實作事項。

## 維護
- BL-001／BL-002 的原始追蹤依據：`README.md`、`REPOSITORY_SETUP.md`；未執行不代表失敗。
- PR #5 的 standalone Hosted Windows Chromium run 41494602192 PASS；下游 [PR #227](https://github.com/hun186/text-category-profiler/pull/227) 已 Merge，九項 Hosted workflow PASS，使用者 Stage 4 Louvain 候選 Windows 9 項實機 PASS。此結果不涵蓋所有 Dash／Windows 組合或完整模型工作負載，BL-001 保留 Partial PASS。
- 下游 `text-category-profiler` 已經由 PR #227 將 exact pin 升到 `47942ac3bd08d8cbcc615fa215c5e5eef286f486`，第五模式預設啟用並保留四模式 rollback；不得重做此升級。BL-002 仍須獨立完成乾淨外部 consumer 和 Dash 多版本矩陣。
- 本次新增的 Windows Chromium 雙版本 smoke 將在 `dash==4.5.0` 與 `dash==3.4.0` 分別實測本機 Jaal iframe、原始 vis DataSet 與可搜尋根節點局部顯示／還原；**僅於本 PR 最新 Hosted CI 兩段皆完成才算驗證**，不外推 Dash 2 或 Stage 4 完整 ML 實機。
- [上游 PR #7](https://github.com/hun186/jaal-topology-viewer/pull/7) 已 Merge；Hosted CI run 41591382206 四項工作 PASS，證明 Ubuntu/Windows 乾淨 venv 由 Wheel 安裝及同埠 HTTP 資產可用，但不能推論完整外部 consumer 相容。Dash 固定版本矩陣另需最新 HEAD CI 實證。
- 新增需要採納來源與驗證完成條件；Done/Dropped 保留簡短驗證或理由，不悄悄刪除。
