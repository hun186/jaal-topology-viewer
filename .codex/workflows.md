# Development Workflows

> Current state；所有命令由 `pyproject.toml`、README、tests 或 `.github/workflows/ci.yml` 提供證據。

## 環境
- Python >=3.10（Hosted CI 3.11），`python -m pip`；Node.js 用於 `node --test`，CI 沒指定固定 Node 版本。
- 測試 runner 為 `ubuntu-latest`；Windows 實機及 Dash 2/3/4 組合尚未完全驗收。
- 無證實的必備 API key、外部服務或環境變數；CLI 在 `127.0.0.1` 開 HTTP server。

## Canonical Commands（repo root）
| 用途 | 命令 | 來源／邊界 |
| --- | --- | --- |
| 安裝 | `python -m pip install -e .` | CI／README |
| Browser local-cases JS | node --test tests/browser_cases.test.cjs | CSV parser, weights, scope, limits and backup schema |
| Browser local-cases Python | python -m unittest discover -s tests -p 'test_browser_cases.py' -v | GET-only Flask assets/CSP and gallery link |
| Browser local-cases Chromium | python tests/browser_cases_acceptance.py --evidence browser-evidence/local-cases | Actual file upload, two layouts, IndexedDB reload and JSON backup/restore; runs in Windows hosted CI |
| Python test | `python -m unittest discover -s tests -p "test_*.py" -v` | CI |
| JS test | `node --test tests/*.test.cjs` | CI；包含 `tests/stress_lab.test.cjs`，驗證四種規模／三個連通分量／決定性／上限 |
| Stress lab Flask smoke | `python -m unittest discover -s tests -p "test_stress_lab.py" -v` | 同源路由/CSP/GET-only/檔案 allowlist，整合 Windows `tests/browser_cases_acceptance.py` 真實 20k 畫布操作 |
| CLI help smoke | `python -m jaal_topology --help` | CI |
| 手動啟動 viewer | `jaal-topology --edges examples/relationships.csv --metadata examples/metadata.csv --root Root` | README；會持續提供 localhost server，非快速測試 |
| 替代啟動 | `python -m jaal_topology --edges examples/relationships.csv --root Root -p 8059` | README |
| Dash HTTP/asset smoke | `build_app` + Flask test_client，驗證 `/_dash-layout`、`16.jaal_visible_labels.js`、`17.jaal_structural_collapse.js`、`18.jaal_community_collapse.js`、`19.jaal_compact_layout.css`、`bootstrap.min.css` 皆回傳 200 | `.github/workflows/ci.yml` 有完整可複製程式 |
| Dash 2／3／4 固定版本回歸 | CI `dash-major-compat`（Ubuntu Python 3.11 + `dash==2.18.2`、`3.4.0`、`4.5.0`），`pip check` 並重跑完整 Python graph／WSGI／HTTP smoke；**不含**跨版本 Chromium 視覺測試 | `.github/workflows/ci.yml`；只代表這三個 exact versions 與 CI 平台，不推及所有 Dash patch 或 consumer Windows |
| Clean Wheel 兩系統隔離驗證 | CI `clean-wheel` matrix（ubuntu-latest／windows-latest）：`python -m pip wheel --no-deps --wheel-dir wheelhouse .`，fresh venv 裝 Wheel 後切出 checkout，實際驗證 Python import／Louvain／Dash HTML/JS/CSS／Flask same-port；後續 PR 加測可選 TemporalTimeline 事件時間片與第三方同埠 mount/callback（需當次 Hosted CI 證據才可宣稱 PASS） | `.github/workflows/ci.yml`；只驗套件 Wheel，不等於外部 consumer 全組合或 Stage 4 實機 |
| 多案例 Python/WSGI smoke | `python -m unittest discover -s tests -p "test_gallery.py" -v`；`python -m unittest discover -s tests -p "test_vercel_runtime.py" -v` | 三案例（有環／樹／多父 DAG）各自 Dash callback、URL/path/資產與初始模式；Windows Chromium 驗證真正 Dropdown 切換與 cycle guard |
| 企業郵件業務情境模擬 | `python -m unittest discover -s tests -p "test_email_simulation.py" -v`，加上 `test_vercel_runtime.py` 與 Windows Chromium | 檢驗種子可重現、回信時間與 thread、夜間事件、月結、部門內高互動、頻次加權 Louvain、唯讀 CSV 下載 |
| 時間演化事件／播放 | `python -m unittest discover -s tests -p "test_temporal.py" -v` 與 `node --test tests/temporal_playback.test.cjs`；Windows Chromium `tests/vercel_runtime_browser.py` | PR #15 新增的可選事件型時間片、前端播放、節點/有向邊可見性與同一畫布驗證；此列為 PR HEAD 行為，未 Merge 前非 main 穩定契約 |
| Vercel 真正 Jaal Flask PoC | `python -m pip install -r requirements.txt`，`python -m unittest discover -s tests -p 'test_vercel_runtime.py' -v`，`python tests/vercel_runtime_browser.py`（需 Playwright Chromium） | Hosted Python 3.12／Windows 實體 Chromium；`app.py` 直接重用 build_app()；CI 不部署，僅相關已 Merge 的 PR 有部署資格。舊 node vercel-poc/build.mjs 只作歷史 SVG 對照 |
| Windows Chromium smoke | `ci.yml` 先安裝 `dash==4.5.0` 執行 `python tests/browser_acceptance.py --evidence browser-evidence`，再由 `requirements.txt` 切換至 `dash==3.4.0`、執行 `python tests/browser_acceptance.py --port 8098 --evidence browser-evidence/dash3`；需 Playwright Chromium | 兩版皆以虛構資料實測同埠 iframe、根節點選取／還原、模式與實際 vis DataSet；只在 Hosted CI 對應工作 PASS 時成立，不代表 Dash 2 的 Windows Chromium 或 Stage 4 人工驗收 |
| Lint、format、typecheck、build | 沒有已確認 canonical 指令 | 不擅自捏造 |

