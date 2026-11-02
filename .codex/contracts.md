# Interface Contracts

> Current state；維持已被外部 consumer 使用的 Python、CSV、CLI、WSGI 與 JS 模式界面。

## Index
| ID | 契約 | 權威 |
| --- | --- | --- |
| CONTRACT-001 | 關係與 metadata CSV | `data.py`, `test_graph.py` |
| CONTRACT-002 | Graph／Python API | `__init__.py`, `data.py` |
| CONTRACT-003 | CLI | `pyproject.toml`, `cli.py` |
| CONTRACT-004 | Flask WSGI 同埠 | `integration.py`, `viewer.py` |
| CONTRACT-005 | 四種模式／browser assets | `modes.py`, `viewer.py`, `assets/` |

## CONTRACT-001 — CSV
- 一個以上關係 CSV，UTF-8/BOM；可無 header，或 `parent,child`、`from,to`、`source,target`、`母類別,子類別`、`#母類別,子類別`；前兩欄定有向邊，額外欄位忽略。
- Node ID 使用 trim 後的字面字串；空值、缺欄、空圖或不合法 CSV 拒絕；重複邊去重，保留方向、多父／環／cross-links。
- Metadata 預設 `ClassLabel,CT`，可指定欄名；缺少或空白翻譯沿用 ID；已有節點的重複 metadata ID 拒絕。

## CONTRACT-002 — Python
- `Graph(edges, nodes, translations)` 是 frozen dataclass，內部 dict 不保證深度 immutable。
- `load_graph(edge_files, metadata_file=None, *, metadata_id_column="ClassLabel", metadata_label_column="CT") -> Graph`。
- `select_subgraph(graph, root=None, *, max_nodes=250, max_edges=5000) -> Graph`；root 沿有向 child 可達，保留子圖內原始邊；root=None 為有界全圖。
- 100,000 unique input edges；max_nodes 1..3000，max_edges 1..5000；非法值／超限丟 `GraphInputError`。
- `ASSETS_DIR` 由 package export；`build_app` 位於 `viewer.py`。

## CONTRACT-003 — CLI
- `jaal-topology`／`python -m jaal_topology`；`--edges` 必填可重複，另有 metadata/欄位 mapping、root、max-nodes、max-edges、port/-p。
- Port 預設 8059，只 bind `127.0.0.1`；無 visible edge 不建 app。輸入錯誤 stderr + exit 2；成功進入持續運行 server。
- stdout 為人類可讀文字，不保證機器解析的 JSON 契約。

## CONTRACT-004 — Flask
- `mount_flask(flask_server, graph, *, mount_path="/jaal-topology", root=None)`，於伺服器開始服務前掛載並回傳 child Dash。
- path 要以 `/` 開頭、不可為 `/`、不可尾隨 `/` 或含 `//`；重複掛載拒絕。
- `DispatcherMiddleware` 同來源同 port；Dash callback／資產 URL 包含 mount prefix。

## CONTRACT-005 — Browser
- 支援 `network`、`network-collapsed`、`hierarchical`、`hierarchical-collapsed`。
- `layout_options` deep-copy base options，切回 network 需顯式還原 hierarchy／physics／edge smooth／node styles。
- 中文翻譯預設關閉；搜尋及 tooltip 用原 ID。JS `16.jaal_visible_labels.js`、`17.jaal_structural_collapse.js` 由本套件提供。
- 正確 Node/unit/HTTP behavior 不等於 Windows 實機視覺已驗收。

## Cross-repo
- 消費端固定 reviewed Git SHA；上游 merge 不自動改 consumer。更動接口需同步測試，breaking change 要記錄版本與遷移方案。
