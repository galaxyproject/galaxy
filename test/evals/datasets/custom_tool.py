"""Custom-tool generation dataset: can the model author a valid Galaxy tool?

Each case is a natural-language "wrap this command as a tool" request against
``CustomToolAgent``. Scored several ways (wired up in ``specs.build_custom_tool``):

- ToolProduced (deterministic): did the agent return a structured, schema-valid,
  lint-clean tool at all? This is the headline metric -- it folds in
  structured-output reliability on the ~33 KB nested schema plus every
  authoring-time validator.
- FirstAttemptOk (deterministic): did it succeed WITHOUT spending a validator
  retry? Isolates how easy the schema + prompt make it to get right first time --
  the quantity schema-shrinking, low temperature, and retry-anchoring target.
- ToolYamlContains (deterministic): does the generated YAML contain the structural
  features the request implies (``yaml_must_contain``)? Partial credit.
- LLMJudge (fuzzy): given the request, is the tool actually correct -- sensible
  container, command that wires inputs to outputs, right input/output shapes?

No live toolbox is needed: tool authoring is self-contained (validate + lint), so
the mocked-deps path is a faithful measurement of model + schema quality. It does
NOT exercise actual tool *build* (``create_tool_from_source``); that end-to-end
check belongs in the live integration eval.
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
        "name": "boxplot_welch_ttest",
        "query": (
            "Create a custom Galaxy tool that takes a tabular dataset with columns including "
            "'group' (Vehicle or Tx) and numeric measurements, generates a boxplot comparing "
            "Vehicle vs Tx groups, performs a Welch's t-test, and displays the p-value above the "
            "plot. The tool should accept the input dataset, allow selection of the measurement "
            "column, and output the plot (e.g., PNG) and a text file with the p-value."
        ),
        "yaml_must_contain": ["type: data", "$(inputs.", "from_work_dir"],
        "rubric": (
            "A correct tool wraps a Python/R container (e.g. a biocontainers image with pandas + "
            "matplotlib/scipy, or an R container), takes the tabular dataset as a data input, lets "
            "the user pick the measurement column (a text/column/select input -- NOT a hardcoded "
            "column), and declares TWO outputs: the plot image and a text file with the p-value, "
            "each claimed via from_work_dir. The shell_command must reference the inputs via "
            "$(inputs.NAME) / $(inputs.NAME.path)."
        ),
    },
    {
        "name": "head_n_lines",
        "query": (
            "Make a Galaxy tool that returns the first N lines of an uploaded text file, where N "
            "is a user-provided integer (default 10). Output the truncated file."
        ),
        "yaml_must_contain": ["type: data", "type: integer", "$(inputs.", "from_work_dir"],
        "rubric": (
            "A correct tool uses a lightweight container (busybox/coreutils/python), a single data "
            "input for the file, an integer input for N (with a default), runs something like "
            "`head -n $(inputs.n) $(inputs.infile.path)`, and claims one output via from_work_dir."
        ),
    },
    {
        "name": "multi_file_concatenate",
        "query": (
            "I want a Galaxy tool that concatenates MULTIPLE uploaded text files (the user selects "
            "two or more) into a single combined output file."
        ),
        # "multiple: true" is the correct modeling for several datasets in one input;
        # this is exactly the case where a naive `min:`-on-single-data definition 500s.
        "yaml_must_contain": ["multiple: true", "from_work_dir"],
        "rubric": (
            "A correct tool models the input as a single data parameter with multiple: true (NOT a "
            "single-dataset input, and NOT min/max without multiple), then concatenates the files "
            "(e.g. `cat $(inputs.files)` ) into one output claimed via from_work_dir."
        ),
    },
    {
        "name": "grep_filter_with_mode",
        "query": (
            "Create a Galaxy tool that filters lines of a text file by a user-supplied search "
            "pattern, with a dropdown to choose whether to keep matching or non-matching lines. "
            "Output the filtered file."
        ),
        "yaml_must_contain": ["type: select", "options", "type: text", "from_work_dir"],
        "rubric": (
            "A correct tool has a data input for the file, a text input for the pattern, and a "
            "select (dropdown) input with options for keep-matching vs invert-match (mapping to "
            "`grep` vs `grep -v`), and claims the filtered output via from_work_dir."
        ),
    },
    {
        "name": "split_to_collection",
        "query": (
            "Make a Galaxy tool that splits a multi-FASTA file into one file per sequence and "
            "returns the results as a dataset collection."
        ),
        "yaml_must_contain": ["type: collection", "discover_datasets"],
        "rubric": (
            "A correct tool takes the multi-FASTA as a data input, splits it into per-sequence "
            "files in the working directory, and declares a collection output that gathers them "
            "via discover_datasets (a pattern). A single data output would be incorrect."
        ),
    },
]


_RUBRIC_TEMPLATE = """\
You are reviewing a Galaxy tool definition produced by an automated tool generator
from a user's natural-language request.

Acceptance rubric for this case:
{rubric}

Score the tool between 0.0 and 1.0:
- 1.0: Valid, runnable-looking tool that satisfies the rubric -- right container,
  command correctly wires the declared inputs to the declared outputs, and the
  input/output shapes match what was asked.
- 0.5: Largely correct but with a real flaw -- a plausible but unverified container,
  a missing/extra input, or an output that won't be claimed correctly.
- 0.0: Doesn't satisfy the request, references undeclared inputs, hardcodes what
  should be a parameter, or no usable tool was produced.

Return a number; no commentary.
"""


def custom_tool_dataset(
    judge_model: Model | None = None,
    only: list[str] | None = None,
) -> Dataset[str, dict, dict[str, Any]]:
    """Build the custom_tool Dataset.

    If ``judge_model`` is given, attaches a per-case LLMJudge with a rubric-specific
    prompt that scores the produced tool's correctness.
    """
    cases: list[Case[str, dict, dict[str, Any]]] = []
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
                metadata={
                    "yaml_must_contain": proto["yaml_must_contain"],
                    "rubric": proto["rubric"],
                },
                evaluators=evaluators,
            )
        )
    return Dataset(name="custom_tool", cases=cases)
