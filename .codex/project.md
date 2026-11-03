# Project Profile

> Current state；以程式碼、設定與 CI 為權威，無日期流水帳。

## Metadata
- 初始化狀態：`INITIALIZED`
- 最後查證日期：2026-11-03（台灣）
- 查證基準：`main` merge commit `47942ac3bd08d8cbcc615fa215c5e5eef286f486`；[PR #5](https://github.com/hun186/jaal-topology-viewer/pull/5) 已於 2026-11-03 Merge。下游 [text-category-profiler PR #227](https://github.com/hun186/text-category-profiler/pull/227) 已合併，將 consumer pin 更新到同一 SHA；使用者 Stage 4 候選實機驗收 9 項 PASS、consumer Hosted Windows/Ubuntu CI PASS，但 Dash 2/3/4 全矩陣及乾淨外部環境仍未證明。
- 維護 repository：`hun186/jaal-topology-viewer`

## 一句話目的
以獨立 Python 套件將關係 CSV（與可選名稱 metadata）轉為唯讀、大小有界的 Jaal 有向圖檢視器，可用 localhost CLI 啟動或於 Flask 同埠掛載。

## 使用者、輸入、輸出
- 使用者：檢視分類樹或其他有向關係的 Python 開發者，以及下游 `text-category-profiler`。
- 輸入：一個以上 parent/child CSV、可選 `ClassLabel,CT` metadata、root 與渲染上限。
- 輸出：Dash/Jaal 互動圖（四種 legacy 模式加一個實驗 Louvain 社群收攏模式；中文名稱預設關閉）；**不回寫**任一 CSV。
- 非目標：BertScript／TCFMain／WorkPool／模型訓練，consumer 的 root 搜尋下拉、sidebar 與 iframe autoheight，正式 Python Runtime 接受任意公開輸入、自動同步下游。Vercel PoC 已改為相同 Jaal/Dash 程式的受限公網展示，僅載入 77/169 虛構資料，不提供上傳。

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
| `app.py`, `requirements.txt`, `vercel.json` | Vercel Flask WSGI 真正 Jaal/Dash 展示，只載入虛構固定 CSV，不改本機 CLI |
| `jaal_topology/__init__.py`, `data.py` | `Graph`、`GraphInputError`、`load_graph`、`select_subgraph` |
| `cli.py`, `__main__.py` | `jaal-topology` 與 `python -m jaal_topology` |
| `viewer.py`, `modes.py` | `build_app`、五種模式、原版 Jaal Search/Filter/Color/Size；左側可收合、頂部工具列可捲動、全版繪圖（可按 Esc 恢復）、可展開說明，不卸載原版 Network |
| `community.py` | 定種子、保留方向的 Louvain 拓樸分群與方向計數 |
| `assets/` | Browser JS（包含社群投影／收攏）、Bootstrap CSS、專用精簡工具列 CSS（19.jaal_compact_layout.css、20.jaal_focus_escape.js），從套件直接提供 |
| `integration.py` | `mount_flask`；Flask 同來源、同 port |
| `tests/`, `examples/` | Python/Node 測試、最小 CSV fixture |
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
