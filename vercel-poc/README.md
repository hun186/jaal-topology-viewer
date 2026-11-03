# Vercel Topology PoC — public, static and read-only

This is a client-only SVG concept demonstrator, **not** the Python Dash/Jaal server.
It uses the repository's fictional 77-role / 169-directed-pair example.
No real email, production database, login, telemetry, uploaded CSV, model or API key.
The department collapse is a fictional role grouping, **not Louvain**.
Original node IDs and directed relationships are preserved in source-derived graph.json.

## Build and verify

Run from repository root on Node 22:

~~~sh
node vercel-poc/build.mjs
node --test tests/test_vercel_poc.test.cjs
~~~

Serve the generated vercel-poc/dist folder as static files. Existing Windows
Chromium CI also executes python tests/vercel_poc_browser.py after the build.
The static builder is deterministic and rejects unexpected CSV schema/size.

## Strict merge-only quota policy

The root vercel.json explicitly sets git.deploymentEnabled=false. This disables
Vercel's automatic Git-based deployments for all branches, even if someone links
the project to the GitHub repository later. Do not enable Git auto-deploy in UI.

The only release automation is .github/workflows/vercel-poc-merge-only.yml.
It has only a trusted pull_request_target closed trigger, then strictly requires merged=true
and base=main, a relevant changed-file path, and an explicit deployment switch.
Ordinary pushes, new or updated PRs, CI/Review reruns, unrelated merges and
workflow_dispatch never create a Vercel deployment. Concurrency serializes
releases. Before deploying, it checks the Vercel API for an existing
production deployment with the same merge SHA, and fails closed on API errors.

## Required initial setup — authorized operator only

1. Create dedicated Vercel project jaal-topology-poc, with no automatic Git
   deployment and no existing production app/domain/secret reuse.
2. In GitHub repository Settings > Secrets and variables > Actions, set
   **variables** VERCEL_ORG_ID, VERCEL_PROJECT_ID, VERCEL_CLI_VERSION
   (a reviewed exact x.y.z version).
3. Create GitHub Environment vercel-poc restricted to main, with an
   **environment secret** VERCEL_TOKEN. Never paste token into source or chat.
4. Only after configuration is verified, set repository **variable**
   JAAL_VERCEL_POC_ENABLED to true. Until then deploy job is skipped.

A one-time, separately authorized deployment after a reviewed merge does not
prove that the GitHub variables and secrets are configured for future merges.
Public site is static-only; the full Python Jaal and Louvain remain local.
