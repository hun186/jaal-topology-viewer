# Architecture

> Current state；具體行為以 `jaal_topology/` 為準。

## 系統邊界
- 此 repo 對任意有向關係 CSV 提供獨立、唯讀、大小受限的 Jaal viewer；不依賴 text classification 的核心、模型或 WorkPool。
- 上游：關係／metadata CSV，由 consumer 準備。下游：localhost browser 或 Flask same-origin iframe。
- Stage 4 consumer 的 root 下拉、sidebar、iframe 自動高度與分類資料屬應用層，不回流為本 repo 硬依賴。

## 元件與資料流
| 模組 | 角色 |
| --- | --- |
| `data.py` | CSV BOM/header/ID parsing，去重，metadata，root directed traversal，hard caps |
| `cli.py`／`__main__.py` | argparse、stderr/exit code、loopback run |
| `viewer.py` | Graph→Jaal DataFrame、原版 Jaal 控制、Dash clientside callbacks、safe tooltip |
| `modes.py` | 四種 legacy 模式與實驗 Louvain 模式 options；由 hierarchy 切回 network 時明確復原 physics／smooth |
| `community.py` | NetworkX 有向 Louvain 分群、固定種子、direction-preserving aggregates |
| `assets/` | JS 中文 label／structural collapse／Louvain community projection、local Bootstrap CSS |
| `integration.py` | `DispatcherMiddleware` 在既有 Flask WSGI 同 port 掛載 child Dash |

1. `load_graph` 逐份讀關係 CSV；保留有向邊與多父／環，去除相同的邊。
2. 以可選 `ClassLabel,CT` metadata 附加顯示名稱，不改原始 ID。
3. `select_subgraph` 依 root 沿 child 遍歷，保留所有兩端在子圖的原始邊並執行 limits。
4. `build_app` 準備 DataFrame、Jaal 原有回呼、四種 legacy 模式＋實驗社群控制、Louvain membership 與套件內資產。
5. CLI `127.0.0.1:8059` 或 Flask WSGI prefix 提供互動圖。

## 不變條件
- Original node ID 是搜尋及關係權威；中文僅顯示，不回寫 CSV。
- 匯入最多 100,000 unique edges；子圖預設 250 nodes/5000 edges，硬限 3000/5000。
- 無可視邊、未知 root、無效資料或超限會 `GraphInputError`；不產生 dummy graph。
- HTML tooltip escape；不把 CSV 文本插入可執行 JS；browser JS 來自此套件。
- 同一 mount path 不可重複；callback／assets 需帶 prefix；原版 Jaal Search/Filter/Color/Size 不應遺失。
- 渲染大型依賴在 `build_app` 才載入；不在 import 時全圖渲染。

## 錯誤與安全
- CLI 捕捉 `GraphInputError`／`OSError` 回報 stderr + exit 2；argparse 也用 code 2；無 database transaction 或重試機制。
- `mount_flask` 要在 host 開始服務前呼叫，沒有另一個監聽 socket；沒有自動 CSV reload。
- 只有 loopback 預設，不等於公開部署安全；Dash/Windows/browser matrix 仍須額外驗證。

## 修改路由
- CSV/schema/limits → `data.py`, `cli.py`, `tests/test_graph.py`。
- 四種 legacy 模式＋Louvain／翻譯／動畫 → `community.py`, `modes.py`, `viewer.py`, `assets/`, `test_browser.test.cjs`、`browser_acceptance.py`。
- Flask same-port → `integration.py`、Python WSGI test、Hosted CI。
- 下游升級 → `REPOSITORY_SETUP.md`、consumer exact pin 與其 CI。
