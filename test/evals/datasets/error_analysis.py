"""Error-analysis dataset: did the agent point at the actual cause?

Each case is a natural-language failure description (mock stderr / exit code
in prose form). Scored two ways:

- MustMention (deterministic): response contains the keyword(s) we consider
  essential -- exit code, parameter name, distinguishing phrase.
- LLMJudge (fuzzy): given the specific failure mode, is the advice on-topic
  and actionable? Built per-case so the rubric mentions the actual cause.
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
        "name": "oom_137",
        "query": "My job failed with exit code 137 and stderr shows 'Killed'. What happened?",
        "must_mention": ["memory", "137"],
        "failure_mode": "OOM kill -- the process exceeded its memory allocation and was killed by the kernel.",
    },
    {
        "name": "command_not_found_samtools",
        "query": "I got 'command not found: samtools' in my job stderr. How do I fix this?",
        "must_mention": ["samtools", "PATH"],
        "failure_mode": "Tool dependency missing -- the samtools binary is not on the execution host's PATH or in the conda environment.",
    },
    {
        "name": "exit_127",
        "query": "My job failed with exit code 127. Stderr is empty. What now?",
        "must_mention": ["127", "command"],
        "failure_mode": "Exit 127 typically means 'command not found' even when stderr is empty -- the shell could not locate the binary.",
    },
    {
        "name": "bwa_oom",
        "query": "Why did my BWA job fail? The log shows 'out of memory'.",
        "must_mention": ["memory"],
        "failure_mode": "OOM during alignment -- BWA needs more RAM than was allocated.",
    },
    {
        "name": "disk_full",
        "query": "Job failed with 'No space left on device' during sort step.",
        "must_mention": ["disk", "space"],
        "failure_mode": "Disk full on the work directory or scratch -- sort spills to disk and ran out of room.",
    },
    {
        "name": "missing_input",
        "query": "Tool errored: 'FileNotFoundError: input.fastq does not exist'.",
        "must_mention": ["input", "file"],
        "failure_mode": "Missing or wrongly-named input file -- the tool received a path that does not resolve.",
    },
    {
        "name": "invalid_param",
        "query": "Picard MarkDuplicates failed with 'Cannot use BARCODE_TAG with VALIDATION_STRINGENCY=STRICT'. Help?",
        "must_mention": ["VALIDATION_STRINGENCY", "BARCODE_TAG"],
        "failure_mode": "Conflicting parameter settings -- two Picard options are mutually exclusive in this combination.",
    },
    {
        "name": "permission_denied",
        "query": "Cluster job failed with 'Permission denied' when writing to /scratch/output.bam.",
        "must_mention": ["permission", "scratch"],
        "failure_mode": "Filesystem permissions issue -- the job's user does not have write access to the target directory.",
    },
]


_RUBRIC_TEMPLATE = """\
You are reviewing the response from an error-analysis agent that helps users
debug failed Galaxy bioinformatics jobs.

For this case, the actual failure mode is:
{failure_mode}

Score the response between 0.0 and 1.0 on how well it helps the user. A
high score requires all of:
1. The response identifies the specific failure mode (not just generic
   debugging advice).
2. The suggested next steps are actionable and relevant to that cause.
3. The response does not mislead the user toward an unrelated cause.

Return a number; no commentary.
"""


def error_analysis_dataset(
    judge_model: Model | None = None,
    only: list[str] | None = None,
) -> Dataset[str, str, dict[str, Any]]:
    """Build the error_analysis Dataset.

    If judge_model is given, attaches a per-case LLMJudge whose rubric
    embeds the failure mode for that case.
    """
    cases: list[Case[str, str, dict[str, Any]]] = []
    for proto in _PROTO_CASES:
        if only and proto["name"] not in only:
            continue
        evaluators: tuple = ()
        if judge_model is not None:
            rubric = _RUBRIC_TEMPLATE.format(failure_mode=proto["failure_mode"])
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
                metadata={
                    "must_mention": proto["must_mention"],
                    "failure_mode": proto["failure_mode"],
                },
                evaluators=evaluators,
            )
        )
    return Dataset(name="error_analysis", cases=cases)
