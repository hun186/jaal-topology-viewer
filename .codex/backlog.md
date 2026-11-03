# Backlog

> Accepted/documented deferred validation。以下是 README/REPOSITORY_SETUP 既有的未完成**驗證閘門**，不是可重現 bug，也沒有承諾交付日期。

## Accepted Items
| ID | 優先度 | 狀態 | 項目 | 完成條件 |
| --- | --- | --- | --- | --- |
| BL-001 | High | Partial PASS | Windows 實機 Jaal／Stage 4 browser 視覺相容驗收 | 已有 consumer PR #227、Windows 使用者 9 項候選實機 PASS 與 Hosted browser acceptance；未覆蓋的 UI／版本組合或完整 ML 工況仍需個別列證，不宣稱全矩陣已驗收 |
| BL-003 | Medium | In Progress | Vercel 公開唯讀 PoC 與節流部署 | 真實 SVG／CSV 靜態互動及 Hosted CI 通過；僅相關 PR 合併才有部署資格；Vercel project/憑證啟用/實際 READY 另驗 |
| BL-002 | Medium | In Progress | 乾淨外部 consumer 安裝與 Dash/Jaal 版本組合驗證 | upstream clean Wheel smoke（Ubuntu／Windows，非 editable）與 HTTP/JS/CSS 正在補齊；外部 consumer 安裝、Dash 多版本矩陣與互動驗收仍需額外證據 |

## Candidate Ideas
- 目前無已採納的額外構想。PyPI、Docker、公網服務部署都是另需授權與安全 review 的議題，不能自動當成待實作事項。

## 維護
- BL-001／BL-002 的原始追蹤依據：`README.md`、`REPOSITORY_SETUP.md`；未執行不代表失敗。
- PR #5 的 standalone Hosted Windows Chromium run 41494602192 PASS；下游 [PR #227](https://github.com/hun186/text-category-profiler/pull/227) 已 Merge，九項 Hosted workflow PASS，使用者 Stage 4 Louvain 候選 Windows 9 項實機 PASS。此結果不涵蓋所有 Dash／Windows 組合或完整模型工作負載，BL-001 保留 Partial PASS。
- 下游 `text-category-profiler` 已經由 PR #227 將 exact pin 升到 `47942ac3bd08d8cbcc615fa215c5e5eef286f486`，第五模式預設啟用並保留四模式 rollback；不得重做此升級。BL-002 仍須獨立完成乾淨外部 consumer 和 Dash 多版本矩陣。
- [上游 PR #7](https://github.com/hun186/jaal-topology-viewer/pull/7) 已 Merge；Hosted CI run 41591382206 四項工作 PASS，證明 Ubuntu/Windows 乾淨 venv 由 Wheel 安裝及同埠 HTTP 資產可用，但不能推論完整外部 consumer 相容。Dash 固定版本矩陣另需最新 HEAD CI 實證。
- 新增需要採納來源與驗證完成條件；Done/Dropped 保留簡短驗證或理由，不悄悄刪除。
