# Interactive company communication demo

This example is a **fictional, reproducible graph**, not real people or real corporate emails. Its 77 synthetic roles originate from a one-to-one rename of the `TW Affairs` taxonomy subtree (82 internal source edge records / 81 distinct directed pairs); invented reply, peer and cross-department links create a 169-edge directed network.

## Launch in one command

After installing the project once from its repository root (`python -m pip install -e .`):

| Windows | Linux/macOS | Same demo |
| --- | --- | --- |
| `run-company-demo.bat` | `bash run-company-demo.sh` | `python -m jaal_topology --edges examples/company_communications.csv --metadata examples/company_people.csv -p 8059` |

These are commands to run at repository root, not live online preview links. Both scripts accept an optional port, e.g. `run-company-demo.bat 8060` and `bash run-company-demo.sh 8060`, and use paths relative to their own folder (safe from other working directories). The server binds to **127.0.0.1** only; visit `http://127.0.0.1:8059/` or the selected port. Stop it using Ctrl+C.

## Suggested guided demo

1. Keep the initial **網狀（全展開） / Network (fully expanded)** mode. Each arrow points **sender → recipient**; the diagram is not an organizational reporting chart.
2. Turn on **優先顯示中文名稱** to view the fictional bilingual role labels, then turn it off. Original English IDs remain the authority for search and relations.
3. Try the original Jaal Search / Filter / Color / Size tools. Search for `CEO / Executive Office`, `International Sales`, and `Finance & Analytics`.
4. Observe replies (two-way arrows), peer connections, cross-team links and directed cycles. The optional third CSV column (`relation`) is illustrative and **not read** by the current renderer.
5. Try **網狀（社群收攏・Louvain）**, a separate experimental communication-community view: click a cluster to expand its members, click a member to re-collapse. Edges between communities retain sender→recipient direction and show counts of unique distinct directed pairs. The older **網狀（收攏）** still means descendant collapse and is **not** appropriate for emails. The community mode uses directed Louvain seed 42 / resolution 1 on unweighted topology, not message frequencies; see [design and limitations](../docs/general_graph_community_collapse.md).

## Exact assets / reproducibility

- [company_communications.csv](company_communications.csv): `from,to,relation`; 169 unique directional sender-recipient pairs.
- [company_people.csv](company_people.csv): `ClassLabel,CT`; bilingual role labels.
- [company_communications_source_mapping.csv](company_communications_source_mapping.csv): original class label, renamed role, organizational branch, discovery depth.
- [source tree](https://github.com/hun186/text-category-profiler/blob/6cc3855ec5d726d5e207e866ca61b165f30ded88/ClassesTree/data/TopicTree.csv): source fixed commit for auditability.

This demo does not fetch upstream files at runtime, install packages automatically, claim live public availability, send emails, change data, or embed a second renderer. Browser visual acceptance is separate from CI HTTP-layout smoke checks.
