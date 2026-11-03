# Interface Contracts

> Current state；維持已被外部 consumer 使用的 Python、CSV、CLI、WSGI 與 JS 模式界面。

## Index
| ID | 契約 | 權威 |
| --- | --- | --- |
| CONTRACT-001 | 關係與 metadata CSV | `data.py`, `test_graph.py` |
| CONTRACT-002 | Graph／Python API | `__init__.py`, `data.py` |
| CONTRACT-003 | CLI | `pyproject.toml`, `cli.py` |
| CONTRACT-004 | Flask WSGI 同埠 | `integration.py`, `viewer.py` |
| CONTRACT-005 | 四種 legacy 模式＋實驗 Louvain 社群模式／browser assets | `modes.py`, `viewer.py`, `assets/` |
| CONTRACT-006 | 多案例展示 Gallery API | `gallery.py`, `viewer.py`, `integration.py`, `test_gallery.py` |
| CONTRACT-007 | 可搜尋根節點與有向 k-hop 局部子圖 | `neighborhood.py`, `viewer.py`, `assets/22.jaal_local_focus.js`, `test_neighborhood.py` |

## CONTRACT-001 — CSV
- 一個以上關係 CSV，UTF-8/BOM；可無 header，或 `parent,child`、`from,to`、`source,target`、`母類別,子類別`、`#母類別,子類別`；前兩欄定有向邊，額外欄位忽略。
- Node ID 使用 trim 後的字面字串；空值、缺欄、空圖或不合法 CSV 拒絕；重複邊去重，保留方向、多父／環／cross-links。
- Metadata 預設 `ClassLabel,CT`，可指定欄名；缺少或空白翻譯沿用 ID；已有節點的重複 metadata ID 拒絕。

## CONTRACT-002 — Python
- `Graph(edges, nodes, translations, edge_counts={})` 是 frozen dataclass；新增可選的 `edge_counts[(from,to)]=positive integer` 只供明確逐件彙總的寄收件示例。舊有三參數呼叫與原始 CSV 解析器不變；`select_subgraph` 同步裁切計數。內部 dict 不保證深度 immutable。
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
- 四種相容 legacy：`network`、`network-collapsed`、`hierarchical`、`hierarchical-collapsed`；實驗第五模式：`network-community-collapsed`，不重新定義原 `network-collapsed` 的子孫節點語義。
- `layout_options` deep-copy base options，切回 network 需顯式還原 hierarchy／physics／edge smooth／node styles。
- 使用 `community.detect_louvain` 以有界有向圖、固定 seed=42、resolution=1、distinct directed edges 執行 NetworkX Louvain；**舊圖 `edge_counts={}` 維持 unit-weight topology-only**，新情境郵件圖才依經確認的合成寄收件次數加權。合成社群 node ID 僅存在顯示層，原 ID 與來源 CSV 不修改。社群聚合後仍區分 A→B／B→A；既有邊標籤仍顯示*獨立有向邊數*而非郵件封數。
- 中文翻譯預設關閉；搜尋及 tooltip 用原 ID，filtered browser 檢視亦保留所選中文標籤。JS `16.jaal_visible_labels.js`、`17.jaal_structural_collapse.js`、`18.jaal_community_collapse.js` 由本套件提供。
- Windows Hosted Chromium 可驗證實際 visdcc DataSet、同埠 iframe、搜尋與收攏的部分契約；不代表使用者 Windows Stage 4 drag/focus/Filter/Color/Size 實機完整驗收。

## CONTRACT-006 — Gallery

- `GalleryCase(key, title, graph, root=None, initial_mode="network")` 為已載入 Graph 的唯讀選擇條目；`create_gallery_app(cases, *, route_prefix="/cases") -> dash.Dash` 回傳第一個案例 Dash，`.server` 為同埠 Flask/WSGI host。
- 案例數 1..20；`key` 僅限安全 ASCII slug、不可重複；每案必須有非空標題、Graph。第一案保留 `/`；其餘為 `/cases/<key>/`，由 `DispatcherMiddleware` 各自掛載。
- `build_app` 與 `mount_flask` 新增*可選*導航參數；原有單圖參數、callback ID/JSON、中文及五模式不變。案例切換用同來源 `dcc.Location` 導向另一 URL，觸發新 Dash app 頁面載入；不以同頁 graph.data 換圖，避免原版 Jaal 搜尋/篩選 callback 保留上一案例的 Graph。
- 初始模式需是五種受支援值；若圖形有環，不得以子樹結構收攏初始模式啟動，拒絕不安全案例；切換不回寫來源資料、不掃描磁碟、不提供檔案上傳。
- 公開案例的 allowlist 與 CSV 於 `app.py` 中宣告；Vercel CI 不部署，僅符合條件的 Merge 可發布。

## CONTRACT-007 — Interactive local scope

- 原生 `build_app(graph)` 的工具列新增可搜尋的原 ID／中文別名根節點選單，清除表示全圖。最大範圍僅限原本已驗證載入的 3000 node/5000 edge Graph；不繞過 bounds。
- `reachable_node_ids(graph, root, hops=2, direction="out")` 回傳 graph.nodes 原排序 ID，hops 為 0..10 或 "all"，方向 out/in/both，BFS unique-ID、防循環，錯誤 GraphInputError。不改寫 graph、edges、translations。
- 前端 `jaal-local-scope` Store 由 server 驗證，瀏覽器只接收原始 ID 列表，JS `22.jaal_local_focus.js` 在 vis DataSet 中隱藏無關節點與有向邊、或提供各收攏模式對應的 induced subgraph，不改 `graph.data` 原始 Graph。Reset 復原所有原始節點／邊。
- 時序圖局部範圍取全期間原始 Graph 可達性，與每個時間窗活躍狀態取交集，不會在每格重算根節點／跳動。既有 Search/Filter 和 Python `root=` 初始化可維持原使用方法。

## Cross-repo
- 消費端固定 reviewed Git SHA；上游 merge 不自動改 consumer。更動接口需同步測試，breaking change 要記錄版本與遷移方案。
