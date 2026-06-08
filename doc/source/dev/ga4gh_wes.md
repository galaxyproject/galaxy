---
myst:
  substitutions:
    GA4GH_WES: GA4GH Workflow Execution Service (WES)
---

# Developing Against the GA4GH WES API

This is a developer-facing companion to the [admin GA4GH docs](../admin/ga4gh.md). The
admin docs cover configuring and verifying the service; this guide walks an API client
through actually submitting and monitoring Galaxy workflow runs over the {{ GA4GH_WES }}
v1.0.0 wire protocol.

Every request below targets a Galaxy server and uses Galaxy's workflow formats. The curl
examples were exercised against a live development server; the responses shown are real
(ids shortened/anonymized).

## Example clients

If you would rather drive the flow below from a runnable tool than from raw curl, two small
reference clients walk exactly this sequence (discover → stage → submit → poll → outputs →
tasks). Both expose a subcommand-per-endpoint CLI plus a `demo` subcommand that runs the
whole example end to end, and both are published to PyPI so they run straight under
[uv](https://docs.astral.sh/uv/) without installing anything:

```bash
export GXY_WES_API_KEY=...
uvx gxy-wes demo --galaxy-url http://localhost:8080            # requests-only
uvx gxy-wes-bioblend demo --galaxy-url http://localhost:8080   # BioBlend-backed
```

- **[gxy-wes](https://github.com/jmchilton/gxy-wes)** — a hand-rolled `requests` wrapper
  with no dependency beyond `requests`, so it stays dependency-light and reads as a literal
  transcript of the wire protocol.
- **[gxy-wes-bioblend](https://github.com/jmchilton/gxy-wes-bioblend)** — the same CLI
  surface, but every call is routed through a [BioBlend](https://bioblend.readthedocs.io/)
  `GalaxyInstance`, showing the shape a BioBlend-based application would use.

```{important}
These two packages are **illustrative examples, not production-supported projects** — they
exist to make this document executable and to show the API two different ways. Do not build
a product on them. For real workflow-execution tooling use
[Planemo](https://planemo.readthedocs.io/) or talk to the Galaxy API through
[BioBlend](https://bioblend.readthedocs.io/) directly.
```

## How Galaxy maps onto WES

WES is workflow-engine agnostic. Galaxy implements it on top of its existing workflow
invocation machinery, so the WES nouns map onto Galaxy nouns:

| WES concept        | Galaxy concept                                                       |
| ------------------ | -------------------------------------------------------------------- |
| `run` / `run_id`   | `WorkflowInvocation` (the `run_id` is the encoded invocation id)     |
| `task` / `task_id` | An invocation step, or a single job within a collection-mapping step |
| run `outputs`      | Invocation outputs (HDAs / HDCAs), decorated with DRS URIs           |
| `workflow_type`    | A Galaxy workflow format (see below) — **not** CWL/Nextflow/WDL      |

`workflow_type` is one of Galaxy's own two workflow formats:

- **`gx_workflow_format2`** — the gxformat2 ("Format2") YAML format. CWL-like, hand-authorable.
- **`gx_workflow_ga`** — the native `.ga` JSON format produced by Galaxy's workflow editor.

`workflow_type_version` is currently accepted as a free-form string (e.g. `"1.0.0"`); the
type itself is what matters, and Galaxy will also auto-detect it from the workflow body
(`class: GalaxyWorkflow` ⇒ format2; a top-level `steps`/`workflow` key ⇒ `.ga`).

## Base URL and authentication

All endpoints live under `/ga4gh/wes/v1/`. With a local dev server that is:

```
http://localhost:8080/ga4gh/wes/v1/
```

Every endpoint except `service-info` requires authentication. Galaxy uses its normal API
key auth — pass `x-api-key: <key>` (the WES spec's bearer-token scheme is not used). Get a
key for an existing account with HTTP basic auth:

```bash
curl -s -u "you@example.com:password" \
  http://localhost:8080/api/authenticate/baseauth
# {"api_key": "317ab17d..."}
```

Anonymous and inactive accounts are rejected on submission and on every run-scoped read.

## 1. Discover the service

`service-info` is public and advertises the supported formats, engine parameters, and
filesystem protocols.

```bash
curl -s http://localhost:8080/ga4gh/wes/v1/service-info | jq .
```

Trimmed to the WES-relevant fields (the real response also carries
`system_state_counts`, `auth_instructions_url`, `tags`, and the standard GA4GH
`organization`/`version`/`environment` keys):

```json
{
  "id": "localhost.wes",
  "name": "Galaxy WES API",
  "type": { "group": "org.ga4gh", "artifact": "wes", "version": "1.0.0" },
  "workflow_type_versions": {
    "gx_workflow_ga": { "workflow_type_version": ["1.0.0"] },
    "gx_workflow_format2": { "workflow_type_version": ["1.0.0"] }
  },
  "supported_wes_versions": ["1.0.0"],
  "supported_filesystem_protocols": ["http", "https", "file", "s3", "gs"],
  "workflow_engine_versions": {
    "galaxy": { "workflow_engine_version": ["1.0.0"] }
  },
  "default_workflow_engine_parameters": [
    { "name": "history_name", "type": "string", "default_value": "" },
    { "name": "history_id", "type": "string", "default_value": "" },
    {
      "name": "preferred_object_store_id",
      "type": "string",
      "default_value": ""
    },
    { "name": "use_cached_job", "type": "boolean", "default_value": "false" }
  ]
}
```

## 2. Provide the workflow and its inputs

A WES `RunRequest` is `multipart/form-data`. The fields Galaxy honors:

| Field                                         | Required              | Notes                                                                                                               |
| --------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `workflow_type`                               | yes                   | `gx_workflow_format2` or `gx_workflow_ga`. Must match the auto-detected type or you get a 400.                      |
| `workflow_type_version`                       | yes                   | Free-form string, e.g. `"1.0.0"`.                                                                                   |
| `workflow_url`                                | one of url/attachment | A URL Galaxy can fetch (`http(s)`, `s3`, `gs`, `file`, `base64://`) **or** a `gxworkflow://` reference (see below). |
| `workflow_attachment`                         | one of url/attachment | The workflow file uploaded inline.                                                                                  |
| `workflow_params`                             | no                    | JSON object of workflow inputs (see below).                                                                         |
| `workflow_engine_parameters`                  | no                    | JSON object of Galaxy-specific run options (see below).                                                             |
| `tags`                                        | no                    | Accepted but currently not persisted onto the invocation.                                                           |
| `workflow_engine` / `workflow_engine_version` | no                    | Accepted; informational.                                                                                            |

### `workflow_params` — wiring up inputs

Galaxy workflow inputs are keyed by the workflow's **input label**, and dataset inputs are
references to data that already exists in Galaxy. Galaxy invokes with `inputs_by="name"`,
so the keys are the workflow input names.

A dataset input is a `{"src": ..., "id": ...}` reference:

```json
{ "input1": { "src": "hda", "id": "1e8ab44153008be8" } }
```

`src` is `hda` for a single dataset or `hdca` for a dataset collection; `id` is the encoded
content id. Simple parameter inputs (integers, text, booleans) are passed as plain JSON
values under their input name.

WES has **no data-staging endpoint** of its own. You stage inputs through Galaxy's normal
API first (create a history, upload/fetch datasets) and then reference them here.

### `workflow_engine_parameters` — Galaxy run options

A JSON object. Recognized keys (also advertised in `service-info`):

| Key                         | Effect                                                                           |
| --------------------------- | -------------------------------------------------------------------------------- |
| `history_id`                | Run into this existing history (encoded id). Otherwise a new history is created. |
| `history_name`              | Name for the auto-created history (default `"WES Run"`).                         |
| `preferred_object_store_id` | Object store for the run's outputs.                                              |
| `use_cached_job`            | `"true"`/`"false"` string — reuse equivalent prior job results.                  |

### Referencing a workflow already in Galaxy: `gxworkflow://`

Galaxy adds a non-standard URL scheme so you don't have to ship the workflow body on every
submission. Use it as `workflow_url`:

```
gxworkflow://<encoded_workflow_id>            # the StoredWorkflow (latest version)
gxworkflow://<encoded_workflow_id>?instance=true  # a specific Workflow instance
```

The caller must own the workflow (or be an admin). With `gxworkflow://`, Galaxy skips
import and invokes the stored workflow directly. `workflow_type` is still required by the
form but is **not** validated against the stored workflow in this case — the
"must match the auto-detected type or 400" check only applies to inline
`workflow_attachment` / fetched `workflow_url` submissions.

## 3. Submit the run

Staging step (Galaxy-native, abbreviated) — create a history and upload one dataset:

```bash
KEY=317ab17d...; BASE=http://localhost:8080
HIST=$(curl -s -X POST "$BASE/api/histories" -H "x-api-key: $KEY" \
  -H 'Content-Type: application/json' -d '{"name":"WES Tutorial"}' | jq -r .id)
HDA=$(curl -s -X POST "$BASE/api/tools/fetch" -H "x-api-key: $KEY" \
  -F "history_id=$HIST" \
  -F 'targets=[{"destination":{"type":"hdas"},"elements":[{"src":"pasted","paste_content":"line one\nline two\n","ext":"txt","name":"wes_input"}]}]' \
  | jq -r '.outputs[0].id')
```

A minimal Format2 workflow (`simple.gxwf.yml`):

```yaml
class: GalaxyWorkflow
name: Simple Workflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
```

Submit it (the WES `POST /runs`):

```bash
curl -s -X POST "$BASE/ga4gh/wes/v1/runs" -H "x-api-key: $KEY" \
  -F "workflow_type=gx_workflow_format2" \
  -F "workflow_type_version=1.0.0" \
  -F "workflow_params={\"input1\":{\"src\":\"hda\",\"id\":\"$HDA\"}}" \
  -F "workflow_engine_parameters={\"history_id\":\"$HIST\"}" \
  -F "workflow_attachment=@simple.gxwf.yml;type=application/x-yaml"
```

```json
{ "run_id": "33b43b4e7093c91f" }
```

The `run_id` is the encoded Galaxy invocation id. Batch invocations (multiple invocations
from one request) are rejected by WES.

## 4. Monitor the run

Abbreviated status:

```bash
curl -s "$BASE/ga4gh/wes/v1/runs/33b43b4e7093c91f/status" -H "x-api-key: $KEY"
# {"run_id":"33b43b4e7093c91f","state":"RUNNING"}
```

Full run log — outputs are decorated with DRS URIs so a client can hand them straight to
the DRS API:

```bash
curl -s "$BASE/ga4gh/wes/v1/runs/33b43b4e7093c91f" -H "x-api-key: $KEY" | jq .
```

```json
{
  "run_id": "33b43b4e7093c91f",
  "request": null,
  "state": "COMPLETE",
  "run_log": null,
  "task_logs_url": "/ga4gh/wes/v1/runs/33b43b4e7093c91f/tasks",
  "task_logs": null,
  "outputs": {
    "wf_output_1": {
      "src": "hda",
      "id": "417e33144b294c21",
      "workflow_step_id": 30,
      "drs_uri": "drs://drs.localhost:8080/hda-4dcf52aeee371f21"
    }
  }
}
```

Notes on the run log:

- `request` is always `null` — Galaxy does not persist the original `RunRequest`, so it
  cannot be reconstructed.
- `task_logs` is intentionally `null` (deprecated in the WES spec). Use `task_logs_url`.
- Only HDA (single-dataset) outputs get a `drs_uri`; collection (HDCA) outputs carry an
  encoded `id` but no DRS URI.

### State mapping

WES has a single flat `State` enum (`QUEUED`, `INITIALIZING`, `RUNNING`, `COMPLETE`,
`EXECUTOR_ERROR`, `CANCELING`, `CANCELED`, ...). A Galaxy run is a `WorkflowInvocation`,
whose state is mapped onto that enum (`GALAXY_TO_WES_STATE` in `services/wes.py`):

| Galaxy invocation state    | WES state        | Meaning                                                 |
| -------------------------- | ---------------- | ------------------------------------------------------- |
| `new`                      | `QUEUED`         | Invocation created, not yet scheduling.                 |
| `requires_materialization` | `INITIALIZING`   | Deferred inputs are being materialized.                 |
| `ready`                    | `INITIALIZING`   | Ready for a scheduling iteration.                       |
| `scheduled`                | `RUNNING`        | Fully scheduled; jobs are running/queued.               |
| `completed`                | `COMPLETE`       | Scheduling done and every job reached a terminal state. |
| `failed`                   | `EXECUTOR_ERROR` | The invocation itself failed to schedule.               |
| `cancelled`                | `CANCELED`       | Invocation was cancelled.                               |
| `cancelling`               | `CANCELING`      | Cancellation requested, in progress.                    |
| (anything unmapped)        | `UNKNOWN`        | Fallback; should not occur for current states.          |

Poll `status` (or the run log `state`) until the state is terminal: `COMPLETE` (success),
`EXECUTOR_ERROR` (failure), or `CANCELED` (cancelled). Keep polling while it is any of the
non-terminal states (`QUEUED`, `INITIALIZING`, `RUNNING`, `CANCELING`).

#### Why `completed` ⇒ `COMPLETE`, even when a job failed

This is intentional and important: **a failed job does not make the run unsuccessful.**
WES `state` describes the run (the invocation), not individual jobs. Galaxy's `completed`
means scheduling finished and all jobs reached a terminal state (`ok`, `error`, `skipped`,
`paused`, ...) — and a job ending in `error` is frequently part of a perfectly normal,
valid execution path. For example, a workflow can route a step through a _filter-failed_
collection operation precisely so that some jobs are allowed to fail and the failures are
filtered out downstream; the invocation still completes successfully.

So:

- The only invocation state that maps to `EXECUTOR_ERROR` is Galaxy's own `failed` — i.e.
  the invocation could not be scheduled — **not** "some job errored."
- Clients should **not** infer run failure from a non-zero per-task `exit_code`. Per-task
  `exit_code`s (from the tasks endpoint) are for inspecting individual steps, not for
  deciding whether the run as a whole succeeded.
- Determine run success from the run `state` (`COMPLETE`); inspect outputs and per-task
  detail for finer-grained results.

## 5. Tasks (per-step / per-job detail)

`task_logs_url` points at a paginated task list. A `task_id` is the step `order_index`
(e.g. `"0"`, `"1"`), or `order_index.job_index` (e.g. `"1.0"`, `"1.2"`) for the individual
jobs of a collection-mapping step.

```bash
curl -s "$BASE/ga4gh/wes/v1/runs/33b43b4e7093c91f/tasks" -H "x-api-key: $KEY" | jq .
```

```json
{
  "task_logs": [
    {
      "id": "0",
      "name": "input1",
      "exit_code": null,
      "stdout": null,
      "stderr": null
    },
    {
      "id": "1",
      "name": "first_cat",
      "exit_code": 0,
      "stdout": "/api/jobs/417e33144b294c21/stdout",
      "stderr": "/api/jobs/417e33144b294c21/stderr"
    }
  ],
  "next_page_token": null
}
```

`stdout` / `stderr` are URLs to plain-text job-output endpoints
(`GET /api/jobs/{job_id}/stdout` and `/stderr`). Steps with no underlying job — input
steps, for example — have `null` `exit_code`, `stdout`, and `stderr` (as `id: "0"` shows
above). Fetch a single task with `GET /ga4gh/wes/v1/runs/{run_id}/tasks/{task_id}`.

### Pagination

Both `GET /runs` and `GET /runs/{id}/tasks` use opaque keyset (cursor) tokens, not
offsets. Pass `page_size` (1–100, default 10); if more results exist the response includes
`next_page_token`, which you echo back as `page_token` on the next request. Do not try to
decode or construct tokens yourself.

```bash
curl -s "$BASE/ga4gh/wes/v1/runs?page_size=2" -H "x-api-key: $KEY"
curl -s "$BASE/ga4gh/wes/v1/runs?page_size=2&page_token=<next_page_token>" -H "x-api-key: $KEY"
```

`GET /runs` only ever lists the authenticated user's own runs.

## 6. Cancel a run

```bash
curl -s -X POST "$BASE/ga4gh/wes/v1/runs/33b43b4e7093c91f/cancel" -H "x-api-key: $KEY"
# {"run_id": "33b43b4e7093c91f"}
```

This requests cancellation of the underlying invocation; the run then transitions through
`CANCELING` to `CANCELED`.

## Errors

Errors come back as Galaxy's standard JSON error body (`{"err_msg": ..., "err_code": ...}`)
with a matching HTTP status. The ones a client is most likely to hit:

| Situation                                                                        | Status |
| -------------------------------------------------------------------------------- | ------ |
| Missing/invalid required form field (e.g. no `workflow_type`)                    | 400    |
| `workflow_type` disagrees with the auto-detected type (attachment / fetched URL) | 400    |
| Malformed `gxworkflow://` URI                                                    | 400    |
| Submit while anonymous                                                           | 403    |
| Submit while logged in but inactive (unactivated account)                        | 403    |
| Run / task id does not exist                                                     | 404    |
| Invalid `task_id` format                                                         | 404    |

Access to resources you do not own is **not** reported uniformly — watch for this:

- Reading a **run** you don't own → `403` (`AuthenticationRequired`).
- Submitting against a **history** you don't own → `404` (`ObjectNotFound`).
- A `gxworkflow://` reference to a **workflow** you don't own → `403`
  (`ItemAccessibilityException`).

So a `404` on submission can mean "your history id is wrong" _or_ "that history belongs to
someone else"; don't assume `404` always means the object is absent.

## Endpoint summary

| Method | Path                                          | Auth     | Purpose                                 |
| ------ | --------------------------------------------- | -------- | --------------------------------------- |
| GET    | `/ga4gh/wes/v1/service-info`                  | public   | Capabilities and supported formats      |
| POST   | `/ga4gh/wes/v1/runs`                          | required | Submit a run (`multipart/form-data`)    |
| GET    | `/ga4gh/wes/v1/runs`                          | required | List the user's runs (keyset paginated) |
| GET    | `/ga4gh/wes/v1/runs/{run_id}`                 | required | Full run log + DRS-decorated outputs    |
| GET    | `/ga4gh/wes/v1/runs/{run_id}/status`          | required | Abbreviated `{run_id, state}`           |
| POST   | `/ga4gh/wes/v1/runs/{run_id}/cancel`          | required | Request cancellation                    |
| GET    | `/ga4gh/wes/v1/runs/{run_id}/tasks`           | required | Paginated task list                     |
| GET    | `/ga4gh/wes/v1/runs/{run_id}/tasks/{task_id}` | required | Single task detail                      |

## Known limitations and gotchas

- **Run `COMPLETE` reflects the invocation, not individual jobs** — by design, a failed
  job does not make the run fail (a failed job can be a normal, valid path, e.g.
  filter-failed). Only an invocation that fails to schedule maps to `EXECUTOR_ERROR`. Do
  not infer run failure from a per-task `exit_code`. See §4.
- **Inputs must be pre-staged** — there is no WES upload endpoint; stage datasets via the
  Galaxy API and reference them by `{src, id}` in `workflow_params`.
- **`request` is never returned** in the run log — the original `RunRequest` is not stored.
- **DRS URIs only on HDA outputs**, not on collection outputs.
- **`tags` are not persisted** to the invocation, and run summaries return `tags: {}`.
- **`service-info` `auth_instructions_url` is a placeholder** (`"TODO"`).
- The generated Pydantic models under `lib/galaxy/schema/wes/` are produced by
  `gen.sh` from the upstream GA4GH OpenAPI spec with no Galaxy post-processing — treat
  them as regenerable and avoid hand edits.

## Source pointers

- Router: `lib/galaxy/webapps/galaxy/api/wes.py`
- Service: `lib/galaxy/webapps/galaxy/services/wes.py`
- Generated models: `lib/galaxy/schema/wes/` (regenerate via `gen.sh`)
- Shared GA4GH service-info builder: `lib/galaxy/webapps/galaxy/services/ga4gh.py`
- API tests (worked examples for every endpoint): `lib/galaxy_test/api/test_wes.py`
