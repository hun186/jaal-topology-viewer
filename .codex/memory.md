# Project Memory

> Recent durable context；不保存聊天逐字稿、完整 log 或可由 diff 直接看出的瑣碎變更。

## Current Focus
- `INITIALIZED`（2026-11-03）；啟動任務固定讀 `project.md` 和本檔 Current Focus／Recent Outcomes。
- 本 repo 是通用 `jaal_topology` Python/JS 核心**唯一來源**；不得回複製到 `text-category-profiler`。
- 維持唯讀 CSV、原始有向圖 IDs、匯入／顯示上限、四個 legacy 模式及獨立實驗 Louvain 模式、同 port Flask mount。
- 下游透過 reviewed exact Git SHA 消費；目前 consumer `requirements.txt` 已釘 PR #5 merge SHA `47942ac3bd08d8cbcc615fa215c5e5eef286f486`（consumer PR #227 已 Merge），後續更新仍需 consumer CI/Review。
- 特定 Stage 4 Louvain 候選的 Windows 使用者實機驗收（9 項）及 consumer Hosted CI 已 PASS；Dash 2/3/4 全矩陣、全 ML 工作負載與乾淨外部 consumer 仍未驗收。
- 本 repo 的通用圖 viewer 與 consumer Stage 4 專屬 root picker、sidebar、iframe autoheight 分工不同。

- Issue #4 已由 [PR #6](https://github.com/hun186/jaal-topology-viewer/pull/6) 合併驗證 Louvain resolution/seed 與 3000-node／5000-edge 邊界；BL-002 的隔離 Wheel smoke 由 PR #7 Hosted CI 通過，Dash 2/3/4 固定版本矩陣以其 PR 最新 HEAD CI/Review 為準，不外推至 consumer 全組合。

- 已 Merge PR #10–#14：同一 Jaal/Dash WSGI、非 sticky/全版視野、四案例切換、可重現且明確虛構的企業郵件事件及收發量加權；Vercel 真正 Python 公網實際部署仍因先前 HTTP 402、merge-only 設定未驗證，**不得宣稱 READY**。
- 目前 [PR #15](https://github.com/hun186/jaal-topology-viewer/pull/15) 為 Ready、尚未 Merge：可選事件時間片與 clientside 播放，不影響一般 CSV API。先前 HEAD `8c830cc` Hosted test/browser 兩類 FAIL；已修正 Node 測試穩定 DataSet 期望與 Windows Dropdown selector；**最新 HEAD CI/正式 Codex Review 尚未完成**，禁止依舊 SHA Review/CI Merge。
## Recent Outcomes
| 日期 | 事件 | 持久結果 |
| --- | --- | --- |
| 2026-11-03 | [PR #14](https://github.com/hun186/jaal-topology-viewer/pull/14) 已 Merge | `main` merge `b62a6b0f97767ca81e86f5b647c45d28786e5296`；新增固定種子的虛構企業郵件事件與明確頻次加權，保留 legacy 拓樸圖；不得誤認真實郵件／公網已部署。 |
| 2026-11-03 | [PR #13](https://github.com/hun186/jaal-topology-viewer/pull/13) 已 Merge | `main` merge `dced7b5027ea565830de8630d5d900e72552e163`；獨立 GalleryCase、多路同埠 Jaal 案例隔離切換，舊單圖 API 不變。 |
| 2026-11-03 | [PR #12](https://github.com/hun186/jaal-topology-viewer/pull/12) 已 Merge | Latest HEAD `e0b5822e77ad4acc840661fc4a79119f346c3cfb` Hosted CI [41618971626](https://github.com/hun186/jaal-topology-viewer/actions/runs/41618971626) 8/8 PASS；Windows 真 Canvas viewport height、Esc 還原驗證；Codex Review 0 Finding，merge `2562cd741203de2cdab0fd5f414a8a41ef49a038`；Vercel 仍因先前 HTTP402 未部署 Python。 |
| 2026-11-03 | [PR #7](https://github.com/hun186/jaal-topology-viewer/pull/7) 已 Merge | Latest HEAD `9f699ef45994267e5f19039b5187da503ed2461f` Hosted [41591382206](https://github.com/hun186/jaal-topology-viewer/actions/runs/41591382206) 四項工作 PASS，正式 Codex Review completed/0 findings；merge commit `744bcdba684d3bbfd5bf87190ec9ed13b4569130`；Ubuntu／Windows clean Wheel install + same-port assets 驗證。 |
| 2026-11-03 | [PR #6](https://github.com/hun186/jaal-topology-viewer/pull/6) 已 Merge | Latest HEAD `b4d50af8b8501763d22a2ebee6cf5d29abeaad5e` Hosted [41590709918](https://github.com/hun186/jaal-topology-viewer/actions/runs/41590709918) Ubuntu／Windows PASS，正式 Codex Review completed/0 findings；merge commit `c1642147c40fa4e9907161ab7c64ceb02ff4b667`，新增 Louvain Seed/Resolution 與 3k/5k 邊界測試。 |
| 2026-11-03 | [Consumer PR #227](https://github.com/hun186/text-category-profiler/pull/227) 已 Merge | 受控升級 Jaal exact pin 至 `47942ac3bd08d8cbcc615fa215c5e5eef286f486`；使用者 Stage 4 候選九項實機 PASS，consumer PR #227 九項 Hosted workflow success；保留舊四模式 rollback。未驗證全部外部環境。 |
| 2026-11-03 | [PR #5](https://github.com/hun186/jaal-topology-viewer/pull/5) 已 Merge | GitHub 確認 merge commit `47942ac3bd08d8cbcc615fa215c5e5eef286f486`；既有 Hosted [41494602192](https://github.com/hun186/jaal-topology-viewer/actions/runs/41494602192) Ubuntu／Windows Chromium PASS，已驗證 real visdcc quotient、Search hidden、中文 CT、77/169 還原；不代表 Stage 4/consumer 完整驗收。 |
| 2026-11-02 | 主線 CI 基準 | `main` `fc49c0d2559c71df79f438e070ef3610e7093e5a` [Hosted CI success](https://github.com/hun186/jaal-topology-viewer/actions/runs/41480969808)；未宣稱本次本機重跑或 Windows 視覺驗收。 |

## Open Handoffs
- Windows browser：PR #5 upstream Windows Hosted Chromium PASS；consumer [PR #227](https://github.com/hun186/text-category-profiler/pull/227) 已 Merge，使用者提供的 Stage 4 候選實機驗收九項 PASS、該 PR Hosted 九項工作流程 PASS；不得外推至全部 Windows／Dash 版本及 ML 工況。
- 下游依賴更新：目前 consumer `requirements.txt` 已釘 `47942ac3bd08d8cbcc615fa215c5e5eef286f486`；PR #227 已透過受控 provenance 與第五模式預設啟用、四模式 rollback 驗證，不得重做既有升級。
- Issue #4 替代演算法、加權郵件完整對外契約與跨版本 consumer 相容仍須額外驗收；PR #14 的合成權重、PR #15 的時間片不可視為真實郵件資料接入。
- PR #15 最新 Head：需 Hosted 全部 CI（尤其 Node、Windows Chromium）及涵蓋最新 Commit 的正式 Codex Review。先前 Reviewed SHA `c302536` 的 P2 fixture Finding 已另行修正/解決，但非對後續 Head 的複審。

## Archive Index
- `.codex/archive/README.md`；日常任務不主動讀 archive。

## 維護
Current Focus 簡短；Recent Outcomes 上限 10，超過約 200 行／24 KB 濃縮。只保留持久可驗證成果，不保存秘密、敏感 payload、完整輸出或臨時猜測。
