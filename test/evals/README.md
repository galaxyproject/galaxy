# Galaxy agent evals

Real-LLM evaluation harness for the agents in `lib/galaxy/agents/`. Built on
[pydantic-evals](https://ai.pydantic.dev/evals/). Runs on demand, **not in
CI** -- real LLMs cost money, are slow, and are flaky.

## What it does

Runs curated datasets against Galaxy agents, scores each model, and emits a
markdown comparison table. The point is to weigh models against each other
("is gpt-oss-120b on Jetstream good enough as a free default? does
Llama-4-Maverick win on error analysis?") and to iterate on prompts with
real measurement. Not run in CI.

Current datasets:

- **routing**: (query, expected handoff target) pairs against `QueryRouterAgent`.
  Scored by `HandoffMatch` (deterministic).
- **error_analysis**: prose failure descriptions against `ErrorAnalysisAgent`.
  Scored two ways: `MustMention` (deterministic keyword check) and `LLMJudge`
  (fuzzy "is the advice on-topic and actionable for this failure mode").
- **tool_recommendation**: "what tool should I use for X?" queries against
  `ToolRecommendationAgent`. Scored by `MustMentionAny` (any of a set of
  canonical tool names appears) plus optional `LLMJudge` with per-case rubrics.
  Runs without a live toolbox, so it measures the model's prior knowledge of
  Galaxy tools rather than grounded search behavior.
- **router_tool_use**: inventory/availability queries that should trigger
  router fast-path tool calls (`search_tools`, `search_workflows`,
  `list_histories`, `get_server_info`, `get_user_info`). Scored by
  `ToolCallMatch` -- did the model invoke at least one of the expected
  tools? Includes a regression case for the failure observed in
  galaxyproject/galaxy#21661 (comment 4367167981) where the router answered
  "what tools are installed?" with a generic essay instead of calling
  `search_tools`.
- **capabilities**: "what can you do?" groundedness against `QueryRouterAgent`.
  Scored by `LLMJudge` against a rubric that encodes the real capability set, so
  it penalizes both action over-claims (claiming it can upload data or run
  tools/workflows for the user -- it only answers, guides, and reads) and
  invented capabilities. Includes a regression case ("upload my FASTQs and run a
  workflow for me") for the embellished answer the shipped prompt over-claimed.
- **staining_quantification**: end-to-end bioimaging use case --
  brightfield RGB inputs, color deconvolution, per-ROI quantification,
  Omero export. Scored by `LLMJudge` against per-case rubrics for
  response substance. The routing decision for the same prompts is
  scored separately by the matching cases in the `routing` dataset, so
  a full flight check runs both. Cases needing a live Galaxy session
  (history sanity check, save-to-page) are off by default; pass
  `--include-galaxy-required` to include them.

## Layout

```
test/evals/
  datasets/                # One module per dataset
    routing.py
    error_analysis.py
  evaluators.py            # HandoffMatch, MustMention
  judge.py                 # Builds an OpenAIChatModel for use as LLM judge
  specs.py                 # DatasetSpec registry: dataset -> task + evaluators
  tasks.py                 # Wraps agents as pydantic-evals task callables
  run_evals.py             # CLI
  results/                 # Local-only run artifacts (gitignored). Keep
                           # baselines you care about somewhere outside the
                           # repo (the JSON sidecars are noisy). Filenames
                           # encode the repo SHA so any baseline pairs back
                           # to a commit.
```

## Two runners

The harness ships with two runners that share dataset definitions,
evaluators, and report format. Use whichever fits the question you're
asking.

### Fast loop -- standalone CLI (default)

`python -m evals.run_evals` builds `GalaxyAgentDependencies` from a
`MagicMock`'d `trans`, so the agents run without a live Galaxy. Fast
iteration, no Galaxy startup, ideal for prompt work and cross-model
comparison. Cases marked `requires_galaxy=True` are filtered out by
default.

### Real flight check -- pytest live runner

`test/integration/test_live_evals.py` runs the same datasets inside a
Galaxy integration-test fixture with a real `trans`. Seeds a demo
history via `test/evals/seed_staining_quantification_history.py`, runs
the `requires_galaxy=True` cases against it, writes a report to
`test/evals/results/` in the same shape as the CLI. Slower (Galaxy
startup), but the only path that actually exercises history-dependent
cases.

### Which to use

- Iterating on a prompt? **CLI.**
- Choosing between models? **CLI.**
- End-to-end flight check before a demo rehearsal? **Pytest live
  runner.**
- Cases involving "my history", "my analysis", or the history agent
  doing real tool calls? **Pytest live runner.**

## Running the CLI

Copy `test/evals/models.yaml.sample` to `test/evals/models.yaml`
(gitignored), list each model you want to evaluate with its proxy URL
and key, then run from the `test/` directory so the `evals.*` modules
import without an editable install:

```bash
. .venv/bin/activate
cd test
python -m evals.run_evals --model-config evals/models.yaml
```

That runs every model in the YAML against every dataset. Output goes to
stdout and to `test/evals/results/<date>-<datasets>-<sha>.md`.

You can still pass `--models gpt-oss-120b,Llama-4-Maverick-17B-128E-Instruct`
to restrict to a subset.

## Running the pytest live runner

```bash
export GALAXY_TEST_ENABLE_LIVE_LLM=1
export GALAXY_TEST_LIVE_EVALS=1
export GALAXY_TEST_AI_API_KEY=...
export GALAXY_TEST_AI_API_BASE_URL=http://localhost:4000/v1/
export GALAXY_TEST_AI_MODEL=gpt-oss-120b

# Optional: override which datasets/models/judge to run
# export EVALS_MODEL_CONFIG=/path/to/models.yaml
# export EVALS_DATASETS=staining_quantification
# export EVALS_MODELS=gpt-oss-120b
# export EVALS_JUDGE_MODEL=gpt-oss-120b

pytest test/integration/test_live_evals.py -v
```

The live runner always passes `include_galaxy_required=True`, so the
history-needing staining-quantification cases (`history_sanity_check`,
`summarize_to_page`, `report_takeaway`, `social_media_post`) actually
get exercised. Default scope is `staining_quantification` only;
override with `EVALS_DATASETS`.

The default judge is `Llama-4-Maverick-17B-128E-Instruct` rather than
`gpt-oss-120b` because gpt-oss-120b tends to grade itself too
charitably; Maverick scores hand-checked-correct responses more
accurately. Override with `EVALS_JUDGE_MODEL` if Maverick isn't
reachable. (The standalone CLI keeps `gpt-oss-120b` as its default
judge for baseline continuity.)

### Diffing against a previous run

Save baselines outside the repo (the JSON sidecars are noisy). Filenames
encode the repo SHA they were generated from, so any baseline file pairs
back to a specific commit.

```bash
cd test
python -m evals.run_evals \
    --baseline /path/to/baselines/2026-05-08-121624-bioinformatics_workflows+orchestrator_planning+tool_recommendation+router_tool_use-db9b1cb0799.md
```

`--baseline` looks for the JSON sidecar next to the markdown (each run writes
both) and renders a "Changes vs baseline" section listing per-case
regressions and improvements per (dataset, model). Useful when iterating
on a prompt -- run before, change the prompt, run with `--baseline` pointing
at the before file, see what moved.

### Useful flags

- `--datasets routing,error_analysis` -- pick which datasets to run (default
  is all registered).
- `--repeat 3` -- run each case N times to expose stochasticity. Per-case
  detail shows e.g. `2/3 [+1 ERR]` when one of three runs errored.
- `--judge-model gpt-oss-120b` -- model for fuzzy LLM-as-judge scoring
  (default gpt-oss-120b). Must also be declared in `--model-config`.
- `--only oom_137,exit_127` -- restrict to specific case names.
- `--include-galaxy-required` -- include cases that need a live Galaxy
  session (the `history_analyzer` ones). Off by default.
- `--max-concurrency 8` -- raise the per-model concurrency limit (default 4).
- `--model-config <yaml>` -- override default of `evals/models.yaml`.
- `--baseline <md-or-json>` -- diff results against a previous run.
- `--no-write` -- skip writing the report file.

## Adding cases

Edit the relevant `datasets/<name>.py`. Each case is the input the agent
sees plus whatever metadata the dataset's evaluators need (expected handoff
target for routing, must_mention keywords + failure_mode for error_analysis).

## Adding datasets

1. Drop a new module under `datasets/` exporting a `<name>_dataset(...)`
   function that returns a pydantic-evals `Dataset`.
2. Add a `make_<name>_task` to `tasks.py`.
3. Register a `build_<name>` in `specs.py`'s `SPECS` dict.

The CLI auto-includes anything registered in `SPECS`.

## How this relates to other agent test infrastructure

- `test/unit/app/test_agents.py::TestAgentUnitMocked` -- deterministic mocked
  unit tests, run in CI. Cover plumbing, not LLM behaviour.
- `test/unit/app/test_static_agent_backend.py` -- tests for the
  `StaticAgentRegistry`, which swaps real agents for canned-YAML responses.
  Complementary, not a substitute: static fixture is for orchestrator
  plumbing tests; evals are for measuring the LLM itself.
