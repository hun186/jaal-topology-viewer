# Project Memory

> Recent durable context；不保存聊天逐字稿、完整 log 或可由 diff 直接看出的瑣碎變更。

## Current Focus
- `INITIALIZED`（2026-11-03）；啟動任務固定讀 `project.md` 和本檔 Current Focus／Recent Outcomes。
- 本 repo 是通用 `jaal_topology` Python/JS 核心**唯一來源**；不得回複製到 `text-category-profiler`。
- 維持唯讀 CSV、原始有向圖 IDs、匯入／顯示上限、四模式與同 port Flask mount。
- 下游使用 reviewed exact Git SHA，更新必須另行修訂 consumer pin、執行 consumer CI/Review。
- Windows 實機視覺、Dash 2/3/4 及乾淨外部 consumer 尚不能視為已驗收。
- 本 repo 的通用圖 viewer 與 consumer Stage 4 專屬 root picker、sidebar、iframe autoheight 分工不同。

## Recent Outcomes
| 日期 | 事件 | 持久結果 |
| --- | --- | --- |
| 2026-11-03 | Codex memory bootstrap | 由 `main` `fc49c0d2559c71df79f438e070ef3610e7093e5a` 的程式、manifest、CI、README 建立 project/workflows/architecture/contracts/decisions/backlog 與 Quickstart；此次僅文件，不修改產品程式碼或測試。 |
| 2026-11-02 | 獨立核心歸屬文件 | [PR #1](https://github.com/hun186/jaal-topology-viewer/pull/1) 已 merged；README／REPOSITORY_SETUP 明確說明 source of truth、下游 exact SHA 更新。 |
| 2026-11-02 | 主線 CI 基準 | `main` `fc49c0d2559c71df79f438e070ef3610e7093e5a` [Hosted CI success](https://github.com/hun186/jaal-topology-viewer/actions/runs/41480969808)；未宣稱本次本機重跑或 Windows 視覺驗收。 |

## Open Handoffs
- Windows browser：root selector、Jaal Search/Filter/Color/Size、四模式、中文 fallback、收攏動畫、focus、same-port iframe 的 consumer 驗證。
- 下游依賴更新：provenance、Stage 4 相容測試、最新 HEAD CI 與正式 Review；上游 merge 不自動影響下游。
- 本次文件 PR 合併狀態以 GitHub 為準；不能在此預先宣告正式 review 或 merge 已完成。

## Archive Index
- `.codex/archive/README.md`；日常任務不主動讀 archive。

## 維護
Current Focus 簡短；Recent Outcomes 上限 10，超過約 200 行／24 KB 濃縮。只保留持久可驗證成果，不保存秘密、敏感 payload、完整輸出或臨時猜測。
