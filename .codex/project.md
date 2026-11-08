# Project Profile

> Current state；以程式碼、設定與 CI 為權威，無日期流水帳。

## Metadata
- 初始化狀態：`INITIALIZED`
- 最後查證日期：2026-11-04（台灣）
- 查證基準：`main` Squash merge commit `fcb980d3c68465321987bc082dfca1f1943eb421`；[PR #16](https://github.com/hun186/jaal-topology-viewer/pull/16) 的 Ubuntu/Windows isolated Wheel 時間演化 Consumer smoke 已於 2026-11-03 Merge、Hosted CI 8/8 PASS；[PR #15](https://github.com/hun186/jaal-topology-viewer/pull/15) 的可選事件時間片／前端播放已 Merge；先前 [PR #14](https://github.com/hun186/jaal-topology-viewer/pull/14) 提供四案例與虛構郵件頻次加權。下游 [text-category-profiler PR #227](https://github.com/hun186/text-category-profiler/pull/227) 仍釘舊版 `47942ac3bd08d8cbcc615fa215c5e5eef286f486`，不代表新時間功能已通過 consumer 驗證。Vercel 公網 Python 仍未證實 READY（先前 HTTP 402／部署需另行授權）。
- 維護 repository：`hun186/jaal-topology-viewer`

## 一句話目的
以獨立 Python 套件將關係 CSV（或可選的有時間戳合成事件）轉為唯讀、大小有界的 Jaal 有向圖檢視器，可用 localhost CLI 啟動或於 Flask 同埠掛載。

## 使用者、輸入、輸出
- 使用者：檢視分類樹或其他有向關係的 Python 開發者，以及下游 `text-category-profiler`。
- 輸入：一個以上 parent/child CSV、可選 `ClassLabel,CT` metadata、root 與渲染上限。
- 輸出：Gallery 為 Dash/Jaal 互動圖（四種 legacy 模式加一個實驗 Louvain 社群收攏模式；中文名稱預設關閉）；**不回寫**任一 CSV。
- 非目標：BertScript／TCFMain／WorkPool／模型訓練，consumer 的 root 搜尋下拉、sidebar 與 iframe autoheight，正式 Python Runtime 接受任意公開輸入、自動同步下游。Vercel PoC 已改為相同 Jaal/Dash 程式的受限公網展示，僅載入 77/169 虛構資料，不提供伺服器端上傳；另有 GET-only /my-cases/ 瀏覽器本機工作區，IndexedDB 保存使用者 CSV 匯入案例。

## 技術與執行
| 項目 | 已確認 | 證據 |
| --- | --- | --- |
| Python | >=3.10；CI 用 3.11 | `pyproject.toml`、`ci.yml` |
| 套件 | `jaal-topology-viewer` 0.1.0；`jaal>=0.1.9`、`pandas>=1.5`、`networkx>=3.2,<4`；未見 lockfile | `pyproject.toml` |
| UI | Jaal / Dash；可選 Flask / Werkzeug WSGI mount | `viewer.py`、`integration.py` |
| Browser | 內含 JS 與 Bootstrap CSS；Node.js 測試、Windows Hosted Chromium 真實 iframe smoke（非 Stage 4 實機驗收） | `assets/`、`tests/browser_acceptance.py`、`ci.yml` |
| OS | CI `ubuntu-latest` + `windows-latest` headless Chromium；下游 Stage 4 特定 Louvain 候選已取得 Windows 使用者實機 9 項 PASS（consumer PR #227），全 Dash/OS 矩陣仍待驗 | `ci.yml`、consumer PR #227 |
| 遠端依賴 | 執行時無必需遠端服務；安裝可能需要取得套件 | `README.md` |

## 入口與 Repository 地圖
| 路徑 | 作用 |
| --- | --- |
| `app.py`, `requirements.txt`, `vercel.json` | Vercel Flask WSGI 真正 Jaal/Dash 四個原始案例＋一個延遲載入 500 人虛構郵件案例（仍使用原版 Jaal，普通 3000/5000 上限保留）（新增固定種子的企業郵件業務情境，保留原拓樸示意／組織樹／DAG）；唯讀 CSV 下載供驗證，不改本機 CLI |
| `jaal_topology/__init__.py`, `data.py` | `Graph`、`GraphInputError`、`load_graph`、`select_subgraph` |
| `cli.py`, `__main__.py` | `jaal-topology` 與 `python -m jaal_topology` |
| `viewer.py`, `modes.py`, `neighborhood.py` | `build_app`、五種模式、原版 Jaal Search/Filter/Color/Size；可搜尋原 ID／中文別名根節點，依 out/in/both 0–10 hop 或全部可達顯示唯讀局部誘導子圖，清除選擇還原全圖；左側可收合、非 sticky 工具列、Esc 全版退出，原版 Network 不卸載 |
| `community.py` | 原有拓樸分群保持不變；僅具明確逐邊郵件數的示範圖使用事件量加權 Louvain，社群邊數仍是獨立寄收件對數 |
| `email_simulation.py` | 固定種子、20 工作天的虛構業務流程發信事件與收發量彙總（人名／帳號／信件內容皆非真實） |
| `assets/` | Browser JS（包含社群投影／收攏、時間片動畫與 22.jaal_local_focus.js 局部子圖投影）、Bootstrap CSS、精簡工具列 CSS，直接由套件提供 |
| `integration.py` | `mount_flask`；Flask 同來源、同 port |
| `scaled_demo.py`, `start-gallery.bat` | 本機 opt-in 原版 Jaal 大型案例：固定規則完整 Graph + EmailEvent 500／3000／5000／20000 節點及 500 人三連通分量；從原 Gallery 選單按需載入；Vercel 只額外公開 500 人案例，3k 以上以及三連通分量均維持本機專用 |
| `stress_lab.py`, `stress_lab/` | PR #25 歷史 Canvas 實驗室仍可直接連線，但已從原 Gallery 工具列移除，不能誤當完整 Jaal 壓測 |
| `browser_cases.py`, `browser_cases/` | Gallery 入口連至本機案例工作區；UTF-8 CSV/TSV 解析、原生 SVG 網狀／階層預覽、IndexedDB 與 JSON 備份在瀏覽器進行，伺服器僅 GET 靜態資產；不能視為原版五模式/Louvain/Temporal 已支援使用者檔案 |
| `gallery.py` | 新的可選多案例 registry：1..20 明確登記的 GalleryCase，以同來源不同路徑各自掛載真實 Jaal/Dash，搜尋／收攏 callback 狀態隔離 |
| `tests/`, `examples/` | Python/Node 測試、合成 CSV fixture、Windows Chromium 下真實 Jaal/visdcc 的根節點局部子圖互動驗證 |
| `vercel-poc/`, `vercel.json`, `.github/workflows/vercel-poc-merge-only.yml` | Vercel 真實 Python Jaal PoC；舊 SVG 留作歷史對照；Git 自動部署禁止、相關 PR 合併後才可依 opt-in workflow 發布（預設關閉） |
| `.github/workflows/ci.yml` | Hosted CI；Ubuntu Python／Node／Dash 與 Windows Chromium 互動／iframe smoke，留存瀏覽器截圖 |
| `REPOSITORY_SETUP.md` | 唯一原始碼來源、下游 exact SHA 升級 |
| `AGENTS.md`, `.codex/` | Codex 路由、現況與記憶 |

## 核心資料／信任／相容性邊界
- CSV ID 是字面字串，允許多父節點、跨連結、環；中文僅用於顯示，缺失翻譯沿用 ID。
- 最多匯入 100,000 不重複有向邊；選擇圖預設 node/edge 限額 250/5000，絕對限額 3000/5000。
- 無邊、未知 root、壞格式或超上限拒絕；CLI 預設只綁定 `127.0.0.1:8059`。
- `text-category-profiler` 透過固定 Git commit 消費套件；本 repo 是 portable Python/JS 核心唯一來源，不複製 runtime 回下游。
- 测試資料可使用 `examples/*.csv`；`.gitignore` 排除本機 cache、venv、build。
- 待確認：未涵蓋的 Windows／Dash 版本矩陣與乾淨外部環境。已確認 consumer PR #227 的特定 Stage 4 實機 PASS，不等於所有版本組合均驗收。

## README 閘門
- `ADEQUATE`：既有 README 已有正確用途、安裝、CLI、整合、測試及限制，保留不重寫。
- 目的／技術／入口／地圖如有變動，更新本檔；成果放 `memory.md`、取捨放 `decisions.md`。
