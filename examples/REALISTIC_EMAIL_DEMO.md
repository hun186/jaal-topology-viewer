# Fictional business-process-driven email dataset

This case is a **reproducible simulation**, not real people, a real company,
or a model statistically calibrated against real corporate email logs.
It replaces the default gallery's historical taxonomy-renaming example;
the older 77-person/169-pair topology remains selectable separately as
**舊版通訊拓樸（類別樹改編）** for honest comparison.

## Reproducibility and behavioral assumptions

- Generator: `jaal_topology.email_simulation.simulate_company_email`
- Fixed seed: `20261103`; 20 business days beginning 2026-10-05
- Roles only (no person names, addresses or message bodies). Nine
  organizational divisions, with a defined manager and departmental head
- Regular working-hour exchanges prefer peers and assigned managers;
  direct reciprocal answers share a thread and occur later than the original
- Client proposals bridge Sales, Product, Finance and Operations; client
  escalations bridge Customer Success, Engineering and Product
- Two **explicit incident days** generate concentrated after-hours
  Engineering–Security–Operations communication and CTO escalation
- Month-end Finance/Operations/People/Sales coordination is stronger near
  the end of the period; CEO sends limited periodic division-head updates
- An independent random generator introduces variation in participant
  selection, timing and reply propensity **inside** these business rules.
  It does not choose arbitrary uniform random endpoints.

This is a **plausible demonstration hypothesis**, not an empirical estimate
of actual mail rates. Public users should not interpret graph centrality,
mail volume, team frequency, performance, risk or rank as real-company facts.

## Data and traceability

Each synthetic mail event contains `event_id,timestamp,thread_id,from,to,
workflow,subject,reply_to`. The timestamp has no asserted UTC offset;
it illustrates local office hours and two after-hours incidents. `reply_to`
refers to another event in the same thread and reply direction is reversed.

The Jaal graph is a read-only aggregation of events by directed `from→to`;
a single pair can represent multiple messages. The graph retains unique
pairs for ordinary topology operations, and has an optional `edge_counts`
map for the simulated number of mail events. Ordinary CSV graphs do not
carry this map and preserve their pre-existing Louvain behavior.

In the new simulation case:

- Edge width / tooltip represent the number of **synthetic emails** over
  20 working days; node `SentEmails` / `ReceivedEmails` / `TotalEmails`
  provide numeric fields for Jaal Size controls.
- Louvain partitions use directed pair weights equal to total message count.
  Community-to-community labels still show **unique directed pairs**, not
  event totals; they must not be used as message-volume measures.
- Full network view reveals actual role-to-role directional links.
  Community mode highlights workflow cross-function collaboration, but
  its clusters are not guaranteed to correspond to reporting lines.
- The viewer's 2-column, optional-metadata CLI is unchanged.

## Public read-only evidence

When running the repository's `app.py` locally on port 8099:

- `http://127.0.0.1:8099/`: realistic default gallery case
- `/demo/mail-events.csv`: all synthetic message events
- `/demo/mail-edges.csv`: unique sender→recipient pairs and event counts
- `/demo/mail-summary`: workflow distribution, response count, within-team
  share and graph size (all marked fictional)

The public endpoints are fixed GET routes, have no user-supplied file path,
no real email service connection, no authentication keys, and do not write
files. **No Vercel quota is consumed by local app testing.**

## Test locally

```bat
git switch main
git pull --ff-only
.venv-vercel\Scripts\python.exe -m unittest discover -s tests -p "test_email_simulation.py" -v
.venv-vercel\Scripts\python.exe -m unittest discover -s tests -p "test_vercel_runtime.py" -v
.venv-vercel\Scripts\python.exe -c "from app import app; app.run(host='127.0.0.1', port=8099, debug=False)"
```

This demo is served by Vercel only after a separately authorized, eligible
Merge release and real cloud acceptance; Git/PR/Push auto deployments remain
disabled to respect the daily API quota.