## 驗證矩陣
| 變更 | 必要檢查 | 額外確認 |
| --- | --- | --- |
| 記憶／README 文件 | 交叉核對程式碼、命令、連結、敏感資訊、diff | 若改契約／命令，適度擴增 smoke |
| CSV、root、bounds | Python test | BOM、無效列、多父、環、超限 |
| Mode、JS、label | Python + Node tests | 實際 browser、動畫與焦點 |
| WSGI／Dash／assets | Python + Node + Hosted CI HTTP smoke | consumer same-port 及版本相容 |
| 下游 Git SHA 升級 | Upstream CI、Review | consumer pin/provenance/Stage 4 CI、Windows 視覺驗收 |
| 對外部署／release | 先安全與發布審核 | localhost PASS 不是公網可部署證據 |

## 已知測試基準與限制
- Fixture：`examples/relationships.csv`、`examples/metadata.csv`；測試使用 `tempfile` 不改寫來源。
- 2026-11-04 主線 PR #20 merge `fcb980d3c68465321987bc082dfca1f1943eb421`：其 HEAD `0a8c724` [Hosted CI 41741363056](https://github.com/hun186/jaal-topology-viewer/actions/runs/41741363056) 8/8 PASS，Windows Chromium 覆蓋當次預設 Dash 4 的 root scope/reset；本工作新增釘版本 3.4/4.5 的雙版本 browser 以**本 PR 的最新 CI** 為準，不視為已執行。
- 每個 PR 依 `REPOSITORY_SETUP.md` 執行最新 HEAD Hosted CI 與正式 Codex Review，0 unresolved findings 才能 Merge；不得以自己撰寫的備註冒充獨立 review。

## Full Jaal local scale acceptance
- CMD / Conda Prompt: `start-gallery.bat` (local fixed 500–20k + three-component options).
- Full Graph factory/contracts: `python -m unittest discover -s tests -p 'test_scaled_demo.py' -v`.
- Existing official CI + Windows browser acceptance remains required for each PR HEAD. Large Jaal 20k visual performance is hardware-dependent; CI correctness cannot replace on-device measurement.

- Windows launch after Anaconda-base `comm` import failure: create dedicated `jaal-viewer` Python 3.11 Conda environment, install requirements and editable project there, then run `start-gallery.bat` (uses dedicated `.venv`/named Conda environment only, refuses mixed `base`).

- Local Flask CLI on loopback now enables the six fixed synthetic large scenarios by default; set `JAAL_ENABLE_LARGE_LOCAL=0` to disable, or `1` to force local enabled. Vercel and ordinary WSGI imports remain four-case only. UI/banner and batch launcher warn of RAM/CPU cost. Windows Chromium validates all five temporal Dropdown popups, 35px options, nonoverlap, visible labels and viewport bounds.
