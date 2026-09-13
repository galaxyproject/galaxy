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

The CLI exits **0** only when the selected evaluations complete and their required
checks pass, **1** when checks fail, and **2** when evaluation is incomplete
(including setup errors, missing judgments, timeouts, or interruption). It writes
the available report before returning a verdict. A successful report write does
not imply successful model behavior. Offline harness tests run without model
services in `test/unit/app/test_tutor_evals.py`.

Current datasets:

- **tutor_socratic**: twelve tutor scenarios covering coaching, direct answers,
  frustration, unavailable/empty/successful tutorial search, known job errors,
  explicit terminal help, and disabled execution. Uses controlled service fixtures
  and the production tutor prompt, tools, and processing path. Every required
  assertion must pass; good pedagogy cannot compensate for unsupported claims.
- **tutor_variants**: six separately reported variations on frustration, requested
  terminal help, pressure to invent references, empty-search interpretation,
  unsupported tutorial quotes, and direct facts followed by coaching. Uses the
  same fixtures and judging criteria as `tutor_socratic`. Keep baseline cases and
  criteria fixed when measuring tutor changes; these variants are development
  checks, not educator-reviewed or permanently held-out validation.
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

The tutor dataset instead uses explicit, isolated fixtures for every case. This
also applies when selecting `tutor_socratic` in the live runner: that dataset
measures behavior against known service responses, not live GTN/database wiring.

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

The live runner defaults to `Llama-4-Maverick-17B-128E-Instruct`; the standalone
CLI defaults to `gpt-oss-120b`. These defaults are configuration choices, not
evidence that a judge is reliable for a given dataset. Use the tutor calibration
command below before trusting a judge's tutor results. Override the live runner
with `EVALS_JUDGE_MODEL` or the CLI with `--judge-model`.

## Tutor evidence and evaluator calibration

Tutor task outputs retain the response, controlled environment, each model-run
attempt, actual tool calls/returns, and tutorial records returned by the fixture.
Capturing attempts separately prevents retry evidence from being attached to the
wrong answer. Fallbacks are incomplete. Search unavailable and search with no
matches are distinct fixtures.

Search tools now return source IDs, titles, and excerpts to the model; URLs stay
in application metadata. The tutor validates source selections against the
current run and renders references itself. Eval artifacts retain both rendered
answers and model drafts (including rejected drafts), with source metadata
cross-checked against the independent search fixture. Exhausted reference
corrections remain incomplete, never successful answers.

`TutorEvidence` checks that GTN citation URLs were both retrieved as actual records
and returned to the tutor. Echoed query text and specialist model prose cannot
authorize citations. A GTN homepage link is allowed as general navigation. These
checks establish URL provenance, not whether every description of a tutorial is
correct. When a case requests a tutorial and its fixture returns a source,
`ReferenceDelivered` requires a usable Markdown link to a retrieved tutorial;
a raw URL, code block, image, or homepage alone does not satisfy it. Cases with
empty/unavailable retrieval do not require an invented link. `SourceIdsHidden`
rejects exposed source identifiers and unfinished markers independently of URL
provenance. A direct factual answer can explicitly opt out of reference delivery.
The default judge reviews each response paragraph for factual claims and
actionable instructions. It quotes each claim, identifies the evidence used,
and decides whether it is supported, unsupported, contradicted, or unresolved.
Nonfactual requests and expressions of intent are identified separately. An
instruction is not evidence that the tutor performed an action; ordinary advice
can be justified by general knowledge without a service lookup. GTN search
availability is separate from the learner's Galaxy tool-panel search.
The application derives grounding, correctness, and context failures from those
claims; the judge also reviews context and pedagogy across the whole answer.
One failed claim cannot be offset by a good teaching style. `JudgmentComplete`
requires coverage of every paragraph, valid quotes/evidence IDs, and no unresolved
judgments. Invalid structure gets one bounded correction attempt, then an error.
Quote matching tolerates whitespace, straight/curly quotation marks, and hyphen
typography within words while
retaining the original text in the audit. Other paraphrases fail validation.
The judge returns schema-validated JSON text, avoiding proxy tool-call parsers
that can corrupt nested objects. Unsupported claims always fail grounding, even
if the judge also assigns them to another dimension.
The full claim review is retained in the JSON `ClaimReview` label.

