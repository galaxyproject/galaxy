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
        "name": "ggplot2_boxplot_configfile",
        "query": (
            "Can you write a tool that uses ggplot2 to create a boxplot from a tabular file. The "
            "user should be able to select grouping column and numeric column. Place the script "
            "inside a configfile."
        ),
        # configfiles: -> the R script is materialized in a configfile (not dropped, not inlined);
        # ggplot2/Rscript -> R plotting wired through that script; quay.io/biocontainers -> a real
        # biocontainer rather than rocker/a guessed image; $(inputs. + from_work_dir -> the two
        # column selections are wired and the plot output is claimed.
        "yaml_must_contain": [
            "configfiles:",
            "ggplot2",
            "Rscript",
            "quay.io/biocontainers",
            "$(inputs.",
            "from_work_dir",
        ],
        "rubric": (
            "A correct tool plots a ggplot2 boxplot from a tabular input and is shaped exactly as "
            "asked:\n"
            "- The R script lives INSIDE a configfile: a `configfiles` entry whose filename holds "
            "the ggplot2 script as its content, and `shell_command` runs that file by name (e.g. "
            "`Rscript boxplot.R`). It must NOT run a script by name with no configfile that creates "
            "it (a dropped configfile), and -- since the user explicitly asked for a configfile -- "
            "must NOT inline the script with `Rscript -e`.\n"
            "- The container is an EXISTING biocontainer that bundles R + ggplot2 (a "
            "quay.io/biocontainers image, e.g. r-ggplot2). rocker/tidyverse, bare r-base, or a "
            "fabricated image/tag is incorrect.\n"
            "- There are TWO user-selectable inputs -- one for the grouping column and one for the "
            "numeric column (text/select/integer column references passed to the script) -- NOT "
            "hardcoded columns.\n"
            "- The tabular dataset is a data input and the plot image is an output claimed via "
            "from_work_dir."
        ),
    },
    {
        "name": "r_ggplot2_scatter_configfile",
        "query": (
            "Write a Galaxy tool that uses ggplot2 to draw a scatter plot from a tabular file. Let "
            "the user choose the x-axis column, the y-axis column, and a column to color the points "
            "by. Put the R script in a configfile."
        ),
        "yaml_must_contain": [
            "configfiles:",
            "ggplot2",
            "Rscript",
            "quay.io/biocontainers",
            "$(inputs.",
            "from_work_dir",
        ],
        "rubric": (
            "A correct tool draws a ggplot2 scatter plot from a tabular input and is shaped exactly "
            "as asked:\n"
            "- The R script lives INSIDE a `configfiles` entry (its content is the ggplot2 script) "
            "and `shell_command` runs that file by name (e.g. `Rscript scatter.R`). It must NOT run "
            "a script by name with no configfile that creates it, and must NOT inline the script "
            "with `Rscript -e`.\n"
            "- The container is an EXISTING quay.io/biocontainers image bundling R + ggplot2 (e.g. "
            "r-ggplot2). rocker/tidyverse, bare r-base, or a fabricated image/tag is incorrect.\n"
            "- There are THREE user-selectable column inputs -- x, y, and color -- passed to the "
            "script, NOT hardcoded columns.\n"
            "- The tabular dataset is a data input and the plot image is an output claimed via "
            "from_work_dir."
        ),
    },
    {
        "name": "pandas_group_summary_configfile",
        "query": (
            "Create a Galaxy tool that reads a tabular file and computes summary statistics (mean, "
            "median, count) of a numeric column grouped by a category column. The user should select "
            "which column is the group and which is the numeric value. Place the Python script in a "
            "configfile."
        ),
        "yaml_must_contain": [
            "configfiles:",
            "pandas",
            "$(inputs.",
            "from_work_dir",
            "quay.io/biocontainers",
        ],
        "rubric": (
            "A correct tool group-summarizes a tabular input with pandas and is shaped exactly as "
            "asked:\n"
            "- The Python script lives INSIDE a `configfiles` entry and `shell_command` runs that "
            "file by name (e.g. `python summary.py`). It must NOT run a script by name with no "
            "configfile that creates it, and must NOT inline the script with `python -c`.\n"
            "- The container is an EXISTING quay.io/biocontainers image that ships pandas (e.g. a "
            "pandas image), NOT bare python or a fabricated image/tag.\n"
            "- There are TWO user-selectable column inputs -- the group column and the numeric value "
            "column -- passed to the script, NOT hardcoded columns.\n"
            "- The tabular dataset is a data input and the summary table is an output claimed via "
            "from_work_dir."
        ),
    },
    {
        "name": "biopython_fasta_filter_configfile",
        "query": (
            "Make a Galaxy tool that filters sequences in a FASTA file by a minimum length that the "
            "user sets. Use a Python script (placed in a configfile) with Biopython to read the "
            "FASTA, drop sequences shorter than the threshold, and write the kept sequences."
        ),
        "yaml_must_contain": [
            "configfiles:",
            "$(inputs.",
            "from_work_dir",
            "quay.io/biocontainers",
            "type: integer",
        ],
        "rubric": (
            "A correct tool filters a FASTA by minimum length with Biopython and is shaped exactly "
            "as asked:\n"
            "- The Python script lives INSIDE a `configfiles` entry and `shell_command` runs that "
            "file by name (e.g. `python filter.py`). It must NOT run a script by name with no "
            "configfile that creates it, and must NOT inline the script with `python -c`.\n"
            "- The container is an EXISTING quay.io/biocontainers image that ships Biopython (e.g. a "
            "biopython image), NOT bare python or a fabricated image/tag.\n"
            "- There is a data input for the FASTA and an INTEGER input for the minimum length "
            "(a user parameter, NOT a hardcoded threshold).\n"
            "- The filtered FASTA is an output claimed via from_work_dir."
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
