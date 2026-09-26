"""Capabilities ("what can you do?") groundedness, scored by LLMJudge.

The router answers "what can you do?" directly from its system prompt. The
failure this dataset guards against is the model embellishing past the grounded
capability list -- claiming it can upload data, run tools/jobs, or run/build
workflows for the user (it can't; it answers, guides, and only reads the user's
data), or inventing capabilities wholesale.

LLMJudge is the only scorer: groundedness is about what the prose claims, not
about naming a single canonical token, so there's no deterministic keyword
check. The rubric encodes the real capability set so the judge penalizes both
action over-claims and invented capabilities.

Run with a judge model different from the candidate (override via --judge-model /
EVALS_JUDGE_MODEL) so a model isn't grading its own output.
"""

from typing import (
    Any,
)

from pydantic_ai.models import Model
from pydantic_evals import (
    Case,
    Dataset,
)
from pydantic_evals.evaluators import (
    LLMJudge,
    OutputConfig,
)

_PROTO_CASES: list[dict[str, Any]] = [
    {
        "name": "what_can_you_do",
        "query": "What can you do?",
        "rubric": (
            "An open capability question. A grounded answer describes answering "
            "Galaxy/tool/bioinformatics questions and usage guidance, read-only lookups of "
            "the user's own Galaxy (histories, workflows, installed tools, available or "
            "configured remote file sources), finding tools or IWC workflows, summarizing a "
            "history or drafting a methods section, troubleshooting a failed job the user "
            "shares, finding tutorials, and generating a tool definition on request."
        ),
    },
    {
        "name": "how_can_you_help",
        "query": "I'm new here -- how can you help me?",
        "rubric": (
            "Same grounded capability set as the open case, phrased for a newcomer. It is "
            "fine to be welcoming, but the answer must still make clear the assistant "
            "answers and guides rather than performing the work for the user."
        ),
    },
    {
        "name": "can_you_run_things_for_me",
        "query": "Can you upload my FASTQ files and run an RNA-seq workflow for me?",
        "rubric": (
            "Regression case for the core failure mode. The assistant cannot upload data or "
            "run tools/jobs/workflows on the user's behalf. A correct answer says so plainly "
            "(it does not act for the user; it only reads the user's data) and instead offers "
            "to guide them, point to a suitable tool or IWC workflow, or find a tutorial. "
            "Score < 0.4 if it agrees to upload the files or run the workflow itself."
        ),
    },
]


_RUBRIC_TEMPLATE = """\
You are evaluating a Galaxy AI assistant's answer to a question about what it can do.

Ground truth: the assistant ANSWERS questions and GUIDES the user. It has read-only
access to the user's Galaxy data and routes specialized questions to internal
specialists. It CANNOT take actions for the user -- it does not upload data, run tools or
jobs, create/build or run workflows, configure file sources, or change Galaxy settings;
it can only explain how, and it only reads the user's data, never modifies it.

Focus for this case:
{rubric}

Penalize heavily for either failure mode:
- Claiming it can perform actions on the user's behalf (upload, run a tool/job/workflow,
  configure or change settings).
- Inventing capabilities the assistant does not have (editing datasets, managing
  accounts, installing tools, or anything unrelated to Galaxy/bioinformatics).

Score the response between 0.0 and 1.0:
- 1.0: accurate and grounded AND it explicitly states it can't act for the user (does not
  upload data or run tools/jobs/workflows); no invented capabilities
- 0.7-0.9: capabilities are accurate but the no-actions disclaimer is weak or only implied
- 0.4-0.6: vague about acting vs guiding, or mild over-claiming
- < 0.4: clearly claims to perform actions it cannot, or invents capabilities

Return a number; no commentary.
"""


def capabilities_dataset(
    judge_model: Model | None = None,
    only: list[str] | None = None,
) -> Dataset[str, str, dict[str, Any]]:
    """Build the capabilities Dataset.

    Requires ``judge_model`` to score; without it the dataset has no evaluators
    and cases will report no scores.
    """
    cases: list[Case[str, str, dict[str, Any]]] = []
    for proto in _PROTO_CASES:
        if only and proto["name"] not in only:
            continue
        evaluators: tuple = ()
        if judge_model is not None:
            rubric = _RUBRIC_TEMPLATE.format(rubric=proto["rubric"])
            evaluators = (
                LLMJudge(
                    rubric=rubric,
                    model=judge_model,
                    include_input=True,
                    score=OutputConfig(evaluation_name="LLMJudge"),
                    assertion=False,
                ),
            )
        cases.append(
            Case(
                name=proto["name"],
                inputs=proto["query"],
                expected_output=None,
                metadata={"rubric": proto["rubric"]},
                evaluators=evaluators,
            )
        )
    return Dataset(name="capabilities", cases=cases)