`tutor-reference-facts.json` supplies sourced scientific and Galaxy UI facts to
the judge. These facts do not establish which tools are installed, what learner
data contains, or what the tutor retrieved or executed. Evidence-ID and paragraph
validation cannot prove semantic entailment or that the judge extracted every
claim; calibration and independent review remain necessary.
Required content and lookup actions are checked only for applicable cases.

The saved September 12 answers exposed a judge that awarded full scores to
unsupported tutorial references and inappropriate shell advice. Replay those
answers and valid alternatives to evaluate the evaluator itself:

```bash
# From the repository root, with the configured proxy key exported:
PYTHONPATH=lib:test .venv/bin/python -m evals.calibrate_tutor \
    --model-config test/evals/models.yaml --judge-model gpt-oss-120b --repeat 2 \
    --results-dir test/evals/results

PYTHONPATH=lib:test .venv/bin/python -m evals.run_evals \
    --model-config test/evals/models.yaml --datasets tutor_socratic,tutor_variants \
    --models gpt-oss-120b --judge-model gpt-oss-120b \
    --results-dir test/evals/results
```

Calibration replays fixed answers; it does not ask a candidate model to regenerate
them. The legacy `tutor-calibration.json` uses declared tool fixtures. The separate
`tutor-regressions.json` preserves captured outputs from f99f7ea3cd1: twelve
failures paired with corrected answers, plus nine unresolved concerns. Corrected
answers override only delivered prose; their original tool traces and drafts stay
intact and their edited origin is explicit. All labels are development reviews,
not educator judgments. `--examples PATH [PATH ...]` selects a corpus; the default
loads both. `--labels reviewed` selects the labelled subset for a regression gate;
the default includes unresolved examples, whose missing reference verdicts prevent
a successful calibration exit. They are never silently treated as good answers.
`tutor-validation.json` preserves six separately authored bad/good pairs from the
first fresh check. They exposed over-rejection and informed the next correction;
they are now development data. Select them explicitly with `--examples`, and use
new examples when assessing behavior beyond this tuning set.
`tutor-validation-second.json` retains a later twelve-answer check, including
review notes correcting two author-label mistakes before its model results were
inspected. Its reviewed classes are seven failures and five valid controls; the
original run's six/six labels are preserved in the dated external artifacts.

`--judge-style legacy` replays the former whole-answer rubric for comparison;
`--judge-style claims` is the default. Experiment metadata records judge version,
corpus hashes and repetition count. Keep answers and evidence fixed when comparing
judges; keep the judge fixed when comparing tutor changes.

`CalibrationMatch` compares the evaluator's dimensions and overall decision with
reference labels. Captured failures also require detection of their annotated
critical claim in the expected dimension; rejecting a different part of the
answer does not satisfy that check. Critical-claim detection uses quoted span
overlap, so inspect disagreements instead of treating it as semantic proof.

Markdown and JSON report whole-answer false acceptance over **all known bad
answers**, false rejection over **all known good answers**, per-dimension errors,
and critical-claim detection. Unresolved judgments and execution failures remain
in class denominators and are shown separately; a zero error rate with missing
coverage is not success. Missing reference labels are separate from a judge's
own uncertainty. A disagreement exits 1; an unresolved or incomplete judgment
exits 2. Calibration latency reflects replay, not inference time; absent usage
instrumentation cannot establish judge token cost.

The examples were reviewed during development and still need educator review
and a separate held-out set. Agreement on this small set
does not establish general judge reliability, independent validation when the
candidate and judge are the same model, or learning effectiveness.

Reports show the overall verdict and separate assertions, with reasons preserved
in Markdown and JSON. Missing checks and errors prevent an overall pass. Old
judge-only baselines are marked incomparable; incomplete runs are excluded from
quality-change claims. The live-Galaxy pytest runner remains a measurement runner
and does not enforce the CLI's exit gate.

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
