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
| Python test | `python -m unittest discover -s tests -p "test_*.py" -v` | CI |
| JS test | `node --test tests/*.test.cjs` | CI |
| CLI help smoke | `python -m jaal_topology --help` | CI |
| 手動啟動 viewer | `jaal-topology --edges examples/relationships.csv --metadata examples/metadata.csv --root Root` | README；會持續提供 localhost server，非快速測試 |
| 替代啟動 | `python -m jaal_topology --edges examples/relationships.csv --root Root -p 8059` | README |
| Dash HTTP/asset smoke | `build_app` + Flask test_client，驗證 `/_dash-layout`、`16.jaal_visible_labels.js`、`17.jaal_structural_collapse.js`、`bootstrap.min.css` 皆回傳 200 | `.github/workflows/ci.yml` 有完整可複製程式 |
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
- 2026-11-02 主線 `fc49c0d2559c71df79f438e070ef3610e7093e5a` [Hosted CI PASS](https://github.com/hun186/jaal-topology-viewer/actions/runs/41480969808)。本次初始化只有遠端程式／CI 證據，**沒有聲稱本機執行上述命令**。
- 每個 PR 依 `REPOSITORY_SETUP.md` 執行最新 HEAD Hosted CI 與正式 Codex Review，0 unresolved findings 才能 Merge；不得以自己撰寫的備註冒充獨立 review。
