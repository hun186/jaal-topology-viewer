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
- [PR #15](https://github.com/hun186/jaal-topology-viewer/pull/15) 已 Merge (`8fddffa1c94edeab0dce4cedafdd44a2ceeb1ac0`)：可選事件時間片與 clientside 播放，已修正時間圖切換佈局時重新啟用 physics 問題，現有 CSV API 不變。獨立外部 consumer 的時間軸 Wheel 驗證仍列 BL-002。
- [PR #16](https://github.com/hun186/jaal-topology-viewer/pull/16) 已 Merge (`1b9cd893531b3777b80f7efabb7bea170cbf5a85`)：從 checkout 外、Ubuntu/Windows clean Wheel 安裝驗證外部時間軸 Consumer 的 rolling frames、same-port Flask callbacks/assets；完整下游 Stage 4 仍未驗證。
- [PR #17](https://github.com/hun186/jaal-topology-viewer/pull/17) 已 Merge（`e680b473ab52f5197b3eb1e5bd654685c342a080`）；多案例 nonroot temporal WSGI 隔離，Hosted CI 8/8 PASS，Codex Review 0 Findings。此結果仍非 Windows 人工動畫視覺驗收。
- 2026-11-04 Windows 使用者在「企業郵件實務模擬」觀察：全展開標籤擁擠、滾動窗看似累積、逐格 Louvain 使展開失效、畫面不穩。已定位前端將 temporal hidden 狀態誤判為 Search/Filter，與每 frame 用 active 子集及時窗 key 重建社群；本修復分支以 fixed-universe、固定群組預設、稀疏標籤及顯式視窗摘要處理，CI/實機仍須以 PR 最新 HEAD 驗證。

- 2026-11-04 使用者 Windows 電郵案例回饋：Louvain 社群展開/收合有時在遠處重繪，並要求可調基礎邊長。修正透過群組前一錨點重新放射佈局、保留社群盒位置，新增 60–300px 視覺間距滑桿；實機視覺驗收需另外進行。
- PR #18 已合併 main `89a3f9cceba03d18b1bba9b86292e3c7a61304d4`：3 天 rolling 預設、固定 Louvain、穩定 ID、稀疏標籤，CI 8/8 和 Codex 0 finding；不代表 Windows 人工視覺驗收。

- 2026-11-04 的時間窗 UX：將日級滑動窗延伸成 minute/hour/day，[start,end) 互斥預設 (step=window)、重疊自訂步長；滑桿範圍可動雙端，另用藍條表示播放中時段；frame 超過 240 明確報錯。此分支需以最新 CI/Review/實機視覺檢查為準。

- 2026-11-04 使用者新增獨立 Jaal searchable root/radius 需求：本候選實作 `neighborhood.py` + `22.jaal_local_focus.js` + Dash 搜尋選單，對 DAG 和一般有環有向圖提供 out/in/both 最短 0..10 hop 或全部可達、誘導子圖；根節點清空恢復全圖。需以 PR 最新 CI/Review 及 Windows 實機證據確認，未自動升級 consumer pin。

## Recent Outcomes
| 日期 | 事件 | 持久結果 |
| --- | --- | --- |
| 2026-11-03 | [PR #17](https://github.com/hun186/jaal-topology-viewer/pull/17) 已 Merge | 8/8 Hosted CI、Codex Review completed/0 Finding；Squash merge `e680b473ab52f5197b3eb1e5bd654685c342a080`，nonroot graph gallery temporal control 隔離驗證。 |
| 2026-11-03 | [PR #16](https://github.com/hun186/jaal-topology-viewer/pull/16) 已 Merge | HEAD `b2029b4111fc585273f3e12708642cc334b44f69` [Hosted CI 41660449981](https://github.com/hun186/jaal-topology-viewer/actions/runs/41660449981) 8/8 PASS，正式 Codex Review completed/0 Finding；Squash merge `1b9cd893531b3777b80f7efabb7bea170cbf5a85`，Linux/Windows 的獨立 Wheel 時間序列 consumer smoke PASS，不代表完整 Stage 4 驗收。 |
| 2026-11-03 | [PR #15](https://github.com/hun186/jaal-topology-viewer/pull/15) 已 Merge | HEAD `9e835cba849426d0bc2b23e5f806891a33d7998f` [Hosted CI 41659077144](https://github.com/hun186/jaal-topology-viewer/actions/runs/41659077144) 8/8 PASS，正式 Codex Review 完成 0 未解決 Finding，Squash merge `8fddffa1c94edeab0dce4cedafdd44a2ceeb1ac0`。動態時間片與佈局 physics 回歸測試已併入；不代表外部 consumer／公網部署完成。 |
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
- BL-002：PR #16 已取得 Ubuntu/Windows clean Wheel time-series consumer 及同埠 Flask callback/assets 的 Hosted CI 證據。剩餘完整外部 Stage 4 與更多版本／真實瀏覽器組合仍未驗收；本次新增非首頁 GalleryCase 時間軸隔離回歸，仍需當次 HEAD Hosted CI／Review 確認。

## Archive Index
- `.codex/archive/README.md`；日常任務不主動讀 archive。

## 維護
Current Focus 簡短；Recent Outcomes 上限 10，超過約 200 行／24 KB 濃縮。只保留持久可驗證成果，不保存秘密、敏感 payload、完整輸出或臨時猜測。
