# Backlog

> Accepted/documented deferred validation。以下是 README/REPOSITORY_SETUP 既有的未完成**驗證閘門**，不是可重現 bug，也沒有承諾交付日期。

## Accepted Items
| ID | 優先度 | 狀態 | 項目 | 完成條件 |
| --- | --- | --- | --- | --- |
| BL-001 | High | Accepted | Windows 實機 Jaal／Stage 4 browser 視覺相容驗收 | root picker、Search/Filter/Color/Size、四模式、中文 fallback、收攏動畫／focus、same-port iframe 有可追溯的實測結果 |
| BL-002 | Medium | Accepted | 乾淨外部 consumer 安裝與 Dash/Jaal 版本組合驗證 | 在明確列出的環境完成可重現 install、HTTP/JS/CSS、互動驗證，未涵蓋的組合明示 |

## Candidate Ideas
- 目前無已採納的額外構想。PyPI、Docker、公網服務部署都是另需授權與安全 review 的議題，不能自動當成待實作事項。

## 維護
- BL-001／BL-002 的原始追蹤依據：`README.md`、`REPOSITORY_SETUP.md`；未執行不代表失敗。
- PR #5 在 Hosted Windows Chromium（GitHub Actions run 41494602192）驗證了 standalone same-port iframe、visdcc quotient、Search hidden、中文 CT 和 77/169 還原；**不等於**使用者 Windows Stage 4 完整驗收，BL-001 不標 Done。
- 下游 `text-category-profiler` 的 `test_jaal_topology_portable.py` 固定期待四種模式，若將 consumer exact pin 升到新版五模式，須同步更新測試契約、執行 Stage 4 consumer CI 與 formal review；BL-002 不標 Done。
- 新增需要採納來源與驗證完成條件；Done/Dropped 保留簡短驗證或理由，不悄悄刪除。
